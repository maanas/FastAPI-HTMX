"""Create or promote a superuser.

    .venv/bin/python -m app.commands.create_superuser

Reads SUPERUSER_EMAIL and SUPERUSER_PASSWORD from the environment and prompts
for a missing value when stdin is a terminal. A given password replaces the
password of an existing user. The password is never printed.
"""

import asyncio
import getpass
import os
import sys

from fastapi_users.password import PasswordHelper
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

MIN_PASSWORD_LENGTH = 12
FORBIDDEN_PASSWORDS = {"password123"}


def check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if password in FORBIDDEN_PASSWORDS:
        raise ValueError("Password is too common")


async def create_or_promote_superuser(
    session: AsyncSession, email: str, password: str | None
) -> str:
    """Return "created" or "promoted"; raise ValueError on bad input."""
    from app.models.users import User

    email = (email or "").strip().lower()
    if "@" not in email:
        raise ValueError("A valid email is required")
    if password:
        check_password(password)
    user = (
        await session.execute(select(User).where(func.lower(User.email) == email))
    ).scalars().first()
    if user is None:
        if not password:
            raise ValueError("A password is required to create a new user")
        session.add(
            User(
                email=email,
                hashed_password=PasswordHelper().hash(password),
                is_superuser=True,
                is_active=True,
            )
        )
        await session.commit()
        return "created"
    user.is_superuser = True
    user.is_active = True
    if password:
        user.hashed_password = PasswordHelper().hash(password)
    await session.commit()
    return "promoted"


def _collect_input() -> tuple[str, str | None]:
    email = os.environ.get("SUPERUSER_EMAIL", "")
    password = os.environ.get("SUPERUSER_PASSWORD") or None
    if sys.stdin.isatty():
        if not email:
            email = input("Superuser email: ")
        if password is None:
            password = getpass.getpass("Password: ")
            if password and password != getpass.getpass("Repeat password: "):
                raise ValueError("Passwords do not match")
            password = password or None
    return email, password


async def _run(email: str, password: str | None) -> str:
    if not os.environ.get("DATABASE_URL"):
        raise ValueError("DATABASE_URL is not set")
    from app.database.base import async_session_maker, engine, init_models

    init_models()
    try:
        async with async_session_maker() as session:
            return await create_or_promote_superuser(session, email, password)
    finally:
        await engine.dispose()


def main() -> int:
    try:
        email, password = _collect_input()
        result = asyncio.run(_run(email, password))
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"Error: {type(exc).__name__}", file=sys.stderr)
        return 1
    suffix = " (password updated)" if password and result == "promoted" else ""
    print(f"Superuser {result}: {email.strip().lower()}{suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
