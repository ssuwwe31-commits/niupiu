from typing import List, Optional, Dict, Any
import json
import re
import logging
from app.services.deepseek_client import RequestsDeepSeekLLM
from app.services.character_system import character_system
from app.config import get_settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ScriptService:
    def __init__(self):
        settings = get_settings()
        if settings.ENABLE_DEEPSEEK and settings.DEEPSEEK_API_KEY:
            self.llm = RequestsDeepSeekLLM(
                model_name=settings.DEEPSEEK_MODEL,
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
                temperature=0.7,
                top_p=0.95,
                max_tokens=8192
            )
        else:
            from app.services.ollama_client import get_ollama_manager
            ollama_manager = get_ollama_manager()
            if not ollama_manager._initialized:
                ollama_manager.initialize()
            self.llm = ollama_manager.llm_long_timeout
        self._character_system_initialized = False

    async def generate_script(
        self,
        plot_context: str,
        required_conflict: str,
        required_emotion: str,
        characters: List[str],
        scene: Optional[str] = None,
        constraints: Optional[Dict[str, Any]] = None,
        goal_driven: bool = False,
        use_character_system: bool = True,
        style: str = "standard",
        length: str = "medium",
        innovation_degree: float = 0.5,
        enable_quality_evaluation: bool = False,
    ) -> Dict[str, Any]:
        """
        使用 DeepSeek 生成剧本

        Args:
            plot_context: 剧情上下文
            required_conflict: 需要的冲突类型
            required_emotion: 需要的情绪类型
            characters: 出场人物列表
            scene: 场景描述
            constraints: 生成约束
            goal_driven: 是否启用目标驱动生成
            use_character_system: 是否使用人物系统
            style: 剧本风格
            length: 剧本长度
            innovation_degree: 创新程度

        Returns:
            生成的剧本结果
        """
        try:
            logger.info(f"开始生成剧本: plot_context={plot_context[:30]}...")
            
            if use_character_system:
                if not self._character_system_initialized:
                    await character_system.initialize()
                    self._character_system_initialized = True
                
                logger.info(f"加载人物状态...")
                character_states = await character_system.load_multiple_characters(characters)
                logger.info(f"加载了 {len(character_states)} 个人物状态")

            logger.info(f"搜索剧情单元...")
            referenced_units = await self._search_story_units(
                query=plot_context,
                conflict_type=required_conflict,
                emotion_type=required_emotion,
                top_k=3
            )
            logger.info(f"找到 {len(referenced_units)} 个参考剧情单元")

            logger.info(f"获取人物约束...")
            if use_character_system and character_states:
                character_constraints = character_system.get_character_constraints_for_generation(characters)
            else:
                character_constraints = await self._get_character_constraints(characters)
            logger.info(f"找到 {len(character_constraints)} 个人物约束")

            character_context = ""
            goal_context = ""
            active_goals = []
            temporal_context = {}

            if character_constraints:
                character_context = "\n人物设定：\n"
                for name, info in character_constraints.items():
                    character_context += f"\n{name}:\n"
                    if info.get("core_personality"):
                        character_context += f"  - 核心性格: {info['core_personality']}\n"
                    if info.get("background"):
                        character_context += f"  - 背景: {info['background']}\n"
                    if info.get("bottom_line"):
                        character_context += f"  - 底线: {info['bottom_line']}\n"
                    if info.get("dominant_emotion"):
                        character_context += f"  - 当前情绪: {info['dominant_emotion']}\n"
                    if use_character_system and name in character_states:
                        char_state = character_states[name]
                        active_goals_list = char_state.get_active_goals()
                        if active_goals_list.get("short_term") or active_goals_list.get("long_term"):
                            active_goals.append({
                                "character": name,
                                "short_term": active_goals_list.get("short_term", []),
                                "long_term": active_goals_list.get("long_term", [])
                            })
                            temporal_context[name] = {
                                "dominant_emotion": char_state.get_dominant_emotion(),
                                "relationships": char_state.relationships
                            }
                    else:
                        if info.get("relationships"):
                            character_context += f"  - 关系: {info['relationships']}\n"

                        if goal_driven and info.get("goals"):
                            goals = info['goals']
                            if isinstance(goals, dict):
                                short_term_goals = goals.get("short", [])
                                long_term_goals = goals.get("long", [])
                                if short_term_goals or long_term_goals:
                                    active_goals.append({
                                        "character": name,
                                        "short_term": short_term_goals,
                                        "long_term": long_term_goals
                                    })

            if goal_driven and active_goals:
                goal_context = "\n目标驱动设定：\n"
                for goal_info in active_goals:
                    goal_context += f"\n{goal_info['character']}:\n"
                    if goal_info['short_term']:
                        goal_context += f"  - 短期目标: {', '.join(goal_info['short_term'])}\n"
                    if goal_info['long_term']:
                        goal_context += f"  - 长期目标: {', '.join(goal_info['long_term'])}\n"

            reference_context = "\n\n".join([
                f"参考剧情{idx+1}:\n{unit['text']}"
                for idx, unit in enumerate(referenced_units)
            ])

            if goal_driven:
                prompt = self._build_goal_driven_prompt(
                    plot_context=plot_context,
                    character_context=character_context,
                    goal_context=goal_context,
                    required_conflict=required_conflict,
                    required_emotion=required_emotion,
                    scene=scene,
                    reference_context=reference_context,
                    constraints=constraints
                )
            else:
                prompt = self._build_standard_prompt(
                    plot_context=plot_context,
                    character_context=character_context,
                    required_conflict=required_conflict,
                    required_emotion=required_emotion,
                    scene=scene,
                    reference_context=reference_context,
                    constraints=constraints
                )

            logger.info(f"调用 DeepSeek API 生成剧本 (prompt 长度: {len(prompt)} 字符)...")
            generated_script = await self._call_deepseek(prompt)
            logger.info(f"DeepSeek API 返回 (生成剧本长度: {len(generated_script)} 字符)")

            if use_character_system and character_states:
                await self._update_character_states_after_generation(
                    character_states, required_emotion
                )

            result = {
                "generated_script": generated_script,
                "referenced_units": [unit["id"] for unit in referenced_units],
                "applied_character_constraints": list(character_constraints.keys()),
                "goal_driven": goal_driven,
                "active_goals": active_goals,
                "temporal_context": temporal_context if temporal_context else None,
                "confidence": 0.85,
                "style": style,
                "length": length,
                "innovation_degree": innovation_degree,
            }

            if enable_quality_evaluation:
                from app.services.quality_evaluator import quality_evaluator
                evaluation = await quality_evaluator.evaluate_script(
                    script_content=generated_script,
                    plot_context=plot_context,
                    characters=characters
                )
                result["quality_evaluation"] = evaluation
                logger.info(f"质量评估完成，综合评分: {evaluation.get('overall_score', 0)}")

            return result
        except Exception as e:
            logger.error(f"Failed to generate script: {str(e)}")
            raise RuntimeError(f"Failed to generate script: {str(e)}") from e

    def _build_standard_prompt(
        self,
        plot_context: str,
        character_context: str,
        required_conflict: str,
        required_emotion: str,
        scene: Optional[str],
        reference_context: str,
        constraints: Optional[Dict[str, Any]],
        style: str = "standard",
        length: str = "medium",
        innovation_degree: float = 0.5,
    ) -> str:
        """构建标准剧本生成 Prompt"""
        style_descriptions = {
            "standard": "标准风格",
            "humorous": "幽默风格，适当加入轻松诙谐的元素",
            "serious": "严肃风格，注重深度和情感表达",
            "romantic": "浪漫风格，突出情感和氛围"
        }
        
        length_ranges = {
            "short": "300-500字",
            "medium": "500-800字",
            "long": "800-1200字"
        }
        
        innovation_guidance = ""
        if innovation_degree < 0.3:
            innovation_guidance = "保持保守风格，贴近参考剧情的常规发展模式"
        elif innovation_degree > 0.7:
            innovation_guidance = "勇于创新，突破常规情节模式，创造意想不到的发展"
        else:
            innovation_guidance = "在参考和创新之间取得平衡"
        
        prompt = f"""请根据以下信息生成一场戏的剧本：

剧情上下文：
{plot_context}
{character_context}
需要的冲突类型：{required_conflict}
需要的情绪类型：{required_emotion}
场景：{scene if scene else '请根据剧情设定'}

参考剧情片段：
{reference_context}

生成要求：
1. 符合指定的冲突类型和情绪类型
2. 严格遵循人物设定，保持人物性格、关系和情绪的一致性
3. 对话自然，符合人物性格和当前状态
4. 有明确的戏剧张力
5. 剧本风格：{style_descriptions.get(style, style)}
6. 字数控制在{length_ranges.get(length, "500-800字")}
7. 剧本必须原创，不能直接复制参考内容
8. 创新指引：{innovation_guidance}
"""

        if constraints:
            prompt += f"\n额外约束：\n"
            for key, value in constraints.items():
                prompt += f"- {key}: {value}\n"

        prompt += "\n请生成剧本："
        return prompt

    def _build_goal_driven_prompt(
        self,
        plot_context: str,
        character_context: str,
        goal_context: str,
        required_conflict: str,
        required_emotion: str,
        scene: Optional[str],
        reference_context: str,
        constraints: Optional[Dict[str, Any]],
        style: str = "standard",
        length: str = "medium",
        innovation_degree: float = 0.5,
    ) -> str:
        """构建目标驱动的剧本生成 Prompt"""
        style_descriptions = {
            "standard": "标准风格",
            "humorous": "幽默风格，适当加入轻松诙谐的元素",
            "serious": "严肃风格，注重深度和情感表达",
            "romantic": "浪漫风格，突出情感和氛围"
        }
        
        length_ranges = {
            "short": "300-500字",
            "medium": "500-800字",
            "long": "800-1200字"
        }
        
        innovation_guidance = ""
        if innovation_degree < 0.3:
            innovation_guidance = "保持保守风格，贴近参考剧情的常规发展模式"
        elif innovation_degree > 0.7:
            innovation_guidance = "勇于创新，突破常规情节模式，创造意想不到的发展"
        else:
            innovation_guidance = "在参考和创新之间取得平衡"
        
        prompt = f"""请根据以下信息生成一场戏的剧本：

剧情上下文：
{plot_context}
{character_context}
{goal_context}
需要的冲突类型：{required_conflict}
需要的情绪类型：{required_emotion}
场景：{scene if scene else '请根据剧情设定'}

参考剧情片段：
{reference_context}

生成要求（目标驱动模式）：
1. 剧情必须围绕角色的目标展开，角色的行为和对话应该服务于目标实现
2. 利用角色目标之间的冲突创造戏剧张力
3. 冲突应该由角色目标驱动而非外部事件
4. 严格遵循人物设定，保持人物性格、关系和情绪的一致性
5. 让角色在追求目标的过程中做出符合性格的选择
6. 剧本风格：{style_descriptions.get(style, style)}
7. 字数控制在{length_ranges.get(length, "500-800字")}
8. 剧本必须原创，不能直接复制参考内容
9. 创新指引：{innovation_guidance}
"""

        if constraints:
            prompt += f"\n额外约束：\n"
            for key, value in constraints.items():
                prompt += f"- {key}: {value}\n"

        prompt += "\n请生成剧本："
        return prompt

    async def _search_story_units(
        self,
        query: Optional[str] = None,
        conflict_type: Optional[str] = None,
        emotion_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """搜索剧情单元"""
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from app.models.story_unit import StoryUnit
        from app.config import get_settings

        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        results = []

        async with async_session() as session:
            stmt = select(StoryUnit).limit(top_k)
            
            if conflict_type:
                stmt = stmt.where(StoryUnit.conflict_type == conflict_type)
            if emotion_type:
                stmt = stmt.where(StoryUnit.emotion_type == emotion_type)
            
            result = await session.execute(stmt)
            story_units = result.scalars().all()
            results = [{"id": str(unit.id), "text": unit.original_text, "score": 0.0} for unit in story_units]

        return results

    async def _call_deepseek(self, prompt: str) -> str:
        """调用 LLM API 生成剧本"""
        try:
            response = self.llm.complete(prompt)
            return response.text
        except Exception as e:
            logger.error(f"LLM API call failed: {str(e)}")
            raise RuntimeError(f"LLM API call failed: {str(e)}") from e

    async def _update_character_states_after_generation(
        self,
        character_states: Dict[str, Any],
        scene_emotion: str
    ):
        """在剧本生成后更新人物状态"""
        for name, char_state in character_states.items():
            try:
                char_state.add_emotion(scene_emotion, intensity=0.7)
                await character_system.save_character_state(name)
                logger.info(f"Updated character state for {name}")
            except Exception as e:
                logger.error(f"Failed to update character state for {name}: {str(e)}")

    async def _get_character_constraints(self, characters: List[str]) -> Dict[str, Any]:
        """获取人物约束信息"""
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import select
        from app.models.character import Character
        from app.config import get_settings

        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        character_constraints = {}
        async with async_session() as session:
            for character_name in characters:
                stmt = select(Character).where(Character.name == character_name)
                result = await session.execute(stmt)
                character = result.scalar_one_or_none()
                if character:
                    character_constraints[character_name] = {
                        "core_personality": character.core_personality,
                        "background": character.background,
                        "bottom_line": character.bottom_line,
                        "current_emotion": character.current_emotion,
                        "relationships": character.relationships,
                        "goals": character.goals
                    }

        return character_constraints

    async def evaluate_script_quality(self, script: str, constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        评估剧本质量

        Args:
            script: 待评估的剧本
            constraints: 生成约束

        Returns:
            评估结果
        """
        evaluation_prompt = f"""请对以下生成的剧本进行质量评估，按照以下维度打分（1-10分）：

剧本内容：
{script}

评估维度：
1. 冲突强度 - 剧本是否展现出强烈的戏剧冲突
2. 情绪渲染 - 情绪表达是否到位，能否引起共鸣
3. 人物一致性 - 人物性格、对话是否符合其设定
4. 对话自然度 - 对话是否流畅自然，符合人物口吻
5. 戏剧张力 - 剧本是否有足够的吸引力和张力
6. 情节连贯性 - 剧情发展是否逻辑连贯
7. 字数控制 - 是否符合字数要求（500-800字）

请以JSON格式返回评估结果：
{{
    "conflict_intensity": 分数,
    "emotion_rendering": 分数,
    "character_consistency": 分数,
    "dialogue_naturalness": 分数,
    "dramatic_tension": 分数,
    "plot_coherence": 分数,
    "word_count_control": 分数,
    "overall_score": 分数,
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["不足1", "不足2"],
    "suggestions": ["改进建议1", "改进建议2"]
}}
"""

        try:
            generated_script = await self._call_deepseek(evaluation_prompt)
            
            json_match = re.search(r'\{[\s\S]*\}', generated_script)
            if json_match:
                evaluation_data = json.loads(json_match.group())

                for key in ["conflict_intensity", "emotion_rendering", "character_consistency", "dialogue_naturalness", "dramatic_tension", "plot_coherence", "word_count_control"]:
                    if key in evaluation_data and isinstance(evaluation_data[key], (int, float)):
                        evaluation_data[key] = int(evaluation_data[key])

                overall_score = evaluation_data.get("overall_score", 0)
                evaluation_data["quality_level"] = self._get_quality_level(overall_score)

                return evaluation_data
            else:
                return self._get_default_evaluation()
        except Exception as e:
            logger.error(f"Failed to evaluate script quality: {str(e)}")
            return self._get_default_evaluation()

    def _get_quality_level(self, score: float) -> str:
        """根据分数获取质量等级"""
        if score >= 8.5:
            return "优秀"
        elif score >= 7.0:
            return "良好"
        elif score >= 5.5:
            return "合格"
        elif score >= 4.0:
            return "一般"
        else:
            return "需要改进"

    def _get_default_evaluation(self) -> Dict[str, Any]:
        """获取默认评估结果"""
        return {
            "conflict_intensity": 5,
            "emotion_rendering": 5,
            "character_consistency": 5,
            "dialogue_naturalness": 5,
            "dramatic_tension": 5,
            "plot_coherence": 5,
            "word_count_control": 5,
            "overall_score": 5.0,
            "quality_level": "一般",
            "strengths": [],
            "weaknesses": ["评估失败，无法提供具体建议"],
            "suggestions": []
        }

    async def generate_script_batch(
        self,
        plot_context: str,
        required_conflict: str,
        required_emotion: str,
        characters: List[str],
        scene: Optional[str] = None,
        constraints: Optional[Dict[str, Any]] = None,
        goal_driven: bool = False,
        use_character_system: bool = True,
        style: str = "standard",
        length: str = "medium",
        innovation_degree: float = 0.5,
        batch_size: int = 3,
        return_best_only: bool = False,
        enable_quality_evaluation: bool = True,
        min_score_threshold: float = 6.0,
    ) -> Dict[str, Any]:
        """
        批次生成剧本

        Args:
            plot_context: 剧情上下文
            required_conflict: 需要的冲突类型
            required_emotion: 需要的情绪类型
            characters: 出场人物列表
            scene: 场景描述
            constraints: 生成约束
            goal_driven: 是否启用目标驱动生成
            use_character_system: 是否使用人物系统
            style: 剧本风格
            length: 剧本长度
            innovation_degree: 创新程度
            batch_size: 批次生成数量（1-10）
            return_best_only: 是否仅返回最佳剧本
            enable_quality_evaluation: 是否启用质量评估
            min_score_threshold: 最低合格分数（仅用于筛选）

        Returns:
            批次生成结果
        """
        import time
        start_time = time.time()
        scripts = []
        evaluations = []

        for i in range(batch_size):
            try:
                result = await self.generate_script(
                    plot_context=plot_context,
                    required_conflict=required_conflict,
                    required_emotion=required_emotion,
                    characters=characters,
                    scene=scene,
                    constraints=constraints,
                    goal_driven=goal_driven,
                    use_character_system=use_character_system,
                    style=style,
                    length=length,
                    innovation_degree=innovation_degree,
                )
                scripts.append(result)
                
                if enable_quality_evaluation:
                    from app.services.quality_evaluator import quality_evaluator
                    evaluation = await quality_evaluator.evaluate_script(
                        script_content=result["generated_script"],
                        plot_context=plot_context,
                        characters=characters
                    )
                    evaluations.append(evaluation)
                    logger.info(f"Generated script {i+1}/{batch_size}, overall_score: {evaluation.get('overall_score', 0)}")
                else:
                    evaluation = await self.evaluate_script_quality(
                        script=result["generated_script"],
                        constraints=constraints
                    )
                    evaluations.append(evaluation)
                    logger.info(f"Generated script {i+1}/{batch_size}, overall_score: {evaluation.get('overall_score', 0)}")
            except Exception as e:
                logger.error(f"Failed to generate script {i+1}/{batch_size}: {str(e)}")

        generation_time = time.time() - start_time

        if not scripts:
            return {
                "scripts": [],
                "best_script_index": None,
                "total_count": 0,
                "generation_time_seconds": generation_time
            }

        best_index = max(range(len(evaluations)), key=lambda i: evaluations[i].get("overall_score", 0))

        if return_best_only:
            return {
                "scripts": [scripts[best_index]],
                "best_script_index": 0,
                "total_count": 1,
                "generation_time_seconds": generation_time,
                "evaluation": evaluations[best_index] if evaluations else None
            }

        return {
            "scripts": scripts,
            "best_script_index": best_index,
            "total_count": len(scripts),
            "generation_time_seconds": generation_time,
            "evaluations": evaluations if enable_quality_evaluation else None
        }


script_service = ScriptService()
