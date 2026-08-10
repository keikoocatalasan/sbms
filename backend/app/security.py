import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from pwdlib import PasswordHash

from . import models
from .config import get_settings
from .db import get_session


bearer = HTTPBearer(auto_error=False)
password_hash = PasswordHash.recommended()
ADMIN_SCOPES = ["subscription:admin", "subscription:billing", "subscription:support", "subscription:reports", "subscription:read", "subscription:system"]
MEMBER_SCOPES = ["subscription:read"]


class Principal(BaseModel):
    user_id: str
    organization_id: str
    scopes: set[str]
    name: str


def issue_token(user: models.User) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": user.id, "organization_id": user.organization_id, "scopes": user.scopes, "name": user.name, "iat": now, "exp": now + timedelta(minutes=settings.jwt_expiry_minutes)}, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def current_principal(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)], session: Annotated[Session, Depends(get_session)]) -> Principal:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    settings = get_settings()
    try:
        claims = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user = session.scalar(select(models.User).where(models.User.id == str(claims["sub"]), models.User.status == "active"))
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive or no longer exists")
        return Principal(user_id=user.id, organization_id=user.organization_id, scopes=set(user.scopes or []), name=user.name)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired bearer token") from exc


def require_scope(*accepted: str):
    def dependency(principal: Annotated[Principal, Depends(current_principal)]) -> Principal:
        if not principal.scopes.intersection(accepted):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your role cannot perform this action")
        return principal
    return dependency


def request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


DBSession = Annotated[Session, Depends(get_session)]
