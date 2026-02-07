from typing import List, Dict, Any, Optional
import logging
import json
import re
import asyncio
from app.services.deepseek_client import RequestsDeepSeekLLM
from app.config import get_settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class QualityEvaluator:
    def __init__(self):
        settings = get_settings()
        if settings.ENABLE_DEEPSEEK and settings.DEEPSEEK_API_KEY:
            self.llm = RequestsDeepSeekLLM(
                model_name=settings.DEEPSEEK_MODEL,
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
                temperature=0.3,
                top_p=0.9,
                max_tokens=4096
            )
        else:
            from app.services.ollama_client import get_ollama_manager
            ollama_manager = get_ollama_manager()
            if not ollama_manager._initialized:
                ollama_manager.initialize()
            self.llm = ollama_manager.llm

    async def evaluate_script(
        self,
        script_content: str,
        plot_context: Optional[str] = None,
        characters: Optional[List[str]] = None,
        custom_weights: Optional[Dict[str, float]] = None,
        reference_script: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            logger.info(f"开始评估剧本质量...")

            weights = self._get_evaluation_weights(custom_weights)

            evaluation_results = {
                "conflict_intensity": await self._evaluate_conflict_intensity(script_content, plot_context),
                "emotion_rendering": await self._evaluate_emotion_rendering(script_content, plot_context),
                "character_consistency": await self._evaluate_character_consistency(script_content, characters),
                "dialogue_naturalness": await self._evaluate_dialogue_naturalness(script_content),
                "dramatic_tension": await self._evaluate_dramatic_tension(script_content, plot_context),
                "overall_coherence": await self._evaluate_overall_coherence(script_content, plot_context)
            }

            overall_score = self._calculate_overall_score(evaluation_results, weights)

            evaluation_results["overall_score"] = overall_score
            evaluation_results["weights_used"] = weights
            evaluation_results["quality_level"] = self._determine_quality_level(overall_score)

            if reference_script:
                comparison_score = await self._compare_with_reference(script_content, reference_script)
                evaluation_results["comparison_with_reference"] = comparison_score

            logger.info(f"剧本质量评估完成，总分: {overall_score:.2f}, 质量等级: {evaluation_results['quality_level']}")

            return evaluation_results

        except Exception as e:
            logger.error(f"剧本质量评估失败: {str(e)}")
            raise ValueError(f"Failed to evaluate script: {str(e)}") from e

    async def evaluate_batch(
        self,
        scripts: List[Dict[str, Any]],
        custom_weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        try:
            logger.info(f"开始批量评估 {len(scripts)} 个剧本...")

            results = []
            for i, script_data in enumerate(scripts):
                logger.info(f"评估剧本 {i+1}/{len(scripts)}...")
                result = await self.evaluate_script(
                    script_content=script_data.get("content", ""),
                    plot_context=script_data.get("plot_context"),
                    characters=script_data.get("characters"),
                    custom_weights=custom_weights
                )
                results.append({
                    "script_id": script_data.get("id", f"script_{i+1}"),
                    "evaluation": result
                })

            sorted_results = sorted(
                results,
                key=lambda x: x["evaluation"]["overall_score"],
                reverse=True
            )

            logger.info(f"批量评估完成，最佳剧本: {sorted_results[0]['script_id']}，分数: {sorted_results[0]['evaluation']['overall_score']:.2f}")

            return {
                "total_count": len(scripts),
                "results": results,
                "ranked_scripts": [r["script_id"] for r in sorted_results],
                "best_script": sorted_results[0] if sorted_results else None
            }

        except Exception as e:
            logger.error(f"批量评估失败: {str(e)}")
            raise ValueError(f"Failed to evaluate batch: {str(e)}") from e

    async def _evaluate_conflict_intensity(
        self,
        script_content: str,
        plot_context: Optional[str] = None
    ) -> Dict[str, Any]:
        prompt = self._build_conflict_intensity_prompt(script_content, plot_context)
        response = await asyncio.to_thread(self.llm.complete, prompt)
        return self._parse_score_response(response.text, "conflict_intensity")

    async def _evaluate_emotion_rendering(
        self,
        script_content: str,
        plot_context: Optional[str] = None
    ) -> Dict[str, Any]:
        prompt = self._build_emotion_rendering_prompt(script_content, plot_context)
        response = await asyncio.to_thread(self.llm.complete, prompt)
        return self._parse_score_response(response.text, "emotion_rendering")

    async def _evaluate_character_consistency(
        self,
        script_content: str,
        characters: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        prompt = self._build_character_consistency_prompt(script_content, characters)
        response = await asyncio.to_thread(self.llm.complete, prompt)
        return self._parse_score_response(response.text, "character_consistency")

    async def _evaluate_dialogue_naturalness(
        self,
        script_content: str
    ) -> Dict[str, Any]:
        prompt = self._build_dialogue_naturalness_prompt(script_content)
        response = await asyncio.to_thread(self.llm.complete, prompt)
        return self._parse_score_response(response.text, "dialogue_naturalness")

    async def _evaluate_dramatic_tension(
        self,
        script_content: str,
        plot_context: Optional[str] = None
    ) -> Dict[str, Any]:
        prompt = self._build_dramatic_tension_prompt(script_content, plot_context)
        response = await asyncio.to_thread(self.llm.complete, prompt)
        return self._parse_score_response(response.text, "dramatic_tension")

    async def _evaluate_overall_coherence(
        self,
        script_content: str,
        plot_context: Optional[str] = None
    ) -> Dict[str, Any]:
        prompt = self._build_overall_coherence_prompt(script_content, plot_context)
        response = await asyncio.to_thread(self.llm.complete, prompt)
        return self._parse_score_response(response.text, "overall_coherence")

    async def _compare_with_reference(
        self,
        script_content: str,
        reference_script: str
    ) -> Dict[str, Any]:
        prompt = self._build_comparison_prompt(script_content, reference_script)
        response = await asyncio.to_thread(self.llm.complete, prompt)
        return self._parse_score_response(response.text, "comparison")

    def _build_conflict_intensity_prompt(
        self,
        script_content: str,
        plot_context: Optional[str] = None
    ) -> str:
        context = f"\n剧情背景: {plot_context}" if plot_context else ""
        return f"""请评估以下剧本的冲突强度。

{context}

剧本内容:
{script_content}

请从以下维度评估:
1. 冲突的明确性和清晰度
2. 冲突的激烈程度
3. 冲突对剧情的推动作用
4. 冲突的合理性和可信度

请以JSON格式返回评估结果:
{{
  "score": 0-10的分数,
  "reasoning": "评分理由",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["不足1", "不足2"]
}}"""

    def _build_emotion_rendering_prompt(
        self,
        script_content: str,
        plot_context: Optional[str] = None
    ) -> str:
        context = f"\n剧情背景: {plot_context}" if plot_context else ""
        return f"""请评估以下剧本的情绪渲染效果。

{context}

剧本内容:
{script_content}

请从以下维度评估:
1. 情绪表达的准确性和恰当性
2. 情绪感染力和代入感
3. 情绪变化的层次和深度
4. 情绪与剧情的契合度

请以JSON格式返回评估结果:
{{
  "score": 0-10的分数,
  "reasoning": "评分理由",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["不足1", "不足2"]
}}"""

    def _build_character_consistency_prompt(
        self,
        script_content: str,
        characters: Optional[List[str]] = None
    ) -> str:
        char_list = ", ".join(characters) if characters else ""
        return f"""请评估以下剧本中人物的一致性。

出场人物: {char_list}

剧本内容:
{script_content}

请从以下维度评估:
1. 人物性格和行为的一致性
2. 人物对话风格的一致性
3. 人物动机和目标的合理性
4. 人物关系的合理性

请以JSON格式返回评估结果:
{{
  "score": 0-10的分数,
  "reasoning": "评分理由",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["不足1", "不足2"]
}}"""

    def _build_dialogue_naturalness_prompt(
        self,
        script_content: str
    ) -> str:
        return f"""请评估以下剧本中对话的自然度。

剧本内容:
{script_content}

请从以下维度评估:
1. 对话的真实性和生活感
2. 对话的流畅性和节奏
3. 对话符合人物身份和性格
4. 对话的信息传递效率

请以JSON格式返回评估结果:
{{
  "score": 0-10的分数,
  "reasoning": "评分理由",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["不足1", "不足2"]
}}"""

    def _build_dramatic_tension_prompt(
        self,
        script_content: str,
        plot_context: Optional[str] = None
    ) -> str:
        context = f"\n剧情背景: {plot_context}" if plot_context else ""
        return f"""请评估以下剧本的剧情张力。

{context}

剧本内容:
{script_content}

请从以下维度评估:
1. 剧情的吸引力和悬念设置
2. 节奏把控和张力营造
3. 高潮的冲击力
4. 观众的期待感

请以JSON格式返回评估结果:
{{
  "score": 0-10的分数,
  "reasoning": "评分理由",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["不足1", "不足2"]
}}"""

    def _build_overall_coherence_prompt(
        self,
        script_content: str,
        plot_context: Optional[str] = None
    ) -> str:
        context = f"\n剧情背景: {plot_context}" if plot_context else ""
        return f"""请评估以下剧本的整体连贯性。

{context}

剧本内容:
{script_content}

请从以下维度评估:
1. 剧情逻辑的合理性
2. 场景衔接的流畅性
3. 因果关系的清晰度
4. 结构的完整性

请以JSON格式返回评估结果:
{{
  "score": 0-10的分数,
  "reasoning": "评分理由",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["不足1", "不足2"]
}}"""

    def _build_comparison_prompt(
        self,
        script_content: str,
        reference_script: str
    ) -> str:
        return f"""请比较以下两个剧本的质量。

参考剧本:
{reference_script}

待评估剧本:
{script_content}

请评估待评估剧本相对于参考剧本的质量:
1. 0-5分: 明显更差
2. 5-7分: 稍差或相当
3. 7-8分: 稍好
4. 8-10分: 明显更好

请以JSON格式返回评估结果:
{{
  "score": 0-10的分数,
  "reasoning": "评分理由",
  "comparison": ["相对优点1", "相对不足1"]
}}"""

    def _parse_score_response(self, response: str, dimension: str) -> Dict[str, Any]:
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
                score = float(result.get("score", 5.0))
                return {
                    "score": min(10.0, max(0.0, score)),
                    "reasoning": result.get("reasoning", ""),
                    "strengths": result.get("strengths", []),
                    "weaknesses": result.get("weaknesses", [])
                }
        except Exception as e:
            logger.warning(f"解析{dimension}评分失败: {str(e)}")

        return {
            "score": 5.0,
            "reasoning": "无法解析评估结果，使用默认分数",
            "strengths": [],
            "weaknesses": []
        }

    def _get_evaluation_weights(self, custom_weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        default_weights = {
            "conflict_intensity": 0.20,
            "emotion_rendering": 0.15,
            "character_consistency": 0.20,
            "dialogue_naturalness": 0.15,
            "dramatic_tension": 0.15,
            "overall_coherence": 0.15
        }

        if custom_weights:
            total_weight = sum(custom_weights.values())
            if total_weight > 0:
                for key in custom_weights:
                    if key in default_weights:
                        default_weights[key] = custom_weights[key] / total_weight * sum(default_weights.values())

        return default_weights

    def _calculate_overall_score(
        self,
        evaluation_results: Dict[str, Any],
        weights: Dict[str, float]
    ) -> float:
        total_score = 0.0
        total_weight = 0.0

        for dimension, weight in weights.items():
            if dimension in evaluation_results:
                score = evaluation_results[dimension].get("score", 5.0)
                total_score += score * weight
                total_weight += weight

        if total_weight > 0:
            return round(total_score / total_weight, 2)
        return 5.0

    def _determine_quality_level(self, overall_score: float) -> str:
        if overall_score >= 8.0:
            return "excellent"
        elif overall_score >= 6.5:
            return "good"
        elif overall_score >= 5.0:
            return "acceptable"
        else:
            return "poor"

    def get_metrics_description(self) -> Dict[str, Any]:
        return {
            "metrics": [
                {
                    "name": "conflict_intensity",
                    "display_name": "冲突强度",
                    "description": "评估冲突的明确性、激烈程度和对剧情的推动作用",
                    "weight": 0.20,
                    "score_range": "0-10"
                },
                {
                    "name": "emotion_rendering",
                    "display_name": "情绪渲染",
                    "description": "评估情绪表达的准确性、感染力和与剧情的契合度",
                    "weight": 0.15,
                    "score_range": "0-10"
                },
                {
                    "name": "character_consistency",
                    "display_name": "人物一致性",
                    "description": "评估人物性格、行为和对话风格的一致性",
                    "weight": 0.20,
                    "score_range": "0-10"
                },
                {
                    "name": "dialogue_naturalness",
                    "display_name": "对话自然度",
                    "description": "评估对话的真实性、流畅性和信息传递效率",
                    "weight": 0.15,
                    "score_range": "0-10"
                },
                {
                    "name": "dramatic_tension",
                    "display_name": "剧情张力",
                    "description": "评估剧本的吸引力、节奏感和悬念设置",
                    "weight": 0.15,
                    "score_range": "0-10"
                },
                {
                    "name": "overall_coherence",
                    "display_name": "整体连贯性",
                    "description": "评估剧情逻辑、场景衔接和因果关系的清晰度",
                    "weight": 0.15,
                    "score_range": "0-10"
                }
            ],
            "overall_score": {
                "display_name": "综合评分",
                "description": "各维度评分的加权平均值",
                "score_range": "0-10"
            },
            "quality_thresholds": {
                "excellent": "8.0-10.0",
                "good": "6.5-7.9",
                "acceptable": "5.0-6.4",
                "poor": "0.0-4.9"
            }
        }


quality_evaluator = QualityEvaluator()
