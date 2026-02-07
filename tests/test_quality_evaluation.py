import asyncio
import httpx
import json


async def test_single_quality_evaluation():
    """测试单个剧本质量评估"""
    base_url = 'http://localhost:8001'
    
    script_content = """
    场景：办公室
    人物：李明、张伟
    
    李明：（焦虑地）这个月的数据不理想啊。
    张伟：（淡定）市场环境不好，慢慢来。
    
    李明：（拍桌子）我们不能坐以待毙！
    张伟：（皱眉）那你想怎么办？
    
    李明：（站起来）我们要改变策略！
    张伟：（点头）好，你说。
    
    李明：（坚定）从今天开始，全员加班！
    张伟：（叹气）你确定这是最好的办法？
    """
    
    data = {
        'script': script_content,
        'custom_weights': {
            'conflict_intensity': 0.2,
            'emotion_rendering': 0.15,
            'character_consistency': 0.2,
            'dialogue_naturalness': 0.15,
            'dramatic_tension': 0.15,
            'overall_coherence': 0.15
        }
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        print('=== 测试单个剧本质量评估 ===')
        response = await client.post(f'{base_url}/api/quality-evaluate', json=data)
        print(f'状态码: {response.status_code}')
        
        if response.status_code == 200:
            result = response.json()
            print(f'评估成功!')
            print(f'总分: {result.get("overall_score")}')
            print(f'质量等级: {result.get("quality_level")}')
            print(f'详细评分: {json.dumps(result.get("dimension_scores"), indent=2, ensure_ascii=False)}')
            print(f'改进建议: {result.get("suggestions")}')
        else:
            print(f'评估失败: {response.text}')


async def test_batch_quality_evaluation():
    """测试批量剧本质量评估"""
    base_url = 'http://localhost:8001'
    
    scripts = [
        {
            'id': 'script_1',
            'content': '场景：办公室\n人物：李明、张伟\n\n李明：（焦虑）这个月的数据不理想。\n张伟：（淡定）市场不好。'
        },
        {
            'id': 'script_2',
            'content': '场景：会议室\n人物：王芳、李明\n\n王芳：（高兴）项目成功了！\n李明：（激动）太棒了！'
        },
        {
            'id': 'script_3',
            'content': '场景：咖啡厅\n人物：张伟、王芳\n\n张伟：（沉思）下一步怎么办？\n王芳：（思考）我们需要重新规划。'
        }
    ]
    
    data = {
        'scripts': scripts,
        'custom_weights': {
            'conflict_intensity': 0.2,
            'emotion_rendering': 0.15,
            'character_consistency': 0.2,
            'dialogue_naturalness': 0.15,
            'dramatic_tension': 0.15,
            'overall_coherence': 0.15
        }
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        print('\n=== 测试批量剧本质量评估 ===')
        response = await client.post(f'{base_url}/api/quality-evaluate/batch', json=data)
        print(f'状态码: {response.status_code}')
        
        if response.status_code == 200:
            result = response.json()
            print(f'批量评估成功!')
            print(f'评估数量: {result.get("total_count")}')
            print(f'平均分: {result.get("average_score"):.2f}')
            print(f'质量分布: {result.get("quality_distribution")}')
            print(f'详细结果: {json.dumps(result.get("results"), indent=2, ensure_ascii=False)}')
        else:
            print(f'批量评估失败: {response.text}')


async def main():
    """主测试函数"""
    await test_single_quality_evaluation()
    await test_batch_quality_evaluation()


if __name__ == "__main__":
    asyncio.run(main())
