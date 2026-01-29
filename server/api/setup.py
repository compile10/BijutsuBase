"""Setup router for initial admin account creation."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_users.exceptions import UserAlreadyExists
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.config import get_db
from models.user import User
from auth.user_manager import get_user_manager, UserManager
from auth.schemas import UserCreate


router = APIRouter(prefix="/setup", tags=["setup"])


class SetupStatusResponse(BaseModel):
    """Response for setup status check."""
    needs_setup: bool


class AdminCreateRequest(BaseModel):
    """Request to create the initial admin account."""
    email: EmailStr
    password: str
    username: str


class AdminCreateResponse(BaseModel):
    """Response after creating admin account."""
    success: bool
    message: str


@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status(db: AsyncSession = Depends(get_db)):
    """
    Check if the application needs initial setup.
    
    Returns needs_setup=True if no users exist in the database.
    """
    result = await db.execute(select(func.count(User.id)))
    user_count = result.scalar_one()
    
    return SetupStatusResponse(needs_setup=user_count == 0)


@router.post("/admin", response_model=AdminCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_account(
    request: AdminCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_manager: UserManager = Depends(get_user_manager),
):
    """
    Create the initial admin account.
    
    This endpoint only works when no users exist in the database.
    The created user will be a superuser (admin).
    """
    # Check if any users exist
    result = await db.execute(select(func.count(User.id)))
    user_count = result.scalar_one()
    
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup has already been completed. Admin account cannot be created."
        )
    
    # Create the admin user
    try:
        user_create = UserCreate(
            email=request.email,
            password=request.password,
            username=request.username,
            is_superuser=True,
            is_active=True,
            is_verified=True,  # Auto-verify the initial admin
        )
        
        await user_manager.create(user_create)
        
        return AdminCreateResponse(
            success=True,
            message="Admin account created successfully. You can now log in."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create admin account: {str(e)}"
        )
