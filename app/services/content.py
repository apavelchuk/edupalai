import os
import asyncio
import sqlalchemy as sa
import random

from typing import List, Awaitable, Optional
from uuid import UUID
from app.database import store_models_to_db, db_session_factory

from app.models.content import Content, ContentLanguage, ContentType
from app.services.integrations.gcp import text_to_speech_service_factory, upload_service_factory
from app.services.integrations.openai import generate_content as new_ai_content


async def generate_new_content_and_store_in_db(
    content_type: ContentType,
    lang: ContentLanguage,
    count: int = 1
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
    text = new_ai_content(content_type, lang)  # TODO: this will need to be converted to async as well
    tts_service = text_to_speech_service_factory(lang)
    mp3_file_path = await tts_service.text_to_mp3(text)
    upload_to_path = os.path.basename(mp3_file_path)
    upload_service = upload_service_factory()
    audio_url = await upload_service.upload_content_for_public_access(mp3_file_path, upload_to_path)
    os.remove(mp3_file_path)
    content = Content(
        content={"text": text},
        content_type=content_type,
        language=lang,
        audio_url=audio_url,
    )
    return content


async def get_random_content_item(
    content_type: ContentType,
    lang: ContentLanguage,
    exclude_ids: Optional[List[UUID]]
) -> Content | None:
    content_query = sa.select(Content).where(sa.and_(
        Content.content_type == content_type,
        Content.language == lang
    ))
    if exclude_ids:
        content_query = content_query.where(Content.id.not_in(exclude_ids))
    count_query = sa.select(sa.func.count()).select_from(content_query)

    async with db_session_factory() as db:
        total = await db.scalar(count_query)
        random_item_pos = random.randint(0, total - 1)
        try:
            random_content_item = (await db.scalars(content_query.offset(random_item_pos).limit(1))).one()
        except sa.exc.NoResultFound:
            random_content_item = None
        return random_content_item
