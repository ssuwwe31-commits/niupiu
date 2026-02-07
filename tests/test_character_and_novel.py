import asyncio
import httpx
import json


async def test_create_character():
    """测试创建角色"""
    base_url = 'http://localhost:8001'
    
    data = {
        'name': '李明',
        'description': '创业者，性格急躁但充满激情',
        'traits': ['勇敢', '固执', '热情'],
        'goals': {
            'short_term': ['完成产品开发', '获得首轮融资'],
            'long_term': ['成为行业领导者']
        },
        'relationships': []
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        print('=== 测试创建角色 ===')
        response = await client.post(f'{base_url}/api/characters', json=data)
        print(f'状态码: {response.status_code}')
        
        if response.status_code == 200:
            result = response.json()
            print(f'创建成功!')
            print(f'角色ID: {result.get("id")}')
            print(f'角色名: {result.get("name")}')
            print(f'特征: {result.get("traits")}')
            print(f'目标: {result.get("goals")}')
            return result.get("id")
        else:
            print(f'创建失败: {response.text}')
            return None


async def test_get_characters():
    """测试获取角色列表"""
    base_url = 'http://localhost:8001'
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print('\n=== 测试获取角色列表 ===')
        response = await client.get(f'{base_url}/api/characters')
        print(f'状态码: {response.status_code}')
        
        if response.status_code == 200:
            result = response.json()
            print(f'获取成功!')
            print(f'角色数量: {result.get("total")}')
            print(f'角色列表: {json.dumps(result.get("characters"), indent=2, ensure_ascii=False)}')
        else:
            print(f'获取失败: {response.text}')


async def test_create_novel():
    """测试创建小说"""
    base_url = 'http://localhost:8001'
    
    data = {
        'title': '创业之路',
        'genre': '商业励志',
        'author': 'AI作者',
        'description': '讲述一个创业团队从零到一的故事'
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        print('\n=== 测试创建小说 ===')
        response = await client.post(f'{base_url}/api/novels', json=data)
        print(f'状态码: {response.status_code}')
        
        if response.status_code == 200:
            result = response.json()
            print(f'创建成功!')
            print(f'小说ID: {result.get("id")}')
            print(f'标题: {result.get("title")}')
            print(f'类型: {result.get("genre")}')
            print(f'作者: {result.get("author")}')
            return result.get("id")
        else:
            print(f'创建失败: {response.text}')
            return None


async def test_get_novels():
    """测试获取小说列表"""
    base_url = 'http://localhost:8001'
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print('\n=== 测试获取小说列表 ===')
        response = await client.get(f'{base_url}/api/novels')
        print(f'状态码: {response.status_code}')
        
        if response.status_code == 200:
            result = response.json()
            print(f'获取成功!')
            print(f'小说数量: {result.get("total")}')
            print(f'小说列表: {json.dumps(result.get("novels"), indent=2, ensure_ascii=False)}')
        else:
            print(f'获取失败: {response.text}')


async def test_observability():
    """测试可观测性接口"""
    base_url = 'http://localhost:8001'
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print('\n=== 测试可观测性接口 ===')
        
        response = await client.get(f'{base_url}/observability/health')
        print(f'健康检查状态码: {response.status_code}')
        if response.status_code == 200:
            print(f'健康检查: {response.json()}')
        
        response = await client.get(f'{base_url}/observability/info')
        print(f'配置信息状态码: {response.status_code}')
        if response.status_code == 200:
            print(f'配置信息: {response.json()}')
        
        response = await client.get(f'{base_url}/observability/cost-stats?days=7')
        print(f'成本统计状态码: {response.status_code}')
        if response.status_code == 200:
            print(f'成本统计: {response.json()}')


async def main():
    """主测试函数"""
    character_id = await test_create_character()
    await test_get_characters()
    novel_id = await test_create_novel()
    await test_get_novels()
    await test_observability()


if __name__ == "__main__":
    asyncio.run(main())
