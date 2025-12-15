import hmac
import hashlib
import json
import httpx
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.models import Lender, WebhookLog, WebhookEventType
import logging

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for delivering webhooks to lenders"""

    @staticmethod
    def _generate_signature(api_key: str, payload: str) -> str:
        """
        Generate HMAC-SHA256 signature for webhook payload.

        Args:
            api_key: Lender's API key (used as secret)
            payload: JSON string of the payload

        Returns:
            Hex-encoded signature
        """
        return hmac.new(
            key=api_key.encode('utf-8'),
            msg=payload.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()

    @staticmethod
    async def send_webhook(
        db: Session,
        lender_id: int,
        event_type: WebhookEventType,
        payload_data: Dict[str, Any]
    ) -> bool:
        """
        Send webhook to lender.

        Args:
            db: Database session
            lender_id: ID of lender to notify
            event_type: Type of webhook event
            payload_data: Data to send in webhook

        Returns:
            True if delivery successful, False otherwise
        """
        # Get lender
        lender = db.query(Lender).filter(Lender.id == lender_id).first()

        if not lender or not lender.webhook_url:
            logger.info(f"Lender {lender_id} has no webhook URL configured, skipping")
            return False

        # Build payload
        request_body = {
            "event": event_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload_data
        }

        payload_json = json.dumps(request_body, default=str)

        # Generate signature
        signature = WebhookService._generate_signature(lender.api_key, payload_json)

        # Send HTTP POST
        response_code = None
        response_body = None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    lender.webhook_url,
                    headers={
                        "Content-Type": "application/json",
                        "X-LSP-Signature": signature
                    },
                    content=payload_json
                )
                response_code = response.status_code
                response_body = response.text[:1000]  # Limit to 1000 chars

                logger.info(f"Webhook delivered to lender {lender_id}: {event_type.value} - Status {response_code}")

        except Exception as e:
            logger.error(f"Webhook delivery failed to lender {lender_id}: {str(e)}")
            response_body = str(e)[:1000]

        # Log delivery attempt
        webhook_log = WebhookLog(
            lender_id=lender_id,
            event_type=event_type,
            payload=request_body,
            response_code=response_code,
            response_body=response_body,
            attempt=1
        )
        db.add(webhook_log)
        db.commit()

        # Return success if 2xx status code
        return response_code is not None and 200 <= response_code < 300


def get_webhook_service() -> WebhookService:
    """Dependency injection for webhook service"""
    return WebhookService()
