from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta, date
from typing import List, Tuple, Optional
from app.models import Contract, Lender, Conflict, ContractStatus, ConflictStatus, WebhookEventType
from app.schemas import ContractCreate, ContractResponse, ConflictInfo, ContractUpdate, ContractUpdateResponse
from app.utils.normalization import normalize_address, normalize_phone, normalize_email, normalize_state, normalize_zip
from app.services.webhook_service import WebhookService
import logging

logger = logging.getLogger(__name__)


class ContractService:
    """Service for handling contract operations and conflict detection"""

    @staticmethod
    def _normalize_contract_data(data: ContractCreate) -> dict:
        """Normalize all contract fields"""
        return {
            "external_id": data.external_id,
            "address_street": normalize_address(data.address_street),
            "address_city": data.address_city.upper(),
            "address_state": normalize_state(data.address_state),
            "address_zip": normalize_zip(data.address_zip),
            "apn": data.apn.upper() if data.apn else None,
            "email": normalize_email(data.email),
            "phone": normalize_phone(data.phone),
            "signed_date": data.signed_date
        }

    @staticmethod
    def _find_conflicts(
        db: Session,
        current_lender_id: int,
        normalized_data: dict
    ) -> List[Contract]:
        """
        Find conflicting contracts from OTHER lenders.

        Returns contracts signed within last 90 days that match on:
        - APN (strongest match)
        - Address + ZIP
        - Email
        - Phone
        """
        ninety_days_ago = date.today() - timedelta(days=90)

        # Build filter conditions
        conditions = []

        # Property matches (strongest)
        if normalized_data["apn"]:
            conditions.append(Contract.apn == normalized_data["apn"])

        conditions.append(
            and_(
                Contract.address_street == normalized_data["address_street"],
                Contract.address_zip == normalized_data["address_zip"]
            )
        )

        # Person matches
        if normalized_data["email"]:
            conditions.append(Contract.email == normalized_data["email"])

        if normalized_data["phone"]:
            conditions.append(Contract.phone == normalized_data["phone"])

        # Query for conflicts
        conflicts = db.query(Contract).filter(
            Contract.status == ContractStatus.ACTIVE,
            Contract.lender_id != current_lender_id,
            Contract.signed_date > ninety_days_ago,
            or_(*conditions)
        ).all()

        return conflicts

    @staticmethod
    def _determine_match_reasons(
        conflict: Contract,
        normalized_data: dict
    ) -> List[str]:
        """Determine why two contracts match"""
        reasons = []

        if conflict.apn and normalized_data["apn"] and conflict.apn == normalized_data["apn"]:
            reasons.append("apn")

        if (conflict.address_street == normalized_data["address_street"] and
            conflict.address_zip == normalized_data["address_zip"]):
            reasons.append("address")

        if conflict.email and normalized_data["email"] and conflict.email == normalized_data["email"]:
            reasons.append("email")

        if conflict.phone and normalized_data["phone"] and conflict.phone == normalized_data["phone"]:
            reasons.append("phone")

        return reasons

    async def create_contract(
        self,
        db: Session,
        lender: Lender,
        data: ContractCreate
    ) -> ContractResponse:
        """
        Create a new contract and check for conflicts.

        Flow:
        1. Normalize input data
        2. Check for conflicts with other lenders
        3. Save contract (always, even if conflicts exist)
        4. If conflicts: record them and notify other lenders
        5. Return response
        """
        # 1. Normalize data
        normalized_data = self._normalize_contract_data(data)

        # 2. Find conflicts
        conflicting_contracts = self._find_conflicts(db, lender.id, normalized_data)

        # 3. Create and save contract
        new_contract = Contract(
            lender_id=lender.id,
            **normalized_data,
            status=ContractStatus.ACTIVE
        )
        db.add(new_contract)
        db.commit()
        db.refresh(new_contract)

        logger.info(f"Contract {new_contract.contract_id} created for lender {lender.name}")

        # 4. Handle conflicts
        conflict_infos = []

        if conflicting_contracts:
            webhook_service = WebhookService()

            for conflict in conflicting_contracts:
                # Determine match reasons
                match_reasons = self._determine_match_reasons(conflict, normalized_data)

                # Record conflict in database
                conflict_record = Conflict(
                    contract_a_id=conflict.id,
                    contract_b_id=new_contract.id,
                    match_reasons=match_reasons,
                    status=ConflictStatus.OPEN
                )
                db.add(conflict_record)

                # Calculate days since signed
                days_since_signed = (date.today() - conflict.signed_date).days

                # Prepare conflict info for response
                conflict_infos.append(ConflictInfo(
                    lender=conflict.lender.name,
                    signed_date=conflict.signed_date,
                    match_reasons=match_reasons,
                    days_since_signed=days_since_signed
                ))

                # Notify the OTHER lender via webhook
                await webhook_service.send_webhook(
                    db=db,
                    lender_id=conflict.lender_id,
                    event_type=WebhookEventType.NEW_CONFLICT,
                    payload_data={
                        "their_contract_id": conflict.external_id,
                        "conflicting_lender": lender.name,
                        "match_reasons": match_reasons,
                        "signed_date": new_contract.signed_date.isoformat()
                    }
                )

            db.commit()
            logger.info(f"Found {len(conflicting_contracts)} conflicts for contract {new_contract.contract_id}")

        # 5. Return response
        return ContractResponse(
            status="EXISTING_CONTRACT" if conflict_infos else "NO_HIT",
            contract_id=new_contract.contract_id,
            conflicts=conflict_infos if conflict_infos else None
        )

    async def update_contract(
        self,
        db: Session,
        contract_id: str,
        lender: Lender,
        data: ContractUpdate
    ) -> ContractUpdateResponse:
        """
        Update contract status (FUNDED or CANCELLED).

        Flow:
        1. Validate ownership
        2. Update contract status
        3. Find and resolve open conflicts
        4. Notify other lenders in conflicts
        5. Return response
        """
        # 1. Validate ownership
        contract = db.query(Contract).filter(
            Contract.contract_id == contract_id,
            Contract.lender_id == lender.id
        ).first()

        if not contract:
            raise ValueError("Contract not found or access denied")

        # 2. Update status
        contract.status = data.status
        if data.status == ContractStatus.FUNDED:
            contract.funded_date = data.funded_date or date.today()
        elif data.status == ContractStatus.CANCELLED:
            contract.cancelled_date = data.cancelled_date or date.today()

        contract.updated_at = datetime.utcnow()

        logger.info(f"Contract {contract_id} updated to status {data.status}")

        # 3. Find open conflicts
        open_conflicts = db.query(Conflict).filter(
            or_(
                Conflict.contract_a_id == contract.id,
                Conflict.contract_b_id == contract.id
            ),
            Conflict.status == ConflictStatus.OPEN
        ).all()

        # 4. Resolve conflicts and notify
        webhook_service = WebhookService()
        conflicts_resolved = 0

        for conflict_record in open_conflicts:
            # Find the other contract
            other_contract_id = (
                conflict_record.contract_a_id
                if conflict_record.contract_b_id == contract.id
                else conflict_record.contract_b_id
            )

            other_contract = db.query(Contract).filter(Contract.id == other_contract_id).first()

            if not other_contract:
                continue

            # Resolve conflict
            conflict_record.status = ConflictStatus.RESOLVED
            conflict_record.resolved_at = datetime.utcnow()
            conflicts_resolved += 1

            # Notify other lender
            if data.status == ContractStatus.FUNDED:
                await webhook_service.send_webhook(
                    db=db,
                    lender_id=other_contract.lender_id,
                    event_type=WebhookEventType.CONFLICT_CONTRACT_FUNDED,
                    payload_data={
                        "your_contract_id": other_contract.external_id,
                        "funded_by": lender.name,
                        "funded_date": contract.funded_date.isoformat() if contract.funded_date else None
                    }
                )
            elif data.status == ContractStatus.CANCELLED:
                await webhook_service.send_webhook(
                    db=db,
                    lender_id=other_contract.lender_id,
                    event_type=WebhookEventType.CONFLICT_RESOLVED,
                    payload_data={
                        "your_contract_id": other_contract.external_id,
                        "cancelled_by": lender.name
                    }
                )

        db.commit()

        logger.info(f"Resolved {conflicts_resolved} conflicts for contract {contract_id}")

        # 5. Return response
        return ContractUpdateResponse(
            contract_id=contract.contract_id,
            status=contract.status,
            conflicts_resolved=conflicts_resolved
        )


def get_contract_service() -> ContractService:
    """Dependency injection for contract service"""
    return ContractService()
