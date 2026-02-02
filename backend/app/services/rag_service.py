from typing import List, Optional, Dict, Any
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.vector_stores.types import VectorStoreQueryMode
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core import Settings
from app.config import get_settings

settings = get_settings()

Settings.embed_model = OllamaEmbedding(model_name=settings.OLLAMA_EMBEDDING_MODEL, base_url=settings.OLLAMA_BASE_URL)
Settings.llm = Ollama(model=settings.LLM_MODEL, base_url=settings.OLLAMA_BASE_URL)


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

        self.vector_store = PGVectorStore(
            connection_string=settings.DATABASE_URL,
            table_name="story_units",
            embed_dim=1024,
        )
        storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        self.index = VectorStoreIndex.from_vector_store(self.vector_store, storage_context=storage_context)

    async def search_story_units(
        self,
        query: Optional[str] = None,
        conflict_type: Optional[str] = None,
        emotion_type: Optional[str] = None,
        character_relationship: Optional[str] = None,
        plot_function: Optional[str] = None,
        top_k: int = 5
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

        from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters

        filters = None
        if metadata_filters:
            filter_list = [
                ExactMatchFilter(key=key, value=value)
                for key, value in metadata_filters.items()
            ]
            filters = MetadataFilters(filters=filter_list)

        if query:
            retriever = self.index.as_retriever(
                similarity_top_k=top_k,
                filters=filters,
                vector_store_query_mode=VectorStoreQueryMode.HYBRID,
            )
            nodes = retriever.retrieve(query)
        else:
            from sqlalchemy import select
            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
            from sqlalchemy.orm import sessionmaker
            from app.models.story_unit import StoryUnit

            engine = create_async_engine(settings.DATABASE_URL)
            async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with async_session() as session:
                stmt = select(StoryUnit)
                if filters:
                    for key, value in metadata_filters.items():
                        stmt = stmt.where(getattr(StoryUnit, key) == value)
                stmt = stmt.limit(top_k)
                result = await session.execute(stmt)
                story_units = result.scalars().all()
                nodes = [self._story_unit_to_node(unit) for unit in story_units]

        return [self._node_to_dict(node) for node in nodes]

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
        return {
            "id": node.node_id,
            "text": node.text,
            "metadata": node.metadata,
            "score": node.score if hasattr(node, "score") else 0.0,
        }

    async def generate_script(
        self,
        plot_context: str,
        required_conflict: str,
        required_emotion: str,
        characters: List[str],
        scene: Optional[str] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        referenced_units = await self.search_story_units(
            query=plot_context,
            conflict_type=required_conflict,
            emotion_type=required_emotion,
            top_k=3
        )

        reference_context = "\n\n".join([
            f"参考剧情{idx+1}:\n{unit['text']}"
            for idx, unit in enumerate(referenced_units)
        ])

        prompt = f"""
请根据以下信息生成一场戏的剧本：

剧情上下文：
{plot_context}

需要的冲突类型：{required_conflict}
需要的情绪类型：{required_emotion}
出场人物：{', '.join(characters)}
场景：{scene if scene else '请根据剧情设定'}

参考剧情片段：
{reference_context}

生成要求：
1. 符合指定的冲突类型和情绪类型
2. 保持人物性格和关系的一致性
3. 对话自然，符合人物设定
4. 有明确的戏剧张力
5. 字数控制在500-800字

请生成剧本：
"""

        response = Settings.llm.complete(prompt)
        generated_script = response.text

        return {
            "generated_script": generated_script,
            "referenced_units": [unit["id"] for unit in referenced_units],
            "confidence": 0.8,
        }


rag_service = RAGService()
