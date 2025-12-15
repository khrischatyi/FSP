from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models import Lender


def get_current_lender(
    x_api_key: str = Header(..., description="API key for authentication"),
    db: Session = Depends(get_db)
) -> Lender:
    """
    Authenticate lender via API key from X-API-Key header.

    Returns:
        Lender object if valid

    Raises:
        401 if invalid or inactive
    """
    lender = db.query(Lender).filter(
        Lender.api_key == x_api_key,
        Lender.is_active == True
    ).first()

    if not lender:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key"
        )

    return lender
