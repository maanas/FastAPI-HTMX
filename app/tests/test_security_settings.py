import importlib

import pytest
from loguru import logger
from sqlalchemy import delete, func, select

from app.app import on_startup
from app.commands.create_superuser import create_or_promote_superuser
from app.core.auth_settings import AuthSettings, get_auth_secret, validate_auth_secret
from app.models.users import User

pytestmark = pytest.mark.anyio

REAL_SECRET = "pytest-real-secret-value-9f8e7d6c5b4a"
EMAIL_PREFIX = "pytest-"
STRONG = "a-long-enough-password"


@pytest.mark.parametrize(
    "bad",
    [
        None,
        "",
        "   ",
        "my_default_secret_key",
        "change-me-auth-secret",
        "  change-me-auth-secret  ",
        "short-but-not-empty",
        "x" * 31,
    ],
)
def test_bad_secret_raises(bad):
    with pytest.raises(RuntimeError, match="AUTH_SECRET"):
        validate_auth_secret(bad)


def test_real_secret_passes():
    assert validate_auth_secret(REAL_SECRET) == REAL_SECRET
    assert validate_auth_secret("x" * 32) == "x" * 32
    assert validate_auth_secret(f"  {REAL_SECRET}\n") == REAL_SECRET


def test_get_auth_secret_reads_env_and_rejects_placeholder(monkeypatch):
    monkeypatch.setenv("AUTH_SECRET", REAL_SECRET)
    assert get_auth_secret() == REAL_SECRET
    monkeypatch.setenv("AUTH_SECRET", "change-me-auth-secret")
    with pytest.raises(RuntimeError, match="secrets.token_urlsafe"):
        get_auth_secret()
    monkeypatch.delenv("AUTH_SECRET")
    # A .env file in the working directory would be a fallback; ignore it here.
    monkeypatch.setitem(AuthSettings.model_config, "env_file", None)
    with pytest.raises(RuntimeError, match="AUTH_SECRET"):
        get_auth_secret()


def test_secret_check_never_logs_or_prints_the_value(monkeypatch, capsys):
    lines: list[str] = []
    sink = logger.add(lines.append, level="TRACE")
    try:
        monkeypatch.setenv("AUTH_SECRET", REAL_SECRET)
        get_auth_secret()
        for bad in ("my_default_secret_key", "change-me-auth-secret"):
            monkeypatch.setenv("AUTH_SECRET", bad)
            with pytest.raises(RuntimeError) as exc:
                get_auth_secret()
            assert bad not in str(exc.value)
    finally:
        logger.remove(sink)
    out = capsys.readouterr()
    assert REAL_SECRET not in "".join(lines) + out.out + out.err


@pytest.fixture
async def clean_users(db_session):
    async def purge():
        await db_session.execute(
            delete(User).where(User.email.like(f"{EMAIL_PREFIX}%"))
        )
        await db_session.commit()

    await purge()
    yield db_session
    await purge()


async def _get(session, email):
    return (
        await session.execute(select(User).where(User.email == email))
    ).scalars().first()


async def test_creates_superuser(clean_users):
    email = f"{EMAIL_PREFIX}create@example.com"
    assert await create_or_promote_superuser(clean_users, email, STRONG) == "created"
    user = await _get(clean_users, email)
    assert user.is_superuser and user.is_active
    assert user.hashed_password != STRONG


async def test_promotes_existing_user_and_is_idempotent(clean_users):
    email = f"{EMAIL_PREFIX}promote@example.com"
    clean_users.add(
        User(
            email=email,
            hashed_password="x",
            is_superuser=False,
            is_active=False,
        )
    )
    await clean_users.commit()
    assert await create_or_promote_superuser(clean_users, email, None) == "promoted"
    user = await _get(clean_users, email)
    assert user.is_superuser and user.is_active
    assert user.hashed_password == "x"  # no password given, hash untouched

    assert await create_or_promote_superuser(clean_users, email, STRONG) == "promoted"
    first_hash = (await _get(clean_users, email)).hashed_password
    assert first_hash != "x"
    assert await create_or_promote_superuser(clean_users, email, None) == "promoted"
    count = await clean_users.scalar(
        select(func.count()).select_from(User).where(User.email == email)
    )
    assert count == 1
    assert (await _get(clean_users, email)).hashed_password == first_hash


@pytest.mark.parametrize("bad", ["short", "elevenchars", "password123"])
async def test_refuses_weak_password(clean_users, bad):
    email = f"{EMAIL_PREFIX}weak@example.com"
    with pytest.raises(ValueError):
        await create_or_promote_superuser(clean_users, email, bad)
    assert await _get(clean_users, email) is None


async def test_new_user_needs_password(clean_users):
    with pytest.raises(ValueError):
        await create_or_promote_superuser(
            clean_users, f"{EMAIL_PREFIX}nopw@example.com", None
        )


async def test_startup_creates_no_default_superuser(db_session):
    import app.database.db as db_module

    assert not hasattr(db_module, "create_db_and_tables")

    async def count():
        return await db_session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.email == "superuser@admin.com")
        )

    before = await count()
    await on_startup()
    after = await count()
    assert after == before


async def test_lookup_is_case_insensitive(clean_users):
    stored = f"{EMAIL_PREFIX}MixedCase@Example.com"
    clean_users.add(
        User(email=stored, hashed_password="x", is_superuser=False, is_active=True)
    )
    await clean_users.commit()
    result = await create_or_promote_superuser(clean_users, stored.lower(), None)
    assert result == "promoted"
    rows = (
        (
            await clean_users.execute(
                select(User).where(func.lower(User.email) == stored.lower())
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1 and rows[0].is_superuser


async def test_manager_hooks_do_not_log_tokens(capsys):
    from app.database.security import UserManager

    token = "sentinel-token-7c1d9e"
    user = User(email=f"{EMAIL_PREFIX}hooks@example.com")
    manager = UserManager(None)
    lines: list[str] = []
    sink = logger.add(lines.append, level="TRACE")
    try:
        await manager.on_after_forgot_password(user, token)
        await manager.on_after_request_verify(user, token)
    finally:
        logger.remove(sink)
    out = capsys.readouterr()
    assert lines  # something was logged, just not the token
    assert token not in "".join(lines) + out.out + out.err


def test_bad_secret_makes_security_import_fail(monkeypatch):
    import app.database.security as security

    monkeypatch.setenv("AUTH_SECRET", "change-me-auth-secret")
    # A failed reload rebinds nothing: the module keeps its auth objects
    with pytest.raises(RuntimeError, match="AUTH_SECRET"):
        importlib.reload(security)
