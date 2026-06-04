import uuid

from pydantic import BaseModel

from brobier.db.models.user import UserRole


class RequestCodeIn(BaseModel):
    email: str


class VerifyCodeIn(BaseModel):
    email: str
    code: str


class UserOut(BaseModel):
    id: uuid.UUID
    display_name: str
    role: UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'


class VerifyCodeResponse(TokenResponse):
    user: UserOut


class MessageResponse(BaseModel):
    message: str
