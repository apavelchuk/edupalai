import os
import asyncio
import sqlalchemy as sa
import random

from typing import List, Awaitable, Optional
from uuid import UUID
from app.database import store_models_to_db, db_session_factory

from app.models.content import Content, ContentLanguage, ContentType
from app.services import factories


async def generate_new_content_and_store_in_db(
    content_type: ContentType, lang: ContentLanguage, count: int = 1
) -> Awaitable[List[Content]]:
    tasks = []
    for _ in range(count):
        task = asyncio.create_task(gen_new_content_and_upload_for_public_access(content_type, lang))
        tasks.append(task)
    models = await asyncio.gather(*tasks)
    models = await store_models_to_db(models)
    return models


async def gen_new_content_and_upload_for_public_access(
    content_type: ContentType,
    lang: ContentLanguage,
) -> Awaitable[Content]:
    text = await factories.ai().generate_content(content_type, lang)
    tts_service = factories.text_to_voice()
    audio_file_path = await tts_service.text_to_audio(lang, text)
    upload_to_path = os.path.basename(audio_file_path)
    upload_service = factories.upload()
    audio_url = await upload_service.upload_public_content(audio_file_path, upload_to_path)
    os.remove(audio_file_path)
    content = Content(
        content={"text": text},
        content_type=content_type,
        language=lang,
        audio_url=audio_url,
    )
    return content


async def get_random_content_item(
    content_type: ContentType, lang: ContentLanguage, exclude_ids: Optional[List[UUID]]
) -> Content | None:
    content_query = sa.select(Content).where(sa.and_(Content.content_type == content_type, Content.language == lang))
    if exclude_ids:
        content_query = content_query.where(Content.id.not_in(exclude_ids))
    count_query = sa.select(sa.func.count()).select_from(content_query)

    async with db_session_factory() as db:
        total = await db.scalar(count_query)
        if total == 0:
            return None
        random_item_pos = random.randint(0, total - 1)
        random_content_item = (await db.scalars(content_query.offset(random_item_pos).limit(1))).one()
        return random_content_item
