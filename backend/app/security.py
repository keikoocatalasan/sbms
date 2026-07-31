import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_session


DEMO_ORGANIZATION_ID = "00000000-0000-0000-0000-000000000001"
DEMO_USERS = {
    "admin@argo.demo": {"id": "00000000-0000-0000-0000-000000000010", "password": "DemoPass123!", "name": "Demo Administrator", "scopes": ["subscription:admin", "subscription:billing", "subscription:support", "subscription:reports", "subscription:read", "subscription:system"]},
    "billing@argo.demo": {"id": "00000000-0000-0000-0000-000000000011", "password": "DemoPass123!", "name": "Demo Billing", "scopes": ["subscription:billing", "subscription:read"]},
}
bearer = HTTPBearer(auto_error=False)


class Principal(BaseModel):
    user_id: str
    organization_id: str
    scopes: set[str]
    name: str


def issue_token(user: dict) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": user["id"], "organization_id": DEMO_ORGANIZATION_ID, "scopes": user["scopes"], "name": user["name"], "iat": now, "exp": now + timedelta(minutes=settings.jwt_expiry_minutes)}, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def current_principal(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> Principal:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    settings = get_settings()
    try:
        claims = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return Principal(user_id=str(claims["sub"]), organization_id=str(claims["organization_id"]), scopes=set(claims.get("scopes", [])), name=str(claims.get("name", "User")))
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
