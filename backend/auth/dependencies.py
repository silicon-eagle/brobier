import uuid

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.auth.jwt import decode_access_token
from backend.db.models.user import User, UserRole
from backend.db.session import get_db


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Missing or invalid Authorization header.')

    token = auth_header.removeprefix('Bearer ')
    try:
        payload = decode_access_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    user_id_str = payload.get('sub')
    if not user_id_str:
        raise HTTPException(status_code=401, detail='Invalid token payload.')

    user = db.get(User, uuid.UUID(user_id_str))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail='User not found or inactive.')

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail='Admin access required.')
    return current_user
