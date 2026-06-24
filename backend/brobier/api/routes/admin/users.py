import uuid

from fastapi import APIRouter, HTTPException, status

from brobier.schemas.admin import AdminUserOut, UserCreate, UserUpdate
from brobier.services import user_service

router = APIRouter(tags=['admin:users'])


@router.get('', response_model=list[AdminUserOut])
def list_users() -> list[AdminUserOut]:
    return user_service.list_users()


@router.post('', response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate) -> AdminUserOut:
    return user_service.create_user(body)


@router.put('/{user_id}', response_model=AdminUserOut)
def update_user(user_id: uuid.UUID, body: UserUpdate) -> AdminUserOut:
    try:
        return user_service.update_user(user_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post('/{user_id}/activate', response_model=AdminUserOut)
def activate_user(user_id: uuid.UUID) -> AdminUserOut:
    try:
        return user_service.activate_user(user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post('/{user_id}/deactivate', response_model=AdminUserOut)
def deactivate_user(user_id: uuid.UUID) -> AdminUserOut:
    try:
        return user_service.deactivate_user(user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
