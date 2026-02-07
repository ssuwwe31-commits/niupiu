import os
import re
import time
import chardet
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.config import get_settings
from app.services.ollama_client import get_ollama_manager
import json
import logging

logger = logging.getLogger(__name__)

settings = get_settings()


class NovelService:
    def __init__(self):
        self.upload_dir = Path("uploads/novels")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self._ollama_manager = get_ollama_manager()
        self.chapter_map = {
            '一、人妖': 1,
            '一、人妖（续）': 1,
            '二、杨素瑶': 2,
            '三、绿毛水怪': 3,
            '战福': 4,
            '这是真的': 5
        }

    @property
    def llm(self):
        if settings.ENABLE_DEEPSEEK and settings.DEEPSEEK_API_KEY:
            from app.services.deepseek_client import RequestsDeepSeekLLM
            if not hasattr(self, '_deepseek_llm'):
                self._deepseek_llm = RequestsDeepSeekLLM(
                    model_name=settings.DEEPSEEK_MODEL,
                    api_key=settings.DEEPSEEK_API_KEY,
                    base_url=settings.DEEPSEEK_BASE_URL,
                    temperature=0.7,
                    top_p=0.95,
                    max_tokens=8192
                )
            return self._deepseek_llm
        else:
            if not self._ollama_manager._initialized:
                raise RuntimeError("Ollama client manager not initialized. Call initialize() first.")
            return self._ollama_manager.llm_long_timeout

    async def save_uploaded_file(self, file_content: bytes, filename: str) -> str:
        file_ext = Path(filename).suffix.lower()
        if file_ext not in ['.txt', '.epub']:
            raise ValueError(f"不支持的文件类型: {file_ext}")

        timestamp = int(time.time())
        file_path = self.upload_dir / f"{timestamp}_{Path(filename).stem}{file_ext}"
        file_path.write_bytes(file_content)
        return str(file_path)

    def clean_text(self, text: str) -> str:
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'第[一二三四五六七八九十百千万0-9]+[章回节]', '\n\\g<0>\n', text)
        return text.strip()

    def split_by_chapters(self, text: str) -> List[Dict[str, Any]]:
        chapter_patterns = [
            r'^[一二三四五六七八九十百千万]+、.+',
            r'^第[一二三四五六七八九十百千万0-9]+[章回节]',
            r'^[0-9]+[\.、].+'
        ]
        
        chapters = []

        for pattern in chapter_patterns:
            matches = list(re.finditer(pattern, text, re.MULTILINE))
            if len(matches) >= 2:
                chapters = []
                for i, match in enumerate(matches):
                    start = match.end()
                    end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

                    chapter_title = match.group().strip()
                    chapter_content = text[start:end].strip()

                    if len(chapter_content) > 100:
                        chapters.append({
                            "chapter_num": i + 1,
                            "title": chapter_title,
                            "content": chapter_content
                        })
                if chapters:
                    break

        if not chapters:
            chapters = [{
                "chapter_num": 1,
                "title": "全文",
                "content": text
            }]

        return chapters

    async def decompose_chapter_to_units(
        self,
        chapter: Dict[str, Any],
        novel_id: str
    ) -> List[Dict[str, Any]]:
        content = chapter["content"]
        logger.info(f"开始拆解章节: {chapter.get('title')}, 内容长度: {len(content)}")

        MAX_CONTENT_LENGTH = 8000

        if len(content) > MAX_CONTENT_LENGTH:
            segments = []
            for i in range(0, len(content), MAX_CONTENT_LENGTH):
                segment = content[i:i + MAX_CONTENT_LENGTH]
                if i > 0:
                    last_newline = segment.rfind('\n', 0, 500)
                    if last_newline > 0:
                        segment = segment[last_newline + 1:]
                segments.append(segment)
        else:
            segments = [content]

        logger.info(f"章节分为 {len(segments)} 个片段")
        all_units = []

        for seg_idx, segment in enumerate(segments, 1):
            logger.info(f"处理片段 {seg_idx}/{len(segments)}, 长度: {len(segment)}")
            prompt = f"""
请分析以下小说章节片段，将其拆解为剧情单元。

章节信息：
- 章节序号：{chapter['chapter_num']}
- 章节标题：{chapter['title']}
- 原章节长度：{len(content)}字
- 当前片段：{seg_idx}/{len(segments)}（本片段{len(segment)}字）

章节内容片段：
{segment}

请按照以下JSON格式输出剧情单元列表：
[
  {{
    "chapter": "章节名称",
    "scene": "场景描述（简洁，20字以内）",
    "characters": ["人物1", "人物2"],
    "core_conflict": "核心冲突描述（30-50字）",
    "emotion_curve": ["情绪1", "情绪2", "情绪3"],
    "plot_function": "剧情功能（如：铺垫、冲突、转折、高潮、收尾）",
    "original_text": "原文片段（50-100字，必须是原文中的内容）",
    "confidence": 0.85
  }}
]

要求：
1. 每个剧情单元是一个相对完整的情节片段，要有明确的场景转换或情节转折
2. 识别场景、人物、冲突、情绪等关键要素，人物关系要准确
3. 提取对应的原文片段（保持原汁原味，50-100字）
4. 确保JSON格式正确，可以直接解析
5. 根据片段长度合理拆分，通常3-8个单元
6. 情感曲线要反映情节的发展变化（如：平静→紧张→高潮→缓解）
7. 只返回JSON数组，不要包含其他内容
"""

            try:
                logger.info(f"开始调用 LLM, prompt长度: {len(prompt)}")
                logger.info(f"当前 LLM 类型: {type(self.llm)}")
                logger.info(f"API Key: {self.llm.api_key[:10]}...")
                logger.info(f"Base URL: {self.llm.base_url}")
                response = self.llm.complete(prompt)
                logger.info(f"LLM 响应已返回")
                response_text = response.text.strip()
                
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                elif response_text.startswith('```'):
                    response_text = response_text[3:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                response_text = response_text.strip()

                try:
                    json_start = response_text.find('[')
                    json_end = response_text.rfind(']') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_text = response_text[json_start:json_end]
                        units = json.loads(json_text)
                    else:
                        units = []
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {e}, 原始输出前500字符: {response_text[:500]}")
                    units = []

                for unit in units:
                    if isinstance(unit, dict):
                        chapter_name = unit.get("chapter", chapter.get('title', ''))
                        chapter_num = self.chapter_map.get(chapter_name, chapter.get('chapter_num', 1))
                        
                        unit["chapter"] = chapter_num
                        unit["source_novel_id"] = novel_id
                        unit["confidence_score"] = unit.get("confidence", 0.7)
                        unit.pop("confidence", None)
                        unit["conflict_type"] = unit.get("conflict_type", "general")
                        unit["emotion_type"] = unit.get("emotion_type", "neutral")
                        unit["character_relationship"] = unit.get("character_relationship", "")
                        unit["time_position"] = unit.get("time_position", "development")
                        unit["result"] = unit.get("result", "")
                        
                        if not unit.get("emotion_curve"):
                            unit["emotion_curve"] = ["neutral"]
                        if not unit.get("plot_function"):
                            unit["plot_function"] = "exposition"
                            
                        all_units.append(unit)
                        
            except Exception as e:
                logger.error(f"拆解章节 {chapter.get('title')} 片段 {seg_idx} 时出错: {e}")
                continue

        return all_units

    async def decompose_novel(
        self,
        novel_id: str,
        chapter_range: Optional[tuple[int, int]] = None
    ) -> Dict[str, Any]:
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from app.models.novel import Novel

        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            result = await session.execute(select(Novel).where(Novel.id == novel_id))
            novel = result.scalar_one_or_none()

            if not novel:
                return {"error": "小说不存在"}

            file_path = Path(novel.file_path)
            if not file_path.exists():
                return {"error": "小说文件不存在"}

            if file_path.suffix.lower() == '.txt':
                with open(file_path, 'rb') as f:
                    raw_content = f.read()
                    detected = chardet.detect(raw_content)
                    content = raw_content.decode(detected['encoding'] or 'utf-8')
            else:
                content = ""

            content = self.clean_text(content)
            chapters = self.split_by_chapters(content)

            if chapter_range:
                start_chapter, end_chapter = chapter_range
                chapters = chapters[start_chapter - 1:end_chapter]

            all_units = []
            success_count = 0
            failed_count = 0

            for chapter in chapters:
                try:
                    units = await self.decompose_chapter_to_units(chapter, novel_id)
                    all_units.extend(units)
                    success_count += len(units)
                except Exception as e:
                    failed_count += 1

            novel.total_chapters = len(chapters)
            novel.total_units = len(all_units)
            novel.status = "decomposed"
            await session.commit()

            return {
                "novel_id": novel_id,
                "total_units": len(all_units),
                "success_count": success_count,
                "failed_count": failed_count,
                "units": all_units,
                "message": f"成功拆解 {len(all_units)} 个剧情单元"
            }


novel_service = NovelService()
