from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_lender
from app.models import Lender
from app.schemas import ContractCreate, ContractResponse, ContractUpdate, ContractUpdateResponse
from app.services.contract_service import get_contract_service, ContractService

router = APIRouter(prefix="/lsp", tags=["LSP Contracts"])


@router.post("/contracts", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def submit_contract(
    contract_data: ContractCreate,
    current_lender: Lender = Depends(get_current_lender),
    db: Session = Depends(get_db),
    contract_service: ContractService = Depends(get_contract_service)
):
    """
    Submit a new contract.

    **Flow:**
    1. Authenticate via X-API-Key header
    2. Normalize input data (address, phone, email)
    3. Check for conflicts with other lenders' contracts
    4. Save contract (always, even if conflicts exist)
    5. If conflicts found:
       - Record conflicts in database
       - Notify other lenders via webhook
    6. Return response with conflict information

    **Headers:**
    - `X-API-Key`: Your lender API key

    **Returns:**
    - `status`: "NO_HIT" (no conflicts) or "EXISTING_CONTRACT" (conflicts found)
    - `contract_id`: UUID of the created contract
    - `conflicts`: List of conflicting contracts (if any)
    """
    return await contract_service.create_contract(db, current_lender, contract_data)


@router.put("/contracts/{contract_id}", response_model=ContractUpdateResponse)
async def update_contract_status(
    contract_id: str,
    update_data: ContractUpdate,
    current_lender: Lender = Depends(get_current_lender),
    db: Session = Depends(get_db),
    contract_service: ContractService = Depends(get_contract_service)
):
    """
    Update contract status (FUNDED or CANCELLED).

    **Flow:**
    1. Authenticate via X-API-Key header
    2. Validate contract ownership
    3. Update contract status
    4. Find and resolve open conflicts
    5. Notify other lenders in conflicts:
       - If FUNDED: send CONFLICT_CONTRACT_FUNDED event
       - If CANCELLED: send CONFLICT_RESOLVED event
    6. Return response

    **Headers:**
    - `X-API-Key`: Your lender API key

    **Path Parameters:**
    - `contract_id`: UUID of the contract to update

    **Body:**
    - `status`: "FUNDED" or "CANCELLED"
    - `funded_date`: Date when funded (optional, defaults to today)
    - `cancelled_date`: Date when cancelled (optional, defaults to today)

    **Returns:**
    - `contract_id`: UUID of the updated contract
    - `status`: New status
    - `conflicts_resolved`: Number of conflicts resolved
    """
    try:
        return await contract_service.update_contract(db, contract_id, current_lender, update_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
