from typing import List, Dict, Any, Optional
import logging
import json
import uuid
from app.services.deepseek_client import RequestsDeepSeekLLM
from app.services.ollama_client import get_ollama_manager
from app.config import get_settings
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class StoryStructureTemplate:
    """剧情结构模板基类"""
    
    def get_structure_name(self) -> str:
        raise NotImplementedError
    
    def get_phase_names(self) -> List[str]:
        raise NotImplementedError
    
    def get_phase_description(self, phase_name: str) -> str:
        raise NotImplementedError
    
    def get_default_scene_count(self, phase_name: str) -> int:
        raise NotImplementedError


class ThreeActStructure(StoryStructureTemplate):
    """三幕式结构模板"""
    
    def get_structure_name(self) -> str:
        return "three_act"
    
    def get_phase_names(self) -> List[str]:
        return ["setup", "confrontation", "resolution"]
    
    def get_phase_description(self, phase_name: str) -> str:
        descriptions = {
            "setup": "铺垫阶段：介绍主角、世界观、初始状态，激励事件发生",
            "confrontation": "对抗阶段：主角面对挑战和障碍，情节升级，进入高潮",
            "resolution": "解决阶段：高潮之后的余波，主角获得成长或改变"
        }
        return descriptions.get(phase_name, "")
    
    def get_default_scene_count(self, phase_name: str) -> int:
        counts = {
            "setup": 3,
            "confrontation": 5,
            "resolution": 2
        }
        return counts.get(phase_name, 2)


class HeroJourneyStructure(StoryStructureTemplate):
    """英雄之旅模板"""
    
    def get_structure_name(self) -> str:
        return "hero_journey"
    
    def get_phase_names(self) -> List[str]:
        return [
            "ordinary_world",
            "call_to_adventure",
            "refusal",
            "meeting_mentor",
            "crossing_threshold",
            "tests_allies_enemies",
            "approach",
            "ordeal",
            "reward",
            "road_back",
            "resurrection",
            "return_with_elixir"
        ]
    
    def get_phase_description(self, phase_name: str) -> str:
        descriptions = {
            "ordinary_world": "平凡世界：展示主角的日常和现状",
            "call_to_adventure": "冒险召唤：激励事件发生，打破平衡",
            "refusal": "拒绝召唤：主角犹豫或抗拒",
            "meeting_mentor": "遇见导师：导师提供指导或工具",
            "crossing_threshold": "跨越门槛：进入特殊世界",
            "tests_allies_enemies": "试炼盟友敌人：学习规则，面对挑战",
            "approach": "接近目标：准备迎接终极挑战",
            "ordeal": "严峻考验：生死攸关的高潮",
            "reward": "获得奖赏：成功后的收获",
            "road_back": "回归之路：返回平凡世界的旅程",
            "resurrection": "复活重生：最后的考验和蜕变",
            "return_with_elixir": "带着灵药归来：带着改变回到起点"
        }
        return descriptions.get(phase_name, "")
    
    def get_default_scene_count(self, phase_name: str) -> str:
        counts = {
            "ordinary_world": 2,
            "call_to_adventure": 1,
            "refusal": 1,
            "meeting_mentor": 1,
            "crossing_threshold": 1,
            "tests_allies_enemies": 3,
            "approach": 2,
            "ordeal": 2,
            "reward": 1,
            "road_back": 1,
            "resurrection": 1,
            "return_with_elixir": 1
        }
        return counts.get(phase_name, 1)


class StoryPlannerService:
    """剧情规划服务"""
    
    STRUCTURE_TEMPLATES = {
        "three_act": ThreeActStructure,
        "hero_journey": HeroJourneyStructure
    }
    
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
            ollama_manager = get_ollama_manager()
            if not ollama_manager._initialized:
                ollama_manager.initialize()
            self.llm = ollama_manager.llm_long_timeout
    
    def get_available_structure_templates(self) -> List[Dict[str, Any]]:
        """获取可用的剧情结构模板"""
        templates = []
        for key, template_class in self.STRUCTURE_TEMPLATES.items():
            template = template_class()
            templates.append({
                "id": template.get_structure_name(),
                "name": template.get_structure_name(),
                "phases": [
                    {
                        "name": phase,
                        "description": template.get_phase_description(phase),
                        "default_scene_count": template.get_default_scene_count(phase)
                    }
                    for phase in template.get_phase_names()
                ]
            })
        return templates
    
    async def generate_story_plan(
        self,
        story_outline: str,
        characters: List[str],
        structure_type: str = "three_act",
        total_scene_count: Optional[int] = None,
        custom_phase_distribution: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        生成剧情规划
        
        Args:
            story_outline: 故事梗概
            characters: 人物列表
            structure_type: 剧情结构类型
            total_scene_count: 总场次数量
            custom_phase_distribution: 自定义各阶段场次分布
        
        Returns:
            剧情规划结果
        """
        try:
            logger.info(f"开始生成剧情规划: story_outline={story_outline[:50]}...")
            
            if structure_type not in self.STRUCTURE_TEMPLATES:
                raise ValueError(f"Unknown structure type: {structure_type}")
            
            template_class = self.STRUCTURE_TEMPLATES[structure_type]
            template = template_class()
            
            phases = template.get_phase_names()
            
            if custom_phase_distribution:
                phase_scene_counts = custom_phase_distribution
            else:
                total_count = total_scene_count or sum(
                    template.get_default_scene_count(phase) for phase in phases
                )
                default_counts = {
                    phase: template.get_default_scene_count(phase)
                    for phase in phases
                }
                total_default = sum(default_counts.values())
                phase_scene_counts = {
                    phase: max(1, int(count * total_count / total_default))
                    for phase, count in default_counts.items()
                }
            
            logger.info(f"生成阶段提示词...")
            scene_plans = await self._generate_scene_plans(
                story_outline=story_outline,
                characters=characters,
                template=template,
                phase_scene_counts=phase_scene_counts
            )
            
            result = {
                "plan_id": None,
                "story_outline": story_outline,
                "characters": characters,
                "structure_type": structure_type,
                "created_at": datetime.utcnow().isoformat(),
                "phases": [],
                "total_scene_count": len(scene_plans)
            }
            
            current_scene_index = 0
            for phase in phases:
                phase_scenes = [
                    scene for scene in scene_plans
                    if scene.get("phase") == phase
                ]
                result["phases"].append({
                    "name": phase,
                    "description": template.get_phase_description(phase),
                    "scene_count": len(phase_scenes),
                    "scenes": phase_scenes
                })
                current_scene_index += len(phase_scenes)
            
            logger.info(f"剧情规划生成完成，共 {len(scene_plans)} 场戏")
            
            from app.db.database import get_db
            from app.db.story_plan_crud import StoryPlanCRUD
            
            async for db in get_db():
                title = f"剧情规划-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                plan = await StoryPlanCRUD.create(
                    db=db,
                    title=title,
                    story_outline=story_outline,
                    characters=characters,
                    structure_type=structure_type,
                    phases_data=result["phases"],
                    total_scene_count=len(scene_plans)
                )
                result["plan_id"] = str(plan.id)
                logger.info(f"剧情规划已保存到数据库: {result['plan_id']}")
                return result
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate story plan: {str(e)}")
            raise RuntimeError(f"Failed to generate story plan: {str(e)}") from e
    
    async def _generate_scene_plans(
        self,
        story_outline: str,
        characters: List[str],
        template: StoryStructureTemplate,
        phase_scene_counts: Dict[str, int]
    ) -> List[Dict[str, Any]]:
        """生成每场戏的规划"""
        
        phases_info = []
        for phase, count in phase_scene_counts.items():
            phases_info.append({
                "phase": phase,
                "description": template.get_phase_description(phase),
                "scene_count": count
            })
        
        characters_str = ", ".join(characters)
        
        prompt = f"""请根据以下信息，规划一个完整的故事剧情大纲。

故事梗概：
{story_outline}

主要人物：
{characters_str}

剧情结构要求：
{self._format_phases_info(phases_info)}

请为每场戏规划以下内容：
1. 场次序号（如：Scene 1）
2. 所属阶段（如：setup）
3. 场景描述（时间、地点）
4. 核心冲突（这场戏的主要冲突是什么）
5. 情绪目标（这场戏想要传达的情绪）
6. 主要人物（哪些人物出场）
7. 剧情功能（这场戏在整体剧情中的作用）
8. 关键事件（这场戏发生的关键事件）

请以 JSON 格式返回，格式如下：
{{
  "scenes": [
    {{
      "scene_number": 1,
      "phase": "setup",
      "scene_description": "早晨，主角家中",
      "core_conflict": "主角与家人的冲突",
      "emotion_goal": "焦虑、压抑",
      "main_characters": ["主角", "母亲"],
      "plot_function": "介绍主角的背景和动机",
      "key_event": "主角收到神秘信件"
    }}
  ]
}}

注意：
- 每场戏的剧情要连贯，符合故事梗概
- 冲突要逐步升级
- 人物行为要符合设定
- 确保每个阶段的功能完整
"""
        
        logger.info(f"调用 LLM 生成剧情规划...")
        response = await self._call_llm(prompt)
        logger.info(f"LLM 返回响应 (长度: {len(response)} 字符)")
        
        scenes = self._parse_scene_plans(response)
        
        scene_plans = []
        for i, scene in enumerate(scenes, 1):
            scene_plans.append({
                "scene_number": i,
                "phase": scene.get("phase", ""),
                "scene_description": scene.get("scene_description", ""),
                "core_conflict": scene.get("core_conflict", ""),
                "emotion_goal": scene.get("emotion_goal", ""),
                "main_characters": scene.get("main_characters", []),
                "plot_function": scene.get("plot_function", ""),
                "key_event": scene.get("key_event", "")
            })
        
        return scene_plans
    
    def _format_phases_info(self, phases_info: List[Dict[str, Any]]) -> str:
        """格式化阶段信息"""
        formatted = []
        for phase_info in phases_info:
            formatted.append(
                f"- {phase_info['phase']} ({phase_info['description']}): {phase_info['scene_count']} 场戏"
            )
        return "\n".join(formatted)
    
    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        try:
            if hasattr(self.llm, 'acomplete'):
                response = await self.llm.acomplete(prompt)
                return response.text if hasattr(response, 'text') else str(response)
            else:
                import asyncio
                response = await asyncio.to_thread(self.llm.complete, prompt)
                return response.text if hasattr(response, 'text') else str(response)
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            raise
    
    def _parse_scene_plans(self, response: str) -> List[Dict[str, Any]]:
        """解析场景规划"""
        import re
        
        def remove_control_chars(text):
            """移除所有控制字符（只保留可打印字符）"""
            allowed_chars = set(' \t\n\r')
            result = []
            for char in text:
                if char in allowed_chars or char.isprintable():
                    result.append(char)
            return ''.join(result)
        
        def fix_json(json_str: str) -> str:
            """修复 JSON 格式问题"""
            json_str = json_str.strip()
            json_str = remove_control_chars(json_str)
            
            json_str = json_str.replace('"', '"').replace('"', '"').replace(''', "'").replace(''', "'")
            
            def escape_quotes(text):
                """转义字符串中的引号"""
                return text.replace('\\', '\\\\').replace('"', '\\"')
            
            pattern = r'\"([a-zA-Z0-9\u4e00-\u9fa5_]+)\"\s*:'
            json_str = re.sub(pattern, r'"\1":', json_str)
            
            def replace_unquoted_string_value(match):
                before_colon = match.group(1)
                value = match.group(2).strip()
                after_value = match.group(3)
                
                if not value:
                    return match.group(0)
                
                if value.startswith('"') or value.startswith("'"):
                    return match.group(0)
                
                if value.lower() in ["true", "false", "null"]:
                    return match.group(0)
                
                if value.startswith('[') or value.startswith('{'):
                    return match.group(0)
                
                try:
                    float(value)
                    return match.group(0)
                except ValueError:
                    pass
                
                escaped_value = escape_quotes(value)
                return f'{before_colon}"{escaped_value}"{after_value}'
            
            pattern = r'(\:\s*)([^\s\[\{\"\'],\]\}]+?)(\s*[,}\]])'
            json_str = re.sub(pattern, replace_unquoted_string_value, json_str)
            
            def fix_array_values(match):
                before_array = match.group(1)
                array_content = match.group(2)
                after_array = match.group(3)
                
                array_content = array_content.strip()
                if not array_content or array_content.startswith('['):
                    return match.group(0)
                
                items = []
                current = ""
                in_quotes = False
                escape_next = False
                
                for char in array_content:
                    if escape_next:
                        current += char
                        escape_next = False
                    elif char == '\\':
                        current += char
                        escape_next = True
                    elif char == '"':
                        in_quotes = not in_quotes
                        current += char
                    elif char == ',' and not in_quotes:
                        items.append(current)
                        current = ""
                    else:
                        current += char
                
                if current:
                    items.append(current)
                
                fixed_items = []
                for item in items:
                    item = item.strip()
                    if item.startswith('"') or item.startswith("'"):
                        fixed_items.append(item)
                    elif item.lower() in ["true", "false", "null"]:
                        fixed_items.append(item)
                    else:
                        try:
                            float(item)
                            fixed_items.append(item)
                        except ValueError:
                            escaped_item = escape_quotes(item)
                            fixed_items.append(f'"{escaped_item}"')
                
                return f'{before_array}[{", ".join(fixed_items)}]{after_array}'
            
            pattern = r'(\:\s*\[)(.*?)(\]\s*[,}\]])'
            json_str = re.sub(pattern, fix_array_values, json_str, flags=re.DOTALL)
            
            return json_str
        
        def remove_control_chars(text):
            """移除所有控制字符（只保留可打印字符）"""
            allowed_chars = set(' \t\n\r')
            result = []
            for char in text:
                if char in allowed_chars or char.isprintable():
                    result.append(char)
            return ''.join(result)
        
        try:
            response = response.strip()
            response = remove_control_chars(response)
            
            json_str = None
            
            pattern = r'```json\s*(\{[\s\S]*?\})\s*```'
            match = re.search(pattern, response)
            if match:
                json_str = match.group(1)
                logger.info("Found JSON block in markdown format")
            else:
                pattern = r'```\s*(\{[\s\S]*?\})\s*```'
                match = re.search(pattern, response)
                if match:
                    json_str = match.group(1)
                    logger.info("Found JSON block without language identifier")
                else:
                    json_start = response.find("{")
                    json_end = response.rfind("}") + 1
                    
                    if json_start == -1 or json_end == 0:
                        raise ValueError("No valid JSON found in response")
                    
                    json_str = response[json_start:json_end]
                    logger.info("Found JSON using fallback method")
            
            data = json.loads(json_str)
            
            if "scenes" not in data:
                raise ValueError("Response does not contain 'scenes' field")
            
            return data["scenes"]
            
        except json.JSONDecodeError as e:
            logger.warning(f"Initial JSON parsing failed: {str(e)}")
            logger.info("Attempting to fix JSON format...")
            
            try:
                json_str = remove_control_chars(json_str)
                fixed_json = fix_json(json_str)
                data = json.loads(fixed_json)
                
                if "scenes" not in data:
                    raise ValueError("Response does not contain 'scenes' field")
                
                logger.info("Successfully parsed JSON after fixing format")
                return data["scenes"]
                
            except Exception as fix_error:
                logger.error(f"Failed to parse JSON even after fixing: {str(fix_error)}")
                logger.error(f"Response: {response[:500]}...")
                raise ValueError(f"Failed to parse scene plans from LLM response: {str(e)}") from e
    
    async def adjust_scene_plan(
        self,
        plan_id: str,
        scene_number: int,
        adjustments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调整某场戏的规划

        Args:
            plan_id: 规划 ID
            scene_number: 场次序号
            adjustments: 调整内容 (description, characters, location, mood, conflict_type, etc.)

        Returns:
            调整后的场景规划
        """
        from app.db.database import get_db
        from app.db.story_plan_crud import StoryPlanCRUD

        async for db in get_db():
            plan = await StoryPlanCRUD.get_by_id(db, plan_id)
            if not plan:
                raise ValueError(f"Plan {plan_id} not found")

            phases_data = plan.phases_data
            if not phases_data:
                raise ValueError("Plan has no phases data")

            target_scene = None
            target_phase_name = None

            for phase in phases_data:
                for scene in phase.get("scenes", []):
                    if scene.get("scene_number") == scene_number:
                        target_scene = scene
                        target_phase_name = phase.get("name")
                        break
                if target_scene:
                    break

            if not target_scene:
                raise ValueError(f"Scene {scene_number} not found in plan")

            if adjustments.get("regenerate", False):
                prompt = self._build_scene_adjustment_prompt(
                    target_scene,
                    adjustments,
                    target_phase_name,
                    plan.story_outline,
                    plan.characters
                )

                try:
                    if hasattr(self.llm, 'acomplete'):
                        response = await self.llm.acomplete(prompt)
                        response_text = response.text if hasattr(response, 'text') else str(response)
                    else:
                        import asyncio
                        response = await asyncio.to_thread(self.llm.complete, prompt)
                        response_text = response.text if hasattr(response, 'text') else str(response)
                    adjusted_scene = self._parse_adjusted_scene(response_text, scene_number)
                    target_scene.update(adjusted_scene)
                except Exception as e:
                    logger.error(f"Failed to regenerate scene {scene_number}: {str(e)}")
                    raise ValueError(f"Failed to regenerate scene: {str(e)}") from e
            else:
                if "description" in adjustments:
                    target_scene["scene_description"] = adjustments["description"]
                if "characters" in adjustments:
                    target_scene["characters"] = adjustments["characters"]
                if "location" in adjustments:
                    target_scene["location"] = adjustments["location"]
                if "mood" in adjustments:
                    target_scene["mood"] = adjustments["mood"]
                if "conflict_type" in adjustments:
                    target_scene["conflict_type"] = adjustments["conflict_type"]
                if "emotion_type" in adjustments:
                    target_scene["emotion_type"] = adjustments["emotion_type"]

            updated_plan = await StoryPlanCRUD.update_scene(db, plan_id, scene_number, target_scene)

            return {
                "plan_id": plan_id,
                "scene_number": scene_number,
                "adjustments": adjustments,
                "status": "adjusted"
            }

    def _build_scene_adjustment_prompt(
        self,
        scene: Dict[str, Any],
        adjustments: Dict[str, Any],
        phase_name: str,
        story_outline: str,
        characters: List[str]
    ) -> str:
        """构建场景调整提示词"""
        base_info = f"""你是一个专业的编剧。请根据以下信息调整一场戏：

故事梗概：{story_outline}
人物：{', '.join(characters)}
剧情阶段：{phase_name}
当前场次：{scene.get('scene_number')}
当前描述：{scene.get('scene_description', '')}
"""

        adjustment_text = "调整要求：\n"
        if adjustments.get("description"):
            adjustment_text += f"- 新的场景描述：{adjustments['description']}\n"
        if adjustments.get("mood"):
            adjustment_text += f"- 氛围基调：{adjustments['mood']}\n"
        if adjustments.get("conflict_type"):
            adjustment_text += f"- 冲突类型：{adjustments['conflict_type']}\n"
        if adjustments.get("emotion_type"):
            adjustment_text += f"- 情绪类型：{adjustments['emotion_type']}\n"

        prompt = f"""{base_info}
{adjustment_text}

请重新生成这一场戏的详细规划，输出格式如下：
```json
{{
  "scene_number": {scene.get('scene_number')},
  "scene_description": "更新后的场景描述",
  "characters": ["涉及的人物列表"],
  "location": "场景地点",
  "mood": "氛围基调",
  "conflict_type": "冲突类型",
  "emotion_type": "情绪类型",
  "key_action": "关键动作",
  "dialogue_focus": "对白重点"
}}
```
只返回 JSON，不要其他内容。"""

        return prompt

    def _parse_adjusted_scene(self, response: str, scene_number: int) -> Dict[str, Any]:
        """解析调整后的场景"""
        import json
        import re

        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            response = json_match.group(1)

        try:
            data = json.loads(response)
            return {
                "scene_number": scene_number,
                "scene_description": data.get("scene_description", ""),
                "characters": data.get("characters", []),
                "location": data.get("location", ""),
                "mood": data.get("mood", ""),
                "conflict_type": data.get("conflict_type", ""),
                "emotion_type": data.get("emotion_type", ""),
                "key_action": data.get("key_action", ""),
                "dialogue_focus": data.get("dialogue_focus", "")
            }
        except json.JSONDecodeError as e:
            logger.error(f"Response: {response[:500]}...")
            raise ValueError(f"Failed to parse adjusted scene from LLM response: {str(e)}") from e


story_planner_service = StoryPlannerService()