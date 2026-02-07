import asyncio
import sys
sys.path.insert(0, '.')

from app.db.database import AsyncSessionLocal
from app.models.character import Character
from sqlalchemy import select

async def check_db():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Character).where(Character.name.in_(["张三", "李四", "王五"])))
        characters = result.scalars().all()
        for char in characters:
            print(f"角色: {char.name}")
            print(f"  current_emotion: {char.current_emotion}")
            print(f"  updated_at: {char.updated_at}")
            print()

if __name__ == "__main__":
    asyncio.run(check_db())
