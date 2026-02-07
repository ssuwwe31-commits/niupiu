from typing import List, Optional, Dict, Any, Tuple
import re
import logging
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.vector_stores.types import VectorStoreQueryMode
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core import Settings
from app.config import get_settings
from app.services.ollama_client import get_ollama_manager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

settings = get_settings()

_ollama_manager = None


def _get_ollama_manager():
    global _ollama_manager
    if _ollama_manager is None:
        _ollama_manager = get_ollama_manager()
    return _ollama_manager


def _ensure_ollama_initialized():
    manager = _get_ollama_manager()
    if not manager._initialized:
        raise RuntimeError("Ollama client manager not initialized. Please ensure the app has started properly.")


def _update_settings():
    _ensure_ollama_initialized()
    Settings.embed_model = _ollama_manager.embed_model
    Settings.llm = _ollama_manager.llm


class RAGService:
    def __init__(self):
        self.vector_store = None
        self.index = None

    async def initialize_vector_store(self):
        import asyncpg

        conn = await asyncpg.connect(settings.DATABASE_URL.replace("+asyncpg", ""))
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        finally:
            await conn.close()

        self.vector_store = None
        self.index = None

    async def search_story_units(
        self,
        query: Optional[str] = None,
        conflict_type: Optional[str] = None,
        emotion_type: Optional[str] = None,
        character_relationship: Optional[str] = None,
        plot_function: Optional[str] = None,
        top_k: int = 5,
        fusion_method: str = "rrf",
        vector_weight: float = 0.4,
        metadata_weight: float = 0.6,
        rrf_k: int = 60
    ) -> List[Dict[str, Any]]:
        metadata_filters = {}

        if conflict_type:
            metadata_filters["conflict_type"] = conflict_type
        if emotion_type:
            metadata_filters["emotion_type"] = emotion_type
        if character_relationship:
            metadata_filters["character_relationship"] = character_relationship
        if plot_function:
            metadata_filters["plot_function"] = plot_function

        vector_results = []
        metadata_results = []

        if query:
            from sqlalchemy import select, text, func
            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
            from sqlalchemy.orm import sessionmaker
            from app.models.story_unit import StoryUnit

            _update_settings()
            query_embedding = Settings.embed_model.get_text_embedding(query)
            embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

            engine = create_async_engine(settings.DATABASE_URL)
            async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with async_session() as session:
                stmt = (
                    select(StoryUnit, text(f"1 - (embedding <=> '{embedding_str}'::vector) AS similarity"))
                    .order_by(text("similarity DESC"))
                    .limit(top_k)
                )
                
                if metadata_filters:
                    for key, value in metadata_filters.items():
                        stmt = stmt.where(getattr(StoryUnit, key) == value)
                
                result = await session.execute(stmt)
                rows = result.all()
                vector_results = [self._story_unit_to_dict_with_score(row[0], float(row[1])) for row in rows]

        if metadata_filters:
            from sqlalchemy import select
            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
            from sqlalchemy.orm import sessionmaker
            from app.models.story_unit import StoryUnit

            engine = create_async_engine(settings.DATABASE_URL)
            async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with async_session() as session:
                stmt = select(StoryUnit)
                for key, value in metadata_filters.items():
                    stmt = stmt.where(getattr(StoryUnit, key) == value)
                stmt = stmt.limit(top_k)
                result = await session.execute(stmt)
                story_units = result.scalars().all()
                metadata_results = [self._story_unit_to_dict_with_score(unit, 0.0) for unit in story_units]

        if not vector_results:
            return metadata_results
        if not metadata_results:
            return vector_results

        if fusion_method == "rrf":
            fused_results = self._rrf_fusion_dict(vector_results, metadata_results, top_k, rrf_k)
        elif fusion_method == "linear":
            fused_results = self._linear_fusion_dict(vector_results, metadata_results, top_k, vector_weight, metadata_weight)
        else:
            fused_results = vector_results

        return fused_results

    def _rrf_fusion(self, vector_results, metadata_results, top_k, rrf_k):
        score_dict = {}

        for rank, node in enumerate(vector_results, 1):
            node_id = node.node_id if hasattr(node, "node_id") else str(hash(node.text))
            score_dict[node_id] = 1 / (rrf_k + rank)
            score_dict[node_id + "_node"] = node

        for rank, node in enumerate(metadata_results, 1):
            node_id = node.node_id if hasattr(node, "node_id") else str(hash(node.text))
            if node_id in score_dict:
                score_dict[node_id] += 1 / (rrf_k + rank)
            else:
                score_dict[node_id] = 1 / (rrf_k + rank)
                score_dict[node_id + "_node"] = node

        sorted_results = sorted(
            [(node_id, score) for node_id, score in score_dict.items() if not node_id.endswith("_node")],
            key=lambda x: -x[1]
        )

        result_nodes = []
        for node_id, _ in sorted_results[:top_k]:
            result_nodes.append(score_dict[node_id + "_node"])

        return result_nodes

    def _linear_fusion(self, vector_results, metadata_results, top_k, vector_weight, metadata_weight):
        score_dict = {}

        for node in vector_results:
            node_id = node.node_id if hasattr(node, "node_id") else str(hash(node.text))
            vector_score = float(node.score) if hasattr(node, "score") else 0.0
            score_dict[node_id] = vector_score * vector_weight
            score_dict[node_id + "_node"] = node

        for rank, node in enumerate(metadata_results):
            node_id = node.node_id if hasattr(node, "node_id") else str(hash(node.text))
            metadata_score = (top_k - rank) / top_k
            if node_id in score_dict:
                score_dict[node_id] += metadata_score * metadata_weight
            else:
                score_dict[node_id] = metadata_score * metadata_weight
                score_dict[node_id + "_node"] = node

        sorted_results = sorted(
            [(node_id, score) for node_id, score in score_dict.items() if not node_id.endswith("_node")],
            key=lambda x: -x[1]
        )

        result_nodes = []
        for node_id, _ in sorted_results[:top_k]:
            result_nodes.append(score_dict[node_id + "_node"])

        return result_nodes

    async def search_temporal_units(
        self,
        target_unit_id: Optional[str] = None,
        chapter_range: Optional[Tuple[int, int]] = None,
        preceding_units: int = 0,
        subsequent_units: int = 0,
        top_k: int = 10
    ) -> Dict[str, Any]:
        try:
            from sqlalchemy import select
            from sqlalchemy import and_
            from app.models.story_unit import StoryUnit
            from app.db.database import AsyncSessionLocal

            result = {
                "preceding_units": [],
                "target_unit": None,
                "subsequent_units": [],
                "timeline": []
            }

            logger.info(f"search_temporal_units called with target_unit_id={target_unit_id}, chapter_range={chapter_range}")

            async with AsyncSessionLocal() as session:
                logger.info("Session created successfully")

                if target_unit_id:
                    target_stmt = select(StoryUnit).where(StoryUnit.id == target_unit_id)
                    target_result = await session.execute(target_stmt)
                    target_unit = target_result.scalar_one_or_none()

                    if target_unit:
                        result["target_unit"] = self._node_to_dict(self._story_unit_to_node(target_unit))

                        preceding_stmt = (
                            select(StoryUnit)
                            .where(StoryUnit.chapter < target_unit.chapter)
                            .order_by(StoryUnit.chapter.desc(), StoryUnit.id.desc())
                            .limit(preceding_units)
                        )
                        preceding_result = await session.execute(preceding_stmt)
                        preceding_list = preceding_result.scalars().all()
                        result["preceding_units"] = [
                            self._node_to_dict(self._story_unit_to_node(unit))
                            for unit in reversed(preceding_list)
                        ]

                        subsequent_stmt = (
                            select(StoryUnit)
                            .where(StoryUnit.chapter > target_unit.chapter)
                            .order_by(StoryUnit.chapter, StoryUnit.id)
                            .limit(subsequent_units)
                        )
                        subsequent_result = await session.execute(subsequent_stmt)
                        subsequent_list = subsequent_result.scalars().all()
                        result["subsequent_units"] = [
                            self._node_to_dict(self._story_unit_to_node(unit))
                            for unit in subsequent_list
                        ]

                elif chapter_range:
                    stmt = (
                        select(StoryUnit)
                        .where(
                            and_(
                                StoryUnit.chapter >= chapter_range[0],
                                StoryUnit.chapter <= chapter_range[1]
                            )
                        )
                        .order_by(StoryUnit.chapter, StoryUnit.id)
                        .limit(top_k)
                    )
                    timeline_result = await session.execute(stmt)
                    timeline_list = timeline_result.scalars().all()
                    result["timeline"] = [
                        self._node_to_dict(self._story_unit_to_node(unit))
                        for unit in timeline_list
                    ]
                else:
                    stmt = (
                        select(StoryUnit)
                        .order_by(StoryUnit.chapter, StoryUnit.id)
                        .limit(top_k)
                    )
                    timeline_result = await session.execute(stmt)
                    timeline_list = timeline_result.scalars().all()
                    result["timeline"] = [
                        self._node_to_dict(self._story_unit_to_node(unit))
                        for unit in timeline_list
                    ]

            return result
        except Exception as e:
            raise RuntimeError(f"Failed to search temporal units: {str(e)}") from e

    async def generate_script_with_temporal(
        self,
        plot_context: str,
        required_conflict: str,
        required_emotion: str,
        characters: List[str],
        scene: Optional[str] = None,
        constraints: Optional[Dict[str, Any]] = None,
        temporal_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        _update_settings()
        try:
            referenced_units = await self.search_story_units(
                query=plot_context,
                conflict_type=required_conflict,
                emotion_type=required_emotion,
                top_k=3
            )

            temporal_units = await self.search_temporal_units(
                target_unit_id=temporal_context.get("target_unit_id") if temporal_context else None,
                chapter_range=temporal_context.get("chapter_range") if temporal_context else None,
                preceding_units=temporal_context.get("preceding_units", 0) if temporal_context else 0,
                subsequent_units=temporal_context.get("subsequent_units", 0) if temporal_context else 0,
            )

            character_constraints = await self._get_character_constraints(characters)

            character_context = ""
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
                    if info.get("current_emotion"):
                        character_context += f"  - 当前情绪: {info['current_emotion']}\n"
                    if info.get("goals"):
                        character_context += f"  - 目标: {info['goals']}\n"
                    if info.get("relationships"):
                        character_context += f"  - 关系: {info['relationships']}\n"

            reference_context = "\n\n".join([
                f"参考剧情{idx+1}:\n{unit['text']}"
                for idx, unit in enumerate(referenced_units)
            ])

            temporal_context_str = ""
            if temporal_units.get("preceding_units"):
                temporal_context_str += "\n前置剧情：\n"
                for idx, unit in enumerate(temporal_units["preceding_units"]):
                    temporal_context_str += f"  {idx+1}. {unit['text']}\n"

            if temporal_units.get("target_unit"):
                temporal_context_str += "\n当前剧情节点：\n"
                temporal_context_str += f"  {temporal_units['target_unit']['text']}\n"

            if temporal_units.get("subsequent_units"):
                temporal_context_str += "\n后置剧情：\n"
                for idx, unit in enumerate(temporal_units["subsequent_units"]):
                    temporal_context_str += f"  {idx+1}. {unit['text']}\n"

            prompt = f"""
请根据以下信息生成一场戏的剧本：

剧情上下文：
{plot_context}
{character_context}
{temporal_context_str}
需要的冲突类型：{required_conflict}
需要的情绪类型：{required_emotion}
场景：{scene if scene else '请根据剧情设定'}

参考剧情片段：
{reference_context}

生成要求：
1. 符合指定的冲突类型和情绪类型
2. 严格遵循人物设定，保持人物性格、关系和情绪的一致性
3. 考虑前后剧情的连贯性，确保时间线和剧情发展的合理性
4. 对话自然，符合人物性格和当前状态
5. 有明确的戏剧张力
6. 字数控制在500-800字

请生成剧本：
"""

            response = Settings.llm.complete(prompt)
            generated_script = response.text

            return {
                "generated_script": generated_script,
                "referenced_units": [unit["id"] for unit in referenced_units],
                "temporal_context": {
                    "preceding_count": len(temporal_units.get("preceding_units", [])),
                    "subsequent_count": len(temporal_units.get("subsequent_units", [])),
                    "has_target_unit": temporal_units.get("target_unit") is not None
                },
                "applied_character_constraints": list(character_constraints.keys()),
                "confidence": 0.85,
            }
        except Exception as e:
            raise RuntimeError(f"Failed to generate script with temporal: {str(e)}") from e

    def _story_unit_to_node(self, story_unit):
        from llama_index.core import Document
        return Document(
            text=story_unit.original_text,
            metadata={
                "scene": story_unit.scene,
                "characters": story_unit.characters,
                "core_conflict": story_unit.core_conflict,
                "emotion_curve": story_unit.emotion_curve,
                "plot_function": story_unit.plot_function,
                "result": story_unit.result,
                "conflict_type": story_unit.conflict_type,
                "emotion_type": story_unit.emotion_type,
                "character_relationship": story_unit.character_relationship,
            }
        )

    def _node_to_dict(self, node) -> Dict[str, Any]:
        from uuid import UUID
        node_id = node.node_id if hasattr(node, "node_id") else ""
        if isinstance(node_id, UUID):
            node_id = str(node_id)
        return {
            "id": node_id,
            "text": node.text,
            "metadata": node.metadata if hasattr(node, "metadata") else {},
            "score": float(node.score) if hasattr(node, "score") else 0.0,
        }

    def _story_unit_to_dict_with_score(self, story_unit, score: float) -> Dict[str, Any]:
        return {
            "id": str(story_unit.id),
            "text": story_unit.original_text,
            "metadata": {
                "scene": story_unit.scene,
                "characters": story_unit.characters,
                "core_conflict": story_unit.core_conflict,
                "emotion_curve": story_unit.emotion_curve,
                "plot_function": story_unit.plot_function,
                "result": story_unit.result,
                "conflict_type": story_unit.conflict_type,
                "emotion_type": story_unit.emotion_type,
                "character_relationship": story_unit.character_relationship,
            },
            "score": score,
        }

    def _rrf_fusion_dict(self, vector_results, metadata_results, top_k, rrf_k):
        score_dict = {}

        for rank, item in enumerate(vector_results, 1):
            node_id = item.get("id", "")
            score_dict[node_id] = 1 / (rrf_k + rank)
            score_dict[node_id + "_item"] = item

        for rank, item in enumerate(metadata_results, 1):
            node_id = item.get("id", "")
            if node_id in score_dict:
                score_dict[node_id] += 1 / (rrf_k + rank)
            else:
                score_dict[node_id] = 1 / (rrf_k + rank)
                score_dict[node_id + "_item"] = item

        sorted_results = sorted(
            [(node_id, score) for node_id, score in score_dict.items() if not node_id.endswith("_item")],
            key=lambda x: -x[1]
        )

        result_items = []
        for node_id, _ in sorted_results[:top_k]:
            result_items.append(score_dict[node_id + "_item"])
            result_items[-1]["score"] = score_dict[node_id]

        return result_items

    def _linear_fusion_dict(self, vector_results, metadata_results, top_k, vector_weight, metadata_weight):
        score_dict = {}

        for item in vector_results:
            node_id = item.get("id", "")
            vector_score = item.get("score", 0.0)
            score_dict[node_id] = vector_score * vector_weight
            score_dict[node_id + "_item"] = item

        for rank, item in enumerate(metadata_results):
            node_id = item.get("id", "")
            metadata_score = (top_k - rank) / top_k
            if node_id in score_dict:
                score_dict[node_id] += metadata_score * metadata_weight
            else:
                score_dict[node_id] = metadata_score * metadata_weight
                score_dict[node_id + "_item"] = item

        sorted_results = sorted(
            [(node_id, score) for node_id, score in score_dict.items() if not node_id.endswith("_item")],
            key=lambda x: -x[1]
        )

        result_items = []
        for node_id, _ in sorted_results[:top_k]:
            result_items.append(score_dict[node_id + "_item"])
            result_items[-1]["score"] = score_dict[node_id]

        return result_items

    async def _get_character_constraints(self, character_names: List[str]) -> Dict[str, Any]:
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from app.models.character import Character

        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        character_constraints = {}

        async with async_session() as session:
            for name in character_names:
                result = await session.execute(
                    select(Character).where(Character.name == name)
                )
                character = result.scalar_one_or_none()

                if character:
                    character_constraints[name] = {
                        "core_personality": character.core_personality,
                        "background": character.background,
                        "bottom_line": character.bottom_line,
                        "current_emotion": character.current_emotion,
                        "goals": character.goals,
                        "relationships": character.relationships
                    }

        return character_constraints

    async def update_character_emotion(
        self,
        character_name: str,
        emotion_type: str,
        intensity: float,
        decay_rate: float = 0.1
    ) -> Dict[str, Any]:
        from sqlalchemy import select
        from app.models.character import Character
        from app.db.database import AsyncSessionLocal
        from datetime import datetime

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Character).where(Character.name == character_name)
            )
            character = result.scalar_one_or_none()

            if not character:
                raise ValueError(f"Character '{character_name}' not found")

            current_emotion = character.current_emotion or {}

            emotion_entry = {
                "type": emotion_type,
                "intensity": intensity,
                "decay_rate": decay_rate,
                "updated_at": datetime.now().isoformat(),
                "original_intensity": intensity
            }

            if current_emotion and isinstance(current_emotion, dict):
                if emotion_type in current_emotion:
                    existing_emotion = current_emotion[emotion_type]
                    if isinstance(existing_emotion, dict):
                        time_diff = (datetime.now() - datetime.fromisoformat(existing_emotion.get("updated_at", datetime.now().isoformat()))).total_seconds() / 3600
                        decayed_intensity = existing_emotion["original_intensity"] * (1 - decay_rate) ** time_diff
                        new_intensity = min(10, decayed_intensity + intensity * 0.5)
                        emotion_entry["intensity"] = new_intensity
                        emotion_entry["original_intensity"] = new_intensity
                elif current_emotion.get("emotion") == emotion_type:
                    old_intensity = current_emotion.get("intensity", 0)
                    old_decay_rate = current_emotion.get("decay_rate", decay_rate)
                    updated_at = current_emotion.get("updated_at")
                    if updated_at:
                        try:
                            time_diff = (datetime.now() - datetime.fromisoformat(updated_at)).total_seconds() / 3600
                            decayed_intensity = old_intensity * (1 - old_decay_rate) ** time_diff
                            new_intensity = min(10, decayed_intensity + intensity * 0.5)
                            emotion_entry["intensity"] = new_intensity
                            emotion_entry["original_intensity"] = new_intensity
                        except:
                            pass

            character.current_emotion = {
                emotion_type: emotion_entry
            }
            character.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            await session.commit()
            await session.refresh(character)

            return {
                "character_id": str(character.id),
                "name": character.name,
                "current_emotion": character.current_emotion,
                "dominant_emotion": self._get_dominant_emotion(character.current_emotion)
            }

    def _get_dominant_emotion(self, emotion_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not emotion_data:
            return None

        dominant = None
        max_intensity = 0

        for emotion_type, emotion_info in emotion_data.items():
            if isinstance(emotion_info, dict):
                intensity = emotion_info.get("intensity", 0)
                if intensity > max_intensity:
                    max_intensity = intensity
                    dominant = {
                        "type": emotion_type,
                        "intensity": intensity
                    }

        return dominant

    async def decay_emotions(self, character_name: Optional[str] = None, time_offset_hours: float = 0.0) -> Dict[str, Any]:
        from sqlalchemy import select
        from app.models.character import Character
        from app.db.database import AsyncSessionLocal
        from datetime import datetime, timedelta

        async with AsyncSessionLocal() as session:
            if character_name:
                result = await session.execute(
                    select(Character).where(Character.name == character_name)
                )
                characters = result.scalars().all()
            else:
                result = await session.execute(select(Character))
                characters = result.scalars().all()

            decayed_results = []
            current_time = datetime.now() + timedelta(hours=time_offset_hours) if time_offset_hours > 0 else datetime.now()
            actual_now = datetime.now()

            for character in characters:
                current_emotion = character.current_emotion or {}
                updated = False
                has_emotions = False

                logger.info(f"[DECAY START] Processing character: {character.name}, "
                           f"current_emotion: {current_emotion}, "
                           f"time_offset_hours: {time_offset_hours}, "
                           f"current_time: {current_time}, "
                           f"actual_now: {actual_now}")

                for emotion_type, emotion_info in list(current_emotion.items()):
                    if isinstance(emotion_info, dict):
                        has_emotions = True
                        updated_at_str = emotion_info.get("updated_at")
                        logger.info(f"[DECAY BEFORE] {character.name}.{emotion_type}: "
                                   f"updated_at_str={updated_at_str}, "
                                   f"emotion_info={emotion_info}")
                        if updated_at_str:
                            try:
                                updated_at = datetime.fromisoformat(updated_at_str)
                                time_diff = (current_time - updated_at).total_seconds() / 3600
                                decay_rate = emotion_info.get("decay_rate", 0.1)
                                original_intensity = emotion_info.get("original_intensity", emotion_info.get("intensity", 0))

                                decayed_intensity = original_intensity * (1 - decay_rate) ** time_diff

                                logger.info(f"[DECAY CALC] Character: {character.name}, Emotion: {emotion_type}, "
                                           f"updated_at: {updated_at}, current_time: {current_time}, "
                                           f"time_offset_hours: {time_offset_hours}, time_diff: {time_diff}, "
                                           f"decay_rate: {decay_rate}, original_intensity: {original_intensity}, "
                                           f"decayed_intensity: {decayed_intensity}, "
                                           f"condition1: {decayed_intensity < 0.5}, "
                                           f"condition2: {time_diff > 0.01}, "
                                           f"condition3: {time_offset_hours > 0}")

                                if decayed_intensity < 0.5:
                                    del current_emotion[emotion_type]
                                    updated = True
                                    logger.info(f"[DECAY DELETE] Deleted {character.name}.{emotion_type}")
                                elif time_diff > 0.01 or time_offset_hours > 0:
                                    emotion_info["intensity"] = decayed_intensity
                                    emotion_info["updated_at"] = current_time.isoformat()
                                    updated = True
                                    logger.info(f"[DECAY UPDATE] Updated {character.name}.{emotion_type}: "
                                               f"intensity {original_intensity:.2f} → {decayed_intensity:.2f}")
                                else:
                                    logger.info(f"[DECAY SKIP] Skipped {character.name}.{emotion_type}: time_diff={time_diff}")
                            except Exception as e:
                                logger.warning(f"Error decaying emotion for {character.name}: {e}")
                                import traceback
                                traceback.print_exc()

                if has_emotions:
                    from sqlalchemy.orm.attributes import flag_modified
                    character.current_emotion = current_emotion
                    flag_modified(character, "current_emotion")
                    character.updated_at = current_time.strftime("%Y-%m-%d %H:%M:%S")
                    decayed_results.append({
                        "name": character.name,
                        "decayed_emotions": current_emotion,
                        "dominant_emotion": self._get_dominant_emotion(current_emotion),
                        "updated": updated
                    })

            await session.commit()

            return {
                    "decayed_count": len(decayed_results),
                    "updated_count": sum(1 for r in decayed_results if r.get("updated")),
                    "results": decayed_results
                }

    async def resolve_character_conflicts(
        self,
        characters: List[str],
        scene_context: Optional[str] = None
    ) -> Dict[str, Any]:
        _update_settings()
        from sqlalchemy import select
        from app.models.character import Character
        from app.db.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            character_data = {}
            for name in characters:
                result = await session.execute(
                    select(Character).where(Character.name == name)
                )
                character = result.scalar_one_or_none()
                if character:
                    character_data[name] = {
                        "core_personality": character.core_personality,
                        "bottom_line": character.bottom_line,
                        "current_emotion": character.current_emotion,
                        "goals": character.goals,
                        "relationships": character.relationships
                    }

        conflicts = []
        resolutions = []

        for i, char1_name in enumerate(characters):
            for char2_name in characters[i+1:]:
                char1 = character_data.get(char1_name, {})
                char2 = character_data.get(char2_name, {})

                conflict = self._detect_conflict(char1_name, char1, char2_name, char2)
                if conflict:
                    conflicts.append(conflict)
                    resolution = self._resolve_conflict(conflict)
                    resolutions.append(resolution)

        prompt = f"""
请分析以下多人物场景中的角色冲突，并提供协调建议：

场景上下文：
{scene_context or '未提供'}

参与角色：
"""
        for name, data in character_data.items():
            prompt += f"\n{name}:\n"
            if data.get("core_personality"):
                prompt += f"  - 核心性格: {data['core_personality']}\n"
            if data.get("bottom_line"):
                prompt += f"  - 底线: {data['bottom_line']}\n"
            if data.get("goals"):
                prompt += f"  - 目标: {data['goals']}\n"
            if data.get("relationships"):
                prompt += f"  - 关系: {data['relationships']}\n"
            if data.get("current_emotion"):
                prompt += f"  - 当前情绪: {data['current_emotion']}\n"

        if conflicts:
            prompt += "\n检测到的冲突：\n"
            for idx, conflict in enumerate(conflicts, 1):
                prompt += f"{idx}. {conflict['description']}\n"

        prompt += """
请提供协调建议，包括：
1. 如何处理这些冲突
2. 角色如何在冲突中保持一致性行为
3. 如何将冲突转化为戏剧张力
4. 建议的角色行动和对话方向
"""

        try:
            response = Settings.llm.complete(prompt)
            ai_suggestion = response.text
        except Exception as e:
            logger.warning(f"Failed to get AI conflict resolution: {e}")
            ai_suggestion = "无法获取AI建议，请根据检测到的冲突手动处理。"

        emotion_analysis = {}
        for name, data in character_data.items():
            if data.get("current_emotion"):
                emotion_analysis[name] = data["current_emotion"]

        return {
            "characters_involved": characters,
            "conflicts_detected": conflicts,
            "proposed_resolutions": resolutions,
            "ai_suggestion": ai_suggestion,
            "scene_safe": len(conflicts) == 0,
            "conflict_analysis": {
                "total_conflicts": len(conflicts),
                "conflict_types": [c.get("type") for c in conflicts],
                "conflict_descriptions": [c.get("description") for c in conflicts]
            },
            "resolution_suggestions": resolutions,
            "emotion_analysis": emotion_analysis
        }

    def _detect_conflict(self, char1_name: str, char1_data: Dict, char2_name: str, char2_data: Dict) -> Optional[Dict[str, Any]]:
        conflicts = []

        char1_goals = char1_data.get("goals", {})
        char2_goals = char2_data.get("goals", {})

        if isinstance(char1_goals, dict) and isinstance(char2_goals, dict):
            char1_short = set(char1_goals.get("short_term", []))
            char2_short = set(char2_goals.get("short_term", []))

            mutual_goals = char1_short & char2_short
            if mutual_goals:
                conflicts.append({
                    "type": "目标竞争",
                    "description": f"{char1_name}和{char2_name}存在相同目标: {', '.join(mutual_goals)}",
                    "severity": "high"
                })

            opposite_goals = []
            for g1 in char1_short:
                for g2 in char2_short:
                    if self._are_opposite_goals(g1, g2):
                        opposite_goals.append((g1, g2))

            if opposite_goals:
                conflicts.append({
                    "type": "目标对立",
                    "description": f"{char1_name}和{char2_name}的目标对立: {', '.join([f'{a} vs {b}' for a, b in opposite_goals])}",
                    "severity": "high"
                })

        char1_bottom = char1_data.get("bottom_line", {})
        char2_bottom = char2_data.get("bottom_line", {})

        if isinstance(char1_bottom, dict) and isinstance(char2_bottom, dict):
            char1_forbidden = set(char1_bottom.get("forbidden", []))
            char2_actions = set(char2_data.get("goals", {}).get("short_term", []))

            violations = char1_forbidden & char2_actions
            if violations:
                conflicts.append({
                    "type": "底线冲突",
                    "description": f"{char2_name}的目标可能触犯{char1_name}的底线: {', '.join(violations)}",
                    "severity": "critical"
                })

        char1_emotion = char1_data.get("current_emotion", {})
        char2_emotion = char2_data.get("current_emotion", {})

        char1_dominant = self._get_dominant_emotion(char1_emotion)
        char2_dominant = self._get_dominant_emotion(char2_emotion)

        if char1_dominant and char2_dominant:
            if self._are_conflicting_emotions(char1_dominant.get("type"), char2_dominant.get("type")):
                conflicts.append({
                    "type": "情绪冲突",
                    "description": f"{char1_name}({char1_dominant['type']})与{char2_name}({char2_dominant['type']})的情绪可能引发冲突",
                    "severity": "medium"
                })

        char1_relations = char1_data.get("relationships", {})
        char2_relations = char2_data.get("relationships", {})

        if isinstance(char1_relations, dict) and isinstance(char2_relations, dict):
            char1_to_char2 = char1_relations.get(char2_name, "")
            char2_to_char1 = char2_relations.get(char1_name, "")

            if char1_to_char2 == "仇敌" or char2_to_char1 == "仇敌":
                conflicts.append({
                    "type": "关系冲突",
                    "description": f"{char1_name}和{char2_name}是仇敌关系，天然存在冲突",
                    "severity": "high"
                })

        if conflicts:
            return {
                "characters": [char1_name, char2_name],
                "conflict_items": conflicts,
                "description": f"{char1_name}与{char2_name}之间存在{len(conflicts)}个冲突"
            }

        return None

    def _are_opposite_goals(self, goal1: str, goal2: str) -> bool:
        opposite_pairs = [
            ("保护", "破坏"),
            ("拯救", "杀害"),
            ("获得", "失去"),
            ("胜利", "失败"),
            ("建设", "毁灭"),
            ("揭露", "掩盖"),
            ("进攻", "防守"),
            ("进攻", "撤退"),
            ("前进", "后退"),
            ("信任", "背叛"),
        ]

        for pair in opposite_pairs:
            if (pair[0] in goal1 and pair[1] in goal2) or (pair[1] in goal1 and pair[0] in goal2):
                return True

        return False

    def _are_conflicting_emotions(self, emotion1: str, emotion2: str) -> bool:
        conflicting_emotions = [
            ("愤怒", "恐惧"),
            ("仇恨", "爱"),
            ("兴奋", "悲伤"),
            ("傲慢", "羞愧"),
            ("嫉妒", "满足"),
            ("轻视", "尊敬"),
        ]

        for pair in conflicting_emotions:
            if (pair[0] in emotion1 and pair[1] in emotion2) or (pair[1] in emotion1 and pair[0] in emotion2):
                return True

        return False

    def _resolve_conflict(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        resolutions = []

        for item in conflict["conflict_items"]:
            conflict_type = item["type"]
            severity = item["severity"]

            if conflict_type == "目标竞争":
                resolutions.append({
                    "type": "合作解决",
                    "description": "让角色意识到合作比竞争更能实现目标，或引入更高层目标",
                    "strategy": "compromise"
                })
            elif conflict_type == "目标对立":
                resolutions.append({
                    "type": "戏剧对抗",
                    "description": "利用目标对立创造戏剧冲突，让一方妥协或寻找第三方解决方案",
                    "strategy": "confrontation"
                })
            elif conflict_type == "底线冲突":
                resolutions.append({
                    "type": "避免触发",
                    "description": "让触犯底线的行为未发生，或引发强烈反应推动剧情",
                    "strategy": "avoidance"
                })
            elif conflict_type == "情绪冲突":
                resolutions.append({
                    "type": "情绪调解",
                    "description": "通过对话或事件缓和情绪，或让情绪冲突爆发推动剧情",
                    "strategy": "mediation"
                })
            elif conflict_type == "关系冲突":
                resolutions.append({
                    "type": "关系利用",
                    "description": "利用现有关系创造戏剧张力，或尝试修复/恶化关系",
                    "strategy": "relationship"
                })

        return {
            "conflict": conflict["description"],
            "resolutions": resolutions,
            "priority": self._get_severity_priority(conflict["conflict_items"])
        }

    def _get_severity_priority(self, conflict_items: List[Dict]) -> str:
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        min_priority = 4

        for item in conflict_items:
            severity = item.get("severity", "low")
            priority = severity_order.get(severity, 3)
            if priority < min_priority:
                min_priority = priority

        return ["critical", "high", "medium", "low"][min_priority]

    async def generate_script(
        self,
        plot_context: str,
        required_conflict: str,
        required_emotion: str,
        characters: List[str],
        scene: Optional[str] = None,
        constraints: Optional[Dict[str, Any]] = None,
        goal_driven: bool = False,
    ) -> Dict[str, Any]:
        _update_settings()
        try:
            referenced_units = await self.search_story_units(
                query=plot_context,
                conflict_type=required_conflict,
                emotion_type=required_emotion,
                top_k=3
            )

            character_constraints = await self._get_character_constraints(characters)

            character_context = ""
            goal_context = ""
            active_goals = []

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
                    if info.get("current_emotion"):
                        character_context += f"  - 当前情绪: {info['current_emotion']}\n"
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
                prompt = f"""
请根据以下信息生成一场戏的剧本：

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
6. 字数控制在500-800字

请生成剧本：
"""
            else:
                prompt = f"""
请根据以下信息生成一场戏的剧本：

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
5. 字数控制在500-800字

请生成剧本：
"""

            response = Settings.llm.complete(prompt)
            generated_script = response.text

            return {
                "generated_script": generated_script,
                "referenced_units": [unit["id"] for unit in referenced_units],
                "applied_character_constraints": list(character_constraints.keys()),
                "goal_driven": goal_driven,
                "active_goals": active_goals,
                "confidence": 0.85,
            }
        except Exception as e:
            raise RuntimeError(f"Failed to generate script: {str(e)}") from e

    async def evaluate_script_quality(self, script: str, constraints: Dict[str, Any]) -> Dict[str, Any]:
        _update_settings()
        evaluation_prompt = f"""
请对以下生成的剧本进行质量评估，按照以下维度打分（1-10分）：

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
            response = Settings.llm.complete(evaluation_prompt)
            evaluation_text = response.text.strip()

            json_match = re.search(r'\{[\s\S]*\}', evaluation_text)
            if json_match:
                import json
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
            return self._get_default_evaluation()

    def _get_quality_level(self, score: float) -> str:
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
            "strengths": ["暂无"],
            "weaknesses": ["评估失败，无法获取详细信息"],
            "suggestions": ["建议人工审核"]
        }

    async def generate_temporal_relations(
        self,
        source_unit_id: str,
        target_unit_id: str,
        auto_update: bool = False
    ) -> Dict[str, Any]:
        _update_settings()
        from sqlalchemy import select
        from app.models.story_unit import StoryUnit
        from app.db.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(StoryUnit).where(StoryUnit.id == source_unit_id)
            )
            source_unit = result.scalar_one_or_none()

            result = await session.execute(
                select(StoryUnit).where(StoryUnit.id == target_unit_id)
            )
            target_unit = result.scalar_one_or_none()

            if not source_unit or not target_unit:
                raise ValueError("One or both story units not found")

        prompt = f"""
请分析以下两个剧情单元之间的时序关系，并返回详细分析：

剧情单元1（前序）：
- ID: {source_unit.id}
- 章节: {source_unit.chapter}
- 文本: {source_unit.text[:500]}
- 情绪: {source_unit.emotion_type}
- 冲突: {source_unit.conflict_type}

剧情单元2（后序）：
- ID: {target_unit.id}
- 章节: {target_unit.chapter}
- 文本: {target_unit.text[:500]}
- 情绪: {target_unit.emotion_type}
- 冲突: {target_unit.conflict_type}

请以JSON格式返回时序关系分析：
{{
    "temporal_relation": "时序关系类型 (sequential|concurrent|overlapping|indeterminate)",
    "temporal_distance": "时序距离 (immediate|short|medium|long|unknown)",
    "causality": "因果关系 (strong|weak|none)",
    "narrative_flow": "叙事流畅度 (smooth|abrupt|disjointed)",
    "character_continuity": "角色连续性 (maintained|partial|broken)",
    "emotional_progression": "情绪进展 (escalating|stable|decreasing|contradictory)",
    "plot_function": "剧情功能 (continuation|transition|climax|resolution|revelation)",
    "confidence": "置信度 (0-1)",
    "explanation": "时序关系说明",
    "suggestions": ["建议1", "建议2"]
}}
"""

        try:
            response = Settings.llm.complete(prompt)
            analysis_text = response.text.strip()
            logger.info(f"LLM response: {analysis_text[:200]}")

            json_match = re.search(r'\{[\s\S]*\}', analysis_text)
            if json_match:
                import json
                temporal_data = json.loads(json_match.group())

                confidence = temporal_data.get("confidence", 0.5)

                if auto_update and confidence >= 0.7:
                    await self._update_temporal_metadata(
                        source_unit, target_unit, temporal_data
                    )

                return {
                    "source_unit_id": source_unit_id,
                    "target_unit_id": target_unit_id,
                    "temporal_relation": temporal_data,
                    "auto_updated": auto_update and confidence >= 0.7
                }
            else:
                default_relation = {
                    "temporal_relation": "indeterminate",
                    "temporal_distance": "unknown",
                    "causality": "none",
                    "narrative_flow": "disjointed",
                    "character_continuity": "partial",
                    "emotional_progression": "stable",
                    "plot_function": "transition",
                    "confidence": 0.3,
                    "explanation": "LLM response parsing failed, using default values",
                    "suggestions": ["建议人工审核"]
                }
                logger.warning(f"Failed to parse LLM response, using defaults: {analysis_text[:100]}")
                return {
                    "source_unit_id": source_unit_id,
                    "target_unit_id": target_unit_id,
                    "temporal_relation": default_relation,
                    "auto_updated": False,
                    "warning": "Failed to parse AI response, using default values"
                }
        except Exception as e:
            logger.error(f"Error generating temporal relations: {e}")
            default_relation = {
                "temporal_relation": "indeterminate",
                "temporal_distance": "unknown",
                "causality": "none",
                "narrative_flow": "disjointed",
                "character_continuity": "partial",
                "emotional_progression": "stable",
                "plot_function": "transition",
                "confidence": 0.0,
                "explanation": f"Error occurred: {str(e)}",
                "suggestions": ["检查LLM服务配置", "建议人工审核"]
            }
            return {
                "source_unit_id": source_unit_id,
                "target_unit_id": target_unit_id,
                "temporal_relation": default_relation,
                "auto_updated": False,
                "error": str(e)
            }

    async def _update_temporal_metadata(
        self,
        source_unit: Any,
        target_unit: Any,
        temporal_data: Dict[str, Any]
    ) -> None:
        from app.db.database import AsyncSessionLocal
        from sqlalchemy import update

        async with AsyncSessionLocal() as session:
            relation = temporal_data.get("temporal_relation", "indeterminate")

            if not target_unit.temporal_relations:
                target_unit.temporal_relations = {}

            target_unit.temporal_relations["preceding"] = [{
                "unit_id": source_unit.id,
                "relation_type": relation,
                "temporal_distance": temporal_data.get("temporal_distance", "unknown"),
                "causality": temporal_data.get("causality", "none"),
                "narrative_flow": temporal_data.get("narrative_flow", "unknown"),
                "confidence": temporal_data.get("confidence", 0.5)
            }]

            target_unit.plot_function = temporal_data.get("plot_function", target_unit.plot_function)

            await session.commit()

    async def batch_generate_temporal_relations(
        self,
        unit_ids: List[str],
        update_threshold: float = 0.7
    ) -> Dict[str, Any]:
        results = []

        for i in range(len(unit_ids) - 1):
            source_id = unit_ids[i]
            target_id = unit_ids[i + 1]

            result = await self.generate_temporal_relations(
                source_unit_id=source_id,
                target_unit_id=target_id,
                auto_update=True
            )

            results.append(result)

        successful_updates = sum(1 for r in results if r.get("auto_updated", False))
        avg_confidence = sum(
            r.get("temporal_relation", {}).get("confidence", 0)
            for r in results if r.get("temporal_relation")
        ) / len(results) if results else 0

        return {
            "total_pairs": len(results),
            "successful_updates": successful_updates,
            "average_confidence": avg_confidence,
            "results": results
        }

    async def auto_link_temporal_context(
        self,
        plot_context: str,
        characters: List[str],
        look_back_units: int = 3,
        look_ahead_units: int = 1
    ) -> Dict[str, Any]:
        _update_settings()
        search_results = await self.search_story_units(
            query=plot_context,
            top_k=look_back_units + look_ahead_units + 2
        )

        if len(search_results) < 2:
            return {
                "context_available": False,
                "reason": "Not enough story units found for temporal analysis"
            }

        selected_units = search_results[:look_back_units + look_ahead_units + 1]

        if len(selected_units) < 2:
            return {
                "context_available": False,
                "reason": "Insufficient units for temporal linking"
            }

        temporal_links = []

        for i in range(len(selected_units) - 1):
            source_unit = selected_units[i]
            target_unit = selected_units[i + 1]

            prompt = f"""
请分析以下剧情单元之间的时序关联，并提取关键的时序上下文信息：

剧情单元{i+1}:
- ID: {source_unit.get('id')}
- 章节: {source_unit.get('chapter')}
- 文本: {source_unit.get('text', '')[:300]}

剧情单元{i+2}:
- ID: {target_unit.get('id')}
- 章节: {target_unit.get('chapter')}
- 文本: {target_unit.get('text', '')[:300]}

请以JSON格式返回：
{{
    "continuity_score": "连续性评分(0-1)",
    "key_characters": ["关键人物1", "关键人物2"],
    "key_events": ["关键事件1", "关键事件2"],
    "temporal_markers": ["时间标记1", "时间标记2"],
    "narrative_bridge": "叙事桥梁描述",
    "context_summary": "上下文摘要"
}}
"""

            try:
                response = Settings.llm.complete(prompt)
                link_text = response.text.strip()

                json_match = re.search(r'\{[\s\S]*\}', link_text)
                if json_match:
                    import json
                    link_data = json.loads(json_match.group())
                    link_data["source_unit_id"] = source_unit.get("id")
                    link_data["target_unit_id"] = target_unit.get("id")
                    temporal_links.append(link_data)
            except Exception as e:
                logger.warning(f"Failed to analyze temporal link: {e}")

        return {
            "context_available": len(temporal_links) > 0,
            "temporal_links": temporal_links,
            "total_units_analyzed": len(selected_units),
            "relevant_characters": list(set(
                char for link in temporal_links for char in link.get("key_characters", [])
            ))
        }


rag_service = RAGService()
