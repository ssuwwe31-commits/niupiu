import logging
from typing import List, Dict, Any, Optional, Set
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from datetime import datetime

from app.models.character import Character
from app.config import get_settings

logger = logging.getLogger(__name__)


class EmotionState:
    """情绪状态模型"""
    
    def __init__(self, emotion_type: str, intensity: float, decay_rate: float = 0.1):
        self.emotion_type = emotion_type
        self.intensity = intensity
        self.decay_rate = decay_rate
        self.last_updated = datetime.now()
    
    def decay(self, time_delta: float = 1.0):
        """情绪衰减"""
        decay_factor = self.decay_rate * time_delta
        self.intensity = max(0, self.intensity - decay_factor)
        self.last_updated = datetime.now()
        return self.intensity
    
    def boost(self, amount: float):
        """情绪增强"""
        self.intensity = min(10, self.intensity + amount)
        self.last_updated = datetime.now()
        return self.intensity
    
    def is_active(self, threshold: float = 1.0) -> bool:
        """检查情绪是否活跃"""
        return self.intensity >= threshold
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "emotion_type": self.emotion_type,
            "intensity": self.intensity,
            "decay_rate": self.decay_rate,
            "last_updated": self.last_updated.isoformat()
        }


class CharacterState:
    """人物状态模型"""
    
    def __init__(
        self,
        character_id: str,
        name: str,
        core_personality: Dict[str, Any],
        background: Optional[str] = None,
        bottom_line: Optional[Dict[str, Any]] = None,
        goals: Optional[Dict[str, Any]] = None,
        relationships: Optional[Dict[str, Any]] = None
    ):
        self.character_id = character_id
        self.name = name
        self.core_personality = core_personality or {}
        self.background = background
        self.bottom_line = bottom_line or {}
        self.goals = goals or {"short_term": [], "long_term": []}
        self.relationships = relationships or {}
        self.emotions: Dict[str, EmotionState] = {}
        self.history: List[Dict[str, Any]] = []
    
    def add_emotion(self, emotion_type: str, intensity: float, decay_rate: float = 0.1):
        """添加或更新情绪"""
        if emotion_type in self.emotions:
            self.emotions[emotion_type].boost(intensity)
        else:
            self.emotions[emotion_type] = EmotionState(emotion_type, intensity, decay_rate)
        
        self._record_action("add_emotion", {
            "emotion_type": emotion_type,
            "intensity": intensity
        })
    
    def get_dominant_emotion(self) -> Optional[str]:
        """获取主导情绪"""
        active_emotions = {
            k: v.intensity for k, v in self.emotions.items() if v.is_active()
        }
        if not active_emotions:
            return None
        return max(active_emotions.items(), key=lambda x: x[1])[0]
    
    def decay_emotions(self, time_delta: float = 1.0):
        """衰减所有情绪"""
        for emotion in self.emotions.values():
            emotion.decay(time_delta)
        
        self._record_action("decay_emotions", {"time_delta": time_delta})
    
    def update_relationship(self, other_character: str, relationship_type: str, intensity: float):
        """更新人物关系"""
        self.relationships[other_character] = {
            "type": relationship_type,
            "intensity": intensity
        }
        self._record_action("update_relationship", {
            "other_character": other_character,
            "relationship_type": relationship_type,
            "intensity": intensity
        })
    
    def check_constraint(self, action: str, context: Dict[str, Any]) -> bool:
        """检查动作是否符合人物约束（底线、性格等）"""
        bottom_line = self.bottom_line
        
        for constraint, value in bottom_line.items():
            if isinstance(value, list) and action in value:
                logger.warning(f"角色 {self.name} 触犯了约束 {constraint}")
                return False
            
            if isinstance(value, dict):
                for sub_constraint, sub_value in value.items():
                    if action == sub_constraint and not self._check_context(context, sub_value):
                        return False
        
        personality = self.core_personality
        for trait, trait_value in personality.items():
            if not self._check_action_against_personality(action, trait, trait_value, context):
                return False
        
        return True
    
    def _check_context(self, context: Dict[str, Any], constraint_value: Any) -> bool:
        """检查上下文是否符合约束"""
        if isinstance(constraint_value, list):
            return context.get("emotion") not in constraint_value
        elif isinstance(constraint_value, dict):
            for key, value in constraint_value.items():
                if context.get(key) == value:
                    return False
        return True
    
    def _check_action_against_personality(
        self, action: str, trait: str, trait_value: Any, context: Dict[str, Any]
    ) -> bool:
        """检查动作是否符合性格"""
        if isinstance(trait_value, list):
            if action in trait_value:
                return True
            else:
                dominant_emotion = self.get_dominant_emotion()
                if dominant_emotion in ["愤怒", "绝望", "恐惧"]:
                    return True
        
        return True
    
    def get_active_goals(self) -> Dict[str, List[str]]:
        """获取活跃目标"""
        return {
            "short_term": self.goals.get("short_term", []),
            "long_term": self.goals.get("long_term", [])
        }
    
    def complete_goal(self, goal_type: str, goal: str):
        """完成目标"""
        goals = self.goals.get(goal_type, [])
        if goal in goals:
            goals.remove(goal)
            self._record_action("complete_goal", {
                "goal_type": goal_type,
                "goal": goal
            })
    
    def _record_action(self, action_type: str, details: Dict[str, Any]):
        """记录动作历史"""
        self.history.append({
            "action_type": action_type,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "character_id": self.character_id,
            "name": self.name,
            "core_personality": self.core_personality,
            "background": self.background,
            "bottom_line": self.bottom_line,
            "goals": self.goals,
            "relationships": self.relationships,
            "emotions": {k: v.to_dict() for k, v in self.emotions.items()},
            "dominant_emotion": self.get_dominant_emotion(),
            "active_goals": self.get_active_goals()
        }


class CharacterSystem:
    """人物系统"""
    
    def __init__(self):
        self.characters: Dict[str, CharacterState] = {}
        self.engine = None
        self.async_session = None
    
    async def initialize(self):
        """初始化数据库连接"""
        settings = get_settings()
        self.engine = create_async_engine(settings.DATABASE_URL)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def load_character(self, name: str) -> Optional[CharacterState]:
        """从数据库加载人物"""
        if name in self.characters:
            return self.characters[name]
        
        async with self.async_session() as session:
            stmt = select(Character).where(Character.name == name)
            result = await session.execute(stmt)
            character = result.scalar_one_or_none()
            
            if not character:
                logger.warning(f"未找到人物: {name}")
                return None
            
            state = CharacterState(
                character_id=str(character.id),
                name=character.name,
                core_personality=character.core_personality,
                background=character.background,
                bottom_line=character.bottom_line,
                goals=character.goals,
                relationships=character.relationships
            )
            
            self.characters[name] = state
            return state
    
    async def load_multiple_characters(self, names: List[str]) -> Dict[str, CharacterState]:
        """批量加载人物"""
        results = {}
        for name in names:
            state = await self.load_character(name)
            if state:
                results[name] = state
        return results
    
    def get_character(self, name: str) -> Optional[CharacterState]:
        """获取人物状态"""
        return self.characters.get(name)
    
    def add_character_state(self, state: CharacterState):
        """添加人物状态"""
        self.characters[state.name] = state
    
    def get_all_characters(self) -> Dict[str, CharacterState]:
        """获取所有人物状态"""
        return self.characters.copy()
    
    def simulate_interaction(
        self, character1: str, character2: str, interaction_type: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """模拟多人物交互"""
        char1 = self.get_character(character1)
        char2 = self.get_character(character2)
        
        if not char1 or not char2:
            return {"error": "人物不存在"}
        
        result = {
            "characters": [character1, character2],
            "interaction_type": interaction_type,
            "conflicts": [],
            "emotional_impacts": {}
        }
        
        if interaction_type == "conflict":
            char1_emotion = context.get("emotion_type", "紧张")
            char1_intensity = context.get("intensity", 5.0)
            char1.add_emotion(char1_emotion, char1_intensity)
            
            char2_emotion = self._get_opposite_emotion(char1_emotion)
            char2.add_emotion(char2_emotion, char1_intensity * 0.8)
            
            result["emotional_impacts"][character1] = {
                "emotion": char1_emotion,
                "intensity": char1_intensity
            }
            result["emotional_impacts"][character2] = {
                "emotion": char2_emotion,
                "intensity": char1_intensity * 0.8
            }
            
            relationship1 = char1.relationships.get(character2, {}).get("intensity", 5.0)
            if relationship1 > 0:
                char1.update_relationship(character2, "紧张", max(0, relationship1 - 1))
                char2.update_relationship(character1, "紧张", max(0, relationship1 - 1))
                result["conflicts"].append({
                    "type": "关系恶化",
                    "from": relationship1,
                    "to": relationship1 - 1
                })
        
        elif interaction_type == "cooperation":
            cooperation_emotion = context.get("emotion_type", "信任")
            cooperation_intensity = context.get("intensity", 3.0)
            
            char1.add_emotion(cooperation_emotion, cooperation_intensity)
            char2.add_emotion(cooperation_emotion, cooperation_intensity)
            
            result["emotional_impacts"][character1] = {
                "emotion": cooperation_emotion,
                "intensity": cooperation_intensity
            }
            result["emotional_impacts"][character2] = {
                "emotion": cooperation_emotion,
                "intensity": cooperation_intensity
            }
            
            relationship1 = char1.relationships.get(character2, {}).get("intensity", 5.0)
            char1.update_relationship(character2, "合作", min(10, relationship1 + 1))
            char2.update_relationship(character1, "合作", min(10, relationship1 + 1))
        
        return result
    
    def _get_opposite_emotion(self, emotion: str) -> str:
        """获取相对情绪"""
        opposite_map = {
            "愤怒": "恐惧",
            "恐惧": "愤怒",
            "开心": "失落",
            "失落": "开心",
            "信任": "怀疑",
            "怀疑": "信任"
        }
        return opposite_map.get(emotion, "紧张")
    
    def check_consistency_constraints(
        self, characters: List[str], action: str, context: Dict[str, Any]
    ) -> Dict[str, bool]:
        """检查一致性约束"""
        results = {}
        for name in characters:
            char = self.get_character(name)
            if char:
                results[name] = char.check_constraint(action, context)
            else:
                results[name] = True
        return results
    
    def get_character_constraints_for_generation(self, characters: List[str]) -> Dict[str, Dict[str, Any]]:
        """获取用于生成的人物约束"""
        constraints = {}
        for name in characters:
            char = self.get_character(name)
            if char:
                constraints[name] = {
                    "core_personality": char.core_personality,
                    "dominant_emotion": char.get_dominant_emotion(),
                    "active_goals": char.get_active_goals(),
                    "bottom_line": char.bottom_line
                }
        return constraints
    
    async def save_character_state(self, name: str):
        """保存人物状态到数据库"""
        char_state = self.get_character(name)
        if not char_state:
            logger.warning(f"Character {name} not found in memory, skipping save")
            return

        async with self.async_session() as session:
            stmt = select(Character).where(Character.name == name)
            result = await session.execute(stmt)
            db_char = result.scalar_one_or_none()

            if db_char:
                db_char.current_emotion = {
                    k: v.to_dict() for k, v in char_state.emotions.items()
                }
                db_char.relationships = char_state.relationships
                db_char.updated_at = datetime.now().isoformat()
                await session.commit()
                logger.info(f"Saved character state for {name}")
            else:
                logger.warning(f"Character {name} not found in database, skipping save")

    async def close(self):
        """关闭数据库连接"""
        if self.engine:
            await self.engine.dispose()


character_system = CharacterSystem()
