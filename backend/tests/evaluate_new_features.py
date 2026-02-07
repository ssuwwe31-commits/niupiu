import asyncio
import aiohttp
import json
from typing import Dict, Any, List
from datetime import datetime
from collections import defaultdict


class FeatureEvaluator:
    def __init__(self, base_url: str = "http://127.0.0.1:8003"):
        self.base_url = base_url
        self.session = None
        self.evaluation_results = []
        self.test_data = {}

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            async with self.session.request(method, url, **kwargs) as response:
                result = {
                    "status": response.status,
                    "success": 200 <= response.status < 300,
                    "endpoint": endpoint,
                    "method": method,
                    "timestamp": datetime.now().isoformat()
                }
                try:
                    result["data"] = await response.json()
                except:
                    result["data"] = await response.text()
                return result
        except Exception as e:
            return {
                "status": 0,
                "success": False,
                "endpoint": endpoint,
                "method": method,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def ensure_test_data(self):
        await self._ensure_test_novel()
        await self._ensure_test_characters()
        await self._ensure_test_story_units()

    async def _ensure_test_novel(self):
        if "novel_id" in self.test_data:
            return

        test_content = """第一章 背叛
主角张三和兄弟李四从小一起长大，情同手足。张三一直相信李四会永远支持自己。然而，在一次重要的商业谈判中，李四暗中与竞争对手合作，出卖了张三。张三发现真相后，感到愤怒和心碎。

第二章 决裂
张三质问李四，李四表示这是为了生存。两人激烈争吵，最终决裂。张三发誓要让李四付出代价，而李四则陷入内疚和恐惧之中。

第三章 复仇
张三开始收集证据，准备揭露李四的背叛。李四试图联系张三，请求原谅，但张三拒绝沟通。两人的关系彻底破裂。

第四章 转折
张三在调查中发现，李四的背叛背后有更大的阴谋。原来李四是被迫的，他的家人被威胁。张三陷入了矛盾：是继续复仇，还是帮助兄弟。

第五章 和解
张三决定帮助李四，两人联手对抗真正的敌人。经过一番波折，他们终于揭露了幕后黑手，重新建立了信任。

第六章 新的开始
张三和李四的关系虽然无法回到从前，但他们选择了原谅。两人各自开始了新的生活，但心中永远留下了这段经历。
"""

        data = aiohttp.FormData()
        data.add_field('file', test_content.encode('utf-8'), filename='test_eval.txt', content_type='text/plain')
        data.add_field('title', '评估测试小说')
        data.add_field('author', '评估测试作者')
        
        result = await self.request("POST", "/api/novels/upload", data=data)
        if result["success"]:
            self.test_data["novel_id"] = result["data"]["id"]
            print(f"✓ 测试小说已创建: {result['data']['id']}")
        else:
            print(f"✗ 创建测试小说失败: {result.get('error')}")

    async def _ensure_test_characters(self):
        if "character_ids" in self.test_data:
            return

        self.test_data["character_ids"] = []

        character_names = ["张三", "李四", "王五"]

        for char_name in character_names:
            result = await self.request("GET", "/api/characters")
            if result["success"] and result["data"]:
                for char in result["data"]:
                    if char["name"] == char_name:
                        self.test_data["character_ids"].append(char["id"])
                        print(f"✓ 测试角色已存在: {char_name}")
                        break

    async def _ensure_test_story_units(self):
        if "story_unit_ids" in self.test_data:
            return

        story_units = [
            {
                "scene": "办公室",
                "characters": ["张三", "李四"],
                "core_conflict": "张三发现李四背叛的证据",
                "emotion_curve": ["震惊", "愤怒", "心碎"],
                "plot_function": "高潮",
                "result": "两人决裂",
                "original_text": "张三在办公室里发现了李四与竞争对手往来的邮件，手中的文件滑落。李四推门进来，看到张三的脸色，知道事情败露。",
                "conflict_type": "背叛",
                "emotion_type": "愤怒",
                "character_relationship": "兄弟决裂",
                "time_position": "第二章",
                "chapter": 2
            },
            {
                "scene": "咖啡厅",
                "characters": ["张三", "王五"],
                "core_conflict": "王五暗示李四的背叛",
                "emotion_curve": ["怀疑", "警惕", "愤怒"],
                "plot_function": "铺垫",
                "result": "张三开始调查",
                "original_text": "王五在咖啡厅里漫不经心地说着李四最近的活动，每一句话都在暗示李四的不可靠。张三握紧了咖啡杯。",
                "conflict_type": "权力斗争",
                "emotion_type": "警惕",
                "character_relationship": "商业对手",
                "time_position": "第一章",
                "chapter": 1
            },
            {
                "scene": "老房子",
                "characters": ["张三", "李四"],
                "core_conflict": "李四请求原谅",
                "emotion_curve": ["犹豫", "痛苦", "坚持"],
                "plot_function": "转折",
                "result": "张三拒绝沟通",
                "original_text": "李四来到两人小时候常去的老房子，跪在地上请求原谅。张三站在门口，冷冷地看着他，最终转身离开。",
                "conflict_type": "身份冲突",
                "emotion_type": "痛苦",
                "character_relationship": "兄弟决裂",
                "time_position": "第三章",
                "chapter": 3
            }
        ]

        self.test_data["story_unit_ids"] = []
        for unit_data in story_units:
            result = await self.request("POST", "/api/story-units", json=unit_data)
            if result["success"]:
                self.test_data["story_unit_ids"].append(result["data"]["id"])
                print(f"✓ 测试剧情单元已创建: {unit_data['scene']}")
            else:
                print(f"✗ 创建剧情单元失败: {unit_data['scene']} - {result.get('error')}")

    def record_evaluation(self, feature_name: str, metrics: Dict[str, Any], details: Dict[str, Any] = None):
        self.evaluation_results.append({
            "feature": feature_name,
            "metrics": metrics,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })

    async def evaluate_multi_index_fusion(self):
        print("\n" + "="*60)
        print("【评估1】多索引组合检索权重策略")
        print("="*60)

        test_queries = [
            {"query": "兄弟背叛", "conflict_type": "背叛", "emotion_type": "愤怒"},
            {"query": "商业竞争", "conflict_type": "权力斗争", "emotion_type": "警惕"},
            {"query": "求原谅", "conflict_type": "身份冲突", "emotion_type": "痛苦"}
        ]

        fusion_results = {
            "rrf": [],
            "linear": []
        }

        for query in test_queries:
            for fusion_method in ["rrf", "linear"]:
                params = {
                    **query,
                    "top_k": 5,
                    "fusion_method": fusion_method,
                    "vector_weight": 0.4 if fusion_method == "linear" else 0.5,
                    "metadata_weight": 0.6 if fusion_method == "linear" else 0.5,
                    "rrf_k": 60
                }
                result = await self.request("POST", "/api/story-units/search", json=params)
                if result["success"]:
                    fusion_results[fusion_method].append({
                        "query": query,
                        "results": result["data"].get("results", []),
                        "count": len(result["data"].get("results", []))
                    })

        rrf_count = sum(r["count"] for r in fusion_results["rrf"])
        linear_count = sum(r["count"] for r in fusion_results["linear"])

        rrf_avg = rrf_count / len(test_queries) if test_queries else 0
        linear_avg = linear_count / len(test_queries) if test_queries else 0

        stability_score = self._calculate_stability(fusion_results)

        metrics = {
            "rrf_avg_results": rrf_avg,
            "linear_avg_results": linear_avg,
            "stability_score": stability_score,
            "comparison": "RRF" if rrf_avg >= linear_avg else "Linear"
        }

        self.record_evaluation(
            "多索引组合检索权重策略",
            metrics,
            {"fusion_results": fusion_results}
        )

        print(f"✓ RRF 平均检索结果数: {rrf_avg:.1f}")
        print(f"✓ Linear 平均检索结果数: {linear_avg:.1f}")
        print(f"✓ 稳定性评分: {stability_score:.2f}")
        print(f"✓ 推荐方法: {metrics['comparison']}")
        print("="*60)

    def _calculate_stability(self, fusion_results: Dict) -> float:
        rrf_counts = [r["count"] for r in fusion_results["rrf"]]
        linear_counts = [r["count"] for r in fusion_results["linear"]]

        rrf_std = self._std_deviation(rrf_counts) if rrf_counts else 0
        linear_std = self._std_deviation(linear_counts) if linear_counts else 0

        return 1 - (rrf_std + linear_std) / 2

    def _std_deviation(self, values: List[float]) -> float:
        if not values:
            return 0
        avg = sum(values) / len(values)
        variance = sum((v - avg) ** 2 for v in values) / len(values)
        return variance ** 0.5

    async def evaluate_emotion_decay(self):
        print("\n" + "="*60)
        print("【评估2】情绪衰减机制")
        print("="*60)

        char_ids = self.test_data.get("character_ids", [])
        if len(char_ids) < 2:
            print("✗ 测试数据不足，跳过情绪衰减评估")
            return

        char_ids_list = list(char_ids[:2])

        char_names = []
        initial_emotions = {}
        for char_id in char_ids_list:
            char_result = await self.request("GET", f"/api/characters/{char_id}")
            if char_result["success"]:
                char_data = char_result.get("data", {})
                char_name = char_data.get("name")
                char_names.append(char_name)
                initial_emotions[char_name] = char_data.get("current_emotion")

        print("准备测试情绪：为角色添加初始情绪")
        test_emotions = [
            {"emotion_type": "愤怒", "intensity": 8.0, "decay_rate": 0.15},
            {"emotion_type": "悲伤", "intensity": 7.0, "decay_rate": 0.1}
        ]

        for i, char_name in enumerate(char_names):
            emotion_data = test_emotions[i]
            update_result = await self.request("POST", f"/api/characters/{char_name}/emotion", json=emotion_data)
            if update_result["success"]:
                print(f"✓ 已为角色 {char_name} 添加测试情绪: {emotion_data['emotion_type']}")

        await asyncio.sleep(0.5)

        pre_decay_emotions = {}
        for char_name in char_names:
            char_result = await self.request("GET", "/api/characters")
            if char_result["success"]:
                for char in char_result.get("data", []):
                    if char.get("name") == char_name:
                        pre_decay_emotions[char_name] = char.get("current_emotion")
                        import json
                        print(f"DEBUG pre_decay {char_name}: {json.dumps(char.get('current_emotion'), indent=2, ensure_ascii=False)}")
                        break

        decay_result = await self.request("POST", "/api/characters/decay-emotions", params={"time_offset_hours": 1.0})
        
        post_decay_emotions = {}
        for char_name in char_names:
            char_result = await self.request("GET", "/api/characters")
            if char_result["success"]:
                for char in char_result.get("data", []):
                    if char.get("name") == char_name:
                        post_decay_emotions[char_name] = char.get("current_emotion")
                        import json
                        print(f"DEBUG post_decay {char_name}: {json.dumps(char.get('current_emotion'), indent=2, ensure_ascii=False)}")
                        break

        metrics = {
            "decay_api_available": decay_result["success"],
            "characters_tested": len(char_names),
            "initial_emotions": initial_emotions,
            "pre_decay_emotions": pre_decay_emotions,
            "post_decay_emotions": post_decay_emotions
        }

        if decay_result["success"]:
            data = decay_result.get("data", {})
            metrics.update({
                "decayed_count": data.get("decayed_count", 0),
                "decay_results": data.get("results", [])
            })
            print(f"✓ 情绪衰减 API 可用")
            print(f"✓ 测试角色数: {len(char_names)}")
            print(f"✓ 成功衰减数: {data.get('decayed_count', 0)}")
            
            if pre_decay_emotions and post_decay_emotions:
                print("\n情绪衰减详情:")
                for char_name in char_names:
                    pre_emotions = pre_decay_emotions.get(char_name, {})
                    post_emotions = post_decay_emotions.get(char_name, {})
                    
                    print(f"  角色: {char_name}")
                    
                    if isinstance(pre_emotions, dict) and isinstance(post_emotions, dict):
                        for emotion_type in pre_emotions:
                            if emotion_type in post_emotions:
                                pre_emotion = pre_emotions[emotion_type]
                                post_emotion = post_emotions[emotion_type]
                                
                                if isinstance(pre_emotion, dict) and isinstance(post_emotion, dict):
                                    pre_intensity = pre_emotion.get("intensity", 0)
                                    post_intensity = post_emotion.get("intensity", 0)
                                    print(f"    {emotion_type}: {pre_intensity:.2f} → {post_intensity:.2f}")
                                elif isinstance(pre_emotion, str) and isinstance(post_emotion, str):
                                    print(f"    {emotion_type}: {pre_emotion} → {post_emotion}")
                                else:
                                    print(f"    {emotion_type}: 数据格式异常")
                            else:
                                pre_emotion = pre_emotions[emotion_type]
                                if isinstance(pre_emotion, dict):
                                    pre_intensity = pre_emotion.get("intensity", 0)
                                    print(f"    {emotion_type}: {pre_intensity:.2f} → (已移除)")
                                else:
                                    print(f"    {emotion_type}: {pre_emotion} → (已移除)")
                    else:
                        print(f"    数据格式异常: pre={type(pre_emotions)}, post={type(post_emotions)}")
        else:
            print(f"✗ 情绪衰减 API 不可用: {decay_result.get('error')}")

        self.record_evaluation(
            "情绪衰减机制",
            metrics,
            decay_result.get("data", {})
        )
        print("="*60)

    async def evaluate_goal_driven_generation(self):
        print("\n" + "="*60)
        print("【评估3】目标驱动的剧情生成")
        print("="*60)

        test_cases = [
            {
                "plot_context": "张三需要处理与李四的关系",
                "required_conflict": "身份冲突",
                "required_emotion": "犹豫",
                "characters": ["张三", "李四"],
                "scene": "老房子",
                "goal_driven": True
            },
            {
                "plot_context": "张三需要处理与李四的关系",
                "required_conflict": "身份冲突",
                "required_emotion": "犹豫",
                "characters": ["张三", "李四"],
                "scene": "老房子",
                "goal_driven": False
            }
        ]

        generation_results = {}

        for i, test_case in enumerate(test_cases):
            mode = "goal_driven" if test_case["goal_driven"] else "normal"
            result = await self.request("POST", "/api/generate-script", json=test_case)
            if result["success"]:
                data = result["data"]
                script = data.get("generated_script", "")
                generation_results[mode] = {
                    "script_length": len(script),
                    "has_goal_mention": "目标" in script or "目的" in script or "想要" in script,
                    "goal_driven": data.get("goal_driven", False),
                    "active_goals": data.get("active_goals", [])
                }

        metrics = {
            "goal_driven_available": "goal_driven" in generation_results,
            "normal_available": "normal" in generation_results,
            "goal_driven_length": generation_results.get("goal_driven", {}).get("script_length", 0),
            "normal_length": generation_results.get("normal", {}).get("script_length", 0),
            "goal_mention_in_driven": generation_results.get("goal_driven", {}).get("has_goal_mention", False),
            "goal_mention_in_normal": generation_results.get("normal", {}).get("has_goal_mention", False)
        }

        if generation_results:
            print(f"✓ 目标驱动生成可用")
            print(f"✓ 目标驱动模式字数: {metrics['goal_driven_length']}")
            print(f"✓ 常规模式字数: {metrics['normal_length']}")
            print(f"✓ 目标驱动模式提及目标: {metrics['goal_mention_in_driven']}")
            print(f"✓ 常规模式提及目标: {metrics['goal_mention_in_normal']}")
        else:
            print("✗ 剧本生成失败")

        self.record_evaluation(
            "目标驱动的剧情生成",
            metrics,
            generation_results
        )
        print("="*60)

    async def evaluate_conflict_resolution(self):
        print("\n" + "="*60)
        print("【评估4】多人物交互冲突协调")
        print("="*60)

        conflict_request = {
            "characters": ["张三", "李四"],
            "scene_context": "张三发现了李四背叛的证据，两人面对面"
        }

        result = await self.request("POST", "/api/resolve-conflicts", json=conflict_request)

        metrics = {
            "api_available": result["success"],
            "characters_involved": len(conflict_request["characters"])
        }

        if result["success"]:
            data = result["data"]
            metrics.update({
                "has_conflict_analysis": "conflict_analysis" in data,
                "has_resolution_suggestions": "resolution_suggestions" in data,
                "has_emotion_analysis": "emotion_analysis" in data
            })
            print(f"✓ 冲突协调 API 可用")
            print(f"✓ 包含冲突分析: {metrics['has_conflict_analysis']}")
            print(f"✓ 包含解决建议: {metrics['has_resolution_suggestions']}")
            print(f"✓ 包含情绪分析: {metrics['has_emotion_analysis']}")
        else:
            print(f"✗ 冲突协调 API 不可用: {result.get('error')}")

        self.record_evaluation(
            "多人物交互冲突协调",
            metrics,
            result.get("data", {})
        )
        print("="*60)

    async def evaluate_temporal_generation(self):
        print("\n" + "="*60)
        print("【评估5】时序关系自动生成")
        print("="*60)

        unit_ids = self.test_data.get("story_unit_ids", [])
        if len(unit_ids) < 2:
            print("✗ 测试数据不足，跳过时序生成评估")
            return

        source_id = unit_ids[0]
        target_id = unit_ids[1]

        result = await self.request("POST", "/api/temporal-relations/generate", json={
            "source_unit_id": source_id,
            "target_unit_id": target_id,
            "auto_update": False
        })

        metrics = {
            "api_available": result["success"],
            "has_temporal_relation": False
        }

        if result["success"]:
            data = result["data"]
            temporal_relation = data.get("temporal_relation", {})
            metrics.update({
                "has_temporal_relation": bool(temporal_relation),
                "has_confidence": "confidence" in temporal_relation,
                "confidence_score": temporal_relation.get("confidence", 0),
                "relation_type": temporal_relation.get("temporal_relation", "unknown")
            })
            print(f"✓ 时序生成 API 可用")
            print(f"✓ 时序关系类型: {metrics['relation_type']}")
            print(f"✓ 置信度: {metrics['confidence_score']}")
        else:
            print(f"✗ 时序生成 API 不可用: {result.get('error')}")

        self.record_evaluation(
            "时序关系自动生成",
            metrics,
            result.get("data", {})
        )

        batch_result = await self.request("POST", "/api/temporal-relations/batch-generate", json={
            "unit_ids": unit_ids[:min(3, len(unit_ids))],
            "update_threshold": 0.7
        })

        if batch_result["success"]:
            data = batch_result["data"]
            print(f"✓ 批量时序生成可用")
            print(f"✓ 处理对数: {data.get('total_pairs', 0)}")
            print(f"✓ 成功更新: {data.get('successful_updates', 0)}")
            print(f"✓ 平均置信度: {data.get('average_confidence', 0):.2f}")

        print("="*60)

    async def run_all_evaluations(self):
        print("="*60)
        print("AI漫剧RAG系统 - 新功能评估")
        print("="*60)
        print("\n准备测试数据...")
        await self.ensure_test_data()
        print("\n开始评估...\n")

        await self.evaluate_multi_index_fusion()
        await self.evaluate_emotion_decay()
        await self.evaluate_goal_driven_generation()
        await self.evaluate_conflict_resolution()
        await self.evaluate_temporal_generation()

        print("\n" + "="*60)
        print("评估完成")
        print("="*60)

    def generate_report(self):
        print("\n" + "="*60)
        print("评估报告")
        print("="*60)

        total_features = len(self.evaluation_results)
        available_features = sum(1 for r in self.evaluation_results if "api_available" not in r.get("metrics", {}) or r["metrics"]["api_available"])

        print(f"评估功能数: {total_features}")
        print(f"可用功能数: {available_features}")
        print(f"可用率: {available_features/total_features*100:.1f}%\n")

        print("详细评估结果:")
        for result in self.evaluation_results:
            feature_name = result["feature"]
            metrics = result["metrics"]
            
            print(f"\n【{feature_name}】")
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    print(f"  {key}: {value}")
                elif isinstance(value, list):
                    print(f"  {key}: {len(value)} 项")
                elif isinstance(value, dict):
                    print(f"  {key}: {list(value.keys())[:3]}...")
                else:
                    print(f"  {key}: {value}")

        print("\n" + "="*60)

        return {
            "total_features": total_features,
            "available_features": available_features,
            "availability_rate": available_features/total_features*100 if total_features > 0 else 0,
            "results": self.evaluation_results
        }

    async def save_report(self, filename: str = "evaluation_report.json"):
        report = self.generate_report()
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n详细报告已保存到 {filename}")


async def main():
    async with FeatureEvaluator() as evaluator:
        await evaluator.run_all_evaluations()
        await evaluator.save_report()


if __name__ == "__main__":
    asyncio.run(main())
