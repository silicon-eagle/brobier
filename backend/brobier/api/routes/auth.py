from fastapi import APIRouter, Depends, HTTPException, Response

from brobier.auth.dependencies import get_current_user, get_refresh_token_raw
from brobier.core.config import get_settings
from brobier.db.models.user import User
from brobier.schemas.auth import (
    MessageResponse,
    RequestCodeIn,
    TokenResponse,
    UserOut,
    VerifyCodeIn,
    VerifyCodeResponse,
)
from brobier.services import auth_service

router = APIRouter(tags=['auth'])


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.jwt_refresh_cookie_name,
        value=raw_token,
        httponly=True,
        samesite='lax',
        secure=settings.env == 'prd',
        path='/auth/refresh',
        max_age=settings.jwt_refresh_expire_days * 86400,
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.jwt_refresh_cookie_name,
        path='/auth/refresh',
    )


@router.post('/request-code', response_model=MessageResponse)
def request_code(body: RequestCodeIn) -> MessageResponse:
    auth_service.request_code(body.email)
    return MessageResponse(message='If that email is registered, a code has been sent.')


@router.post('/verify-code', response_model=VerifyCodeResponse)
def verify_code(body: VerifyCodeIn, response: Response) -> VerifyCodeResponse:
    try:
        access_token, raw_refresh_token, user = auth_service.verify_code(body.email, body.code)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    _set_refresh_cookie(response, raw_refresh_token)
    return VerifyCodeResponse(
        access_token=access_token,
        user=UserOut(id=user.id, display_name=user.display_name, role=user.role),
    )


@router.post('/refresh', response_model=TokenResponse)
def refresh(raw_token: str = Depends(get_refresh_token_raw)) -> TokenResponse:
    try:
        access_token = auth_service.refresh(raw_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    return TokenResponse(access_token=access_token)


@router.post('/logout', response_model=MessageResponse)
def logout(response: Response, raw_token: str = Depends(get_refresh_token_raw)) -> MessageResponse:
    auth_service.logout(raw_token)
    _clear_refresh_cookie(response)
    return MessageResponse(message='Logged out.')


@router.get('/me', response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=current_user.id, display_name=current_user.display_name, role=current_user.role)
