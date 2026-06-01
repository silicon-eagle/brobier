import uuid

from fastapi import APIRouter, HTTPException, status

from backend.schemas.admin import AdminUserOut, UserCreate, UserUpdate

router = APIRouter(tags=['admin:users'])


@router.get('', response_model=list[AdminUserOut])
def list_users() -> list[AdminUserOut]:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail='Not implemented.')


@router.post('', response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate) -> AdminUserOut:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail='Not implemented.')


@router.put('/{user_id}', response_model=AdminUserOut)
def update_user(user_id: uuid.UUID, body: UserUpdate) -> AdminUserOut:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail='Not implemented.')


@router.post('/{user_id}/activate', response_model=AdminUserOut)
def activate_user(user_id: uuid.UUID) -> AdminUserOut:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail='Not implemented.')


@router.post('/{user_id}/deactivate', response_model=AdminUserOut)
def deactivate_user(user_id: uuid.UUID) -> AdminUserOut:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail='Not implemented.')
