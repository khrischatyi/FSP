from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import secrets
from app.database import get_db
from app.models import Lender
from app.schemas import LenderCreate, LenderResponse

router = APIRouter(prefix="/admin/lenders", tags=["Admin - Lender Management"])


@router.post("", response_model=LenderResponse, status_code=status.HTTP_201_CREATED)
def create_lender(
    lender_data: LenderCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new lender with API key.

    **Note:** In production, this endpoint should be protected with admin authentication.

    **Returns:**
    - Lender information including generated API key
    """
    # Generate secure API key
    api_key = f"lsp_{secrets.token_urlsafe(32)}"

    lender = Lender(
        name=lender_data.name,
        api_key=api_key,
        webhook_url=lender_data.webhook_url,
        is_active=True
    )

    db.add(lender)
    db.commit()
    db.refresh(lender)

    return lender


@router.get("", response_model=List[LenderResponse])
def list_lenders(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all lenders.

    **Note:** In production, this endpoint should be protected with admin authentication.
    """
    lenders = db.query(Lender).offset(skip).limit(limit).all()
    return lenders


@router.get("/{lender_id}", response_model=LenderResponse)
def get_lender(
    lender_id: str,
    db: Session = Depends(get_db)
):
    """
    Get specific lender by ID.

    **Note:** In production, this endpoint should be protected with admin authentication.
    """
    lender = db.query(Lender).filter(Lender.lender_id == lender_id).first()

    if not lender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lender {lender_id} not found"
        )

    return lender


@router.patch("/{lender_id}/deactivate")
def deactivate_lender(
    lender_id: str,
    db: Session = Depends(get_db)
):
    """
    Deactivate a lender (revoke API access).

    **Note:** In production, this endpoint should be protected with admin authentication.
    """
    lender = db.query(Lender).filter(Lender.lender_id == lender_id).first()

    if not lender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lender {lender_id} not found"
        )

    lender.is_active = False
    db.commit()

    return {"message": f"Lender {lender.name} deactivated"}
