import asyncio
import aiohttp

async def check_via_api():
    base_url = "http://127.0.0.1:8007"
    async with aiohttp.ClientSession() as session:
        print("查询角色信息:")
        response = await session.get(f"{base_url}/api/characters")
        data = await response.json()
        for char in data:
            if char['name'] in ['张三', '李四', '王五']:
                print(f"\n角色: {char['name']}")
                print(f"  current_emotion: {char.get('current_emotion', {})}")
                print(f"  updated_at: {char.get('updated_at', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(check_via_api())
