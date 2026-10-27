"""Служебные команды.

    docker compose exec app uv run python -m backend.app.cli make-admin user@example.com
    docker compose exec app uv run python -m backend.app.cli remove-admin user@example.com
"""
import argparse
import asyncio

from sqlalchemy import select

from backend.app.db.connect import SessionLocal, engine
from backend.app.db.enums import UserRole
from backend.app.db.models import User


async def set_role(email: str, role: UserRole) -> None:
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email))

        if user is None:
            raise SystemExit(f"Пользователь {email} не найден")

        user.role = role
        await db.commit()

    await engine.dispose()
    print(f"{email}: роль {role.value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Служебные команды")
    commands = parser.add_subparsers(dest="command", required=True)

    for name in ("make-admin", "remove-admin"):
        commands.add_parser(name).add_argument("email")

    args = parser.parse_args()
    role = UserRole.ADMIN if args.command == "make-admin" else UserRole.USER
    asyncio.run(set_role(args.email, role))


if __name__ == "__main__":
    main()
