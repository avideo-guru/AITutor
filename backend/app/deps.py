import functools
from dataclasses import dataclass

import jwt
from fastapi import Request

from app.config import settings
from app.db import get_pool
from app.errors import ApiError


# Cached client fetches Supabase's public signing keys from its JWKS endpoint,
# so this verifies tokens under key rotation without a shared secret. Built
# lazily on first auth (not at import): PyJWKClient validates the URL in its
# constructor, so eager init would make the whole app un-importable whenever
# SUPABASE_URL is unset (CI, tooling, tests).
@functools.lru_cache(maxsize=1)
def _get_jwks_client() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(
        f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    )


@dataclass
class AuthUser:
    id: str
    email: str


async def get_current_user(request: Request) -> AuthUser:
    """Verify the Supabase access token against Supabase's published JWKS."""
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise ApiError(401, "UNAUTHENTICATED", "Missing bearer token")
    token = auth[7:]
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError:
        raise ApiError(401, "UNAUTHENTICATED", "Invalid or expired token")
    return AuthUser(id=payload["sub"], email=payload.get("email", ""))


async def get_profile(request: Request) -> dict:
    """Auth + ensure a profiles row exists; returns the row as a dict."""
    user = await get_current_user(request)
    pool = get_pool()
    row = await pool.fetchrow(
        """
        insert into profiles (id) values ($1)
        on conflict (id) do update set id = excluded.id
        returning id, exam_target, plan, stripe_customer_id, plan_expires_at,
                  questions_today, questions_reset_on,
                  questions_month, questions_month_reset_on
        """,
        user.id,
    )
    profile = dict(row)
    profile["email"] = user.email
    return profile
