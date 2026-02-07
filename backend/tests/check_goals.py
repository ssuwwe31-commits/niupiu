import asyncio
from app.db.database import AsyncSessionLocal
from app.models.character import Character
from sqlalchemy import select

async def check_goals():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Character).where(Character.name.in_(["张三", "李四", "王五"])))
        characters = result.scalars().all()
        for char in characters:
            print(f"角色: {char.name}")
            print(f"  goals: {char.goals}")
            print(f"  goals type: {type(char.goals)}")
            if char.goals:
                if isinstance(char.goals, dict):
                    print(f"  short_term: {char.goals.get('short_term', [])}")
                    print(f"  long_term: {char.goals.get('long_term', [])}")
                else:
                    print(f"  goals content (非dict): {char.goals}")
            print()

if __name__ == "__main__":
    asyncio.run(check_goals())
