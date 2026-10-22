import asyncio
import getpass
import sys

from pydantic import ValidationError

from app.core.security import hash_password
from app.db.session import async_session, engine
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate


async def main(email: str) -> None:
    async with async_session() as session:
        repo = UserRepository(session)
        existing = await repo.get_by_email(email.lower())

        if existing:
            existing.role = "admin"
            existing.is_active = True
            await session.commit()
            print(f"{existing.email} is now an admin.")

        else:
            password = getpass.getpass("Password: ")
            try:
                data = UserCreate(email=email, password=password)
            except ValidationError as exc:
                sys.exit(f"Invalid input: {exc.errors()[0]['msg']}")

            user = await repo.create(data.email, hash_password(data.password))
            user.role = "admin"
            await session.commit()
            print(f"Admin {user.email} created.")

        await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m scripts.create_admin <email>")
    asyncio.run(main(sys.argv[1]))
