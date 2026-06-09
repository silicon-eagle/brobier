import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from brobier.db.engine import get_admin_engine
from brobier.db.models import User
from brobier.schemas.admin import AdminUserOut, UserCreate, UserUpdate

router = APIRouter(tags=['admin:users'])


@router.get('', response_model=list[AdminUserOut])
def list_users() -> list[AdminUserOut]:
    with Session(get_admin_engine()) as db:
        users = db.scalars(select(User).order_by(User.created_at)).all()
        return [AdminUserOut.model_validate(u) for u in users]


@router.post('', response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate) -> AdminUserOut:
    with Session(get_admin_engine()) as db:
        user = User(
            email=body.email,
            display_name=body.display_name,
            role=body.role,
            is_active=body.is_active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return AdminUserOut.model_validate(user)


@router.put('/{user_id}', response_model=AdminUserOut)
def update_user(user_id: uuid.UUID, body: UserUpdate) -> AdminUserOut:
    with Session(get_admin_engine()) as db:
        user = db.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found.')

        if body.display_name is not None:
            user.display_name = body.display_name
        if body.role is not None:
            user.role = body.role
        if body.is_active is not None:
            user.is_active = body.is_active

        db.commit()
        db.refresh(user)
        return AdminUserOut.model_validate(user)


@router.post('/{user_id}/activate', response_model=AdminUserOut)
def activate_user(user_id: uuid.UUID) -> AdminUserOut:
    with Session(get_admin_engine()) as db:
        user = db.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found.')
        user.is_active = True
        db.commit()
        db.refresh(user)
        return AdminUserOut.model_validate(user)


@router.post('/{user_id}/deactivate', response_model=AdminUserOut)
def deactivate_user(user_id: uuid.UUID) -> AdminUserOut:
    with Session(get_admin_engine()) as db:
        user = db.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found.')
        user.is_active = False
        db.commit()
        db.refresh(user)
        return AdminUserOut.model_validate(user)
