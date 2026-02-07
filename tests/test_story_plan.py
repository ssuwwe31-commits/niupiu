import asyncio
import httpx
import time


async def test_generate_story_plan():
    """测试生成剧情规划"""
    base_url = 'http://localhost:8001'
    
    data = {
        'story_outline': '一个关于创业团队的故事。李明和张伟是两个性格迥异的合伙人，他们在创业过程中面临各种挑战和冲突。',
        'characters': ['李明', '张伟', '王芳'],
        'structure_type': 'three_act'
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        print('=== 测试生成剧情规划 ===')
        response = await client.post(f'{base_url}/api/story-plan/generate', json=data)
        print(f'状态码: {response.status_code}')
        
        if response.status_code == 200:
            result = response.json()
            plan_id = result.get('plan_id')
            scene_count = result.get('scene_count', 0)
            print(f'生成成功! Plan ID: {plan_id}, 场景数: {scene_count}')
            print(f'场景列表: {result.get("scenes", [])}')
            return plan_id
        else:
            print(f'生成失败: {response.text}')
            return None


async def test_adjust_scene_plan(plan_id: str):
    """测试调整场景规划"""
    base_url = 'http://localhost:8001'
    
    data = {
        'plan_id': plan_id,
        'scene_number': 5,
        'adjustments': {
            'add_conflict': True,
            'enhance_emotion': 'anxiety',
            'modify_characters': ['李明', '张伟'],
            'change_location': '深夜办公室'
        }
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        print(f'\n=== 测试调整场景规划 (场景 {data["scene_number"]}) ===')
        response = await client.post(f'{base_url}/api/story-plan/adjust-scene', json=data)
        print(f'状态码: {response.status_code}')
        
        if response.status_code == 200:
            result = response.json()
            print(f'调整成功!')
            print(f'Plan ID: {result.get("plan_id")}')
            print(f'场景序号: {result.get("scene_number")}')
            print(f'调整内容: {result.get("adjustments")}')
            print(f'状态: {result.get("status")}')
        else:
            print(f'调整失败: {response.text}')


async def test_get_story_plan(plan_id: str):
    """测试获取剧情规划"""
    base_url = 'http://localhost:8001'
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f'\n=== 测试获取剧情规划 ===')
        response = await client.get(f'{base_url}/api/story-plan/{plan_id}')
        print(f'状态码: {response.status_code}')
        
        if response.status_code == 200:
            result = response.json()
            print(f'获取成功!')
            print(f'Plan ID: {result.get("plan_id")}')
            print(f'故事大纲: {result.get("story_outline")[:50]}...')
            print(f'场景数: {result.get("scene_count")}')
        else:
            print(f'获取失败: {response.text}')


async def main():
    """主测试函数"""
    plan_id = await test_generate_story_plan()
    
    if plan_id:
        time.sleep(1)
        await test_adjust_scene_plan(plan_id)
        time.sleep(1)
        await test_get_story_plan(plan_id)


if __name__ == "__main__":
    asyncio.run(main())
