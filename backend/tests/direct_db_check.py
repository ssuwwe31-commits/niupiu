import asyncio
import asyncpg

async def check_db_directly():
    DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/niupi_db"
    db_url = DATABASE_URL.replace("+asyncpg", "")
    
    conn = await asyncpg.connect(db_url)
    try:
        rows = await conn.fetch(
            "SELECT name, current_emotion, updated_at FROM characters WHERE name IN ($1, $2, $3)",
            "张三", "李四", "王五"
        )
        print("直接查询数据库:")
        for row in rows:
            print(f"\n角色: {row['name']}")
            print(f"  current_emotion: {row['current_emotion']}")
            print(f"  updated_at: {row['updated_at']}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_db_directly())
