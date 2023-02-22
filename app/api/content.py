from datetime import datetime
from fastapi import APIRouter, Query
from pydantic import BaseModel, validator
from uuid import UUID
from typing import Dict, Any, List, Optional

from app.models.content import ContentType, ContentLanguage
from app.services import content as content_service
from app.services.integrations.gcp import get_url_for_storage_object

router = APIRouter()


class ContentItem(BaseModel):
    id: UUID
    content: Dict[str, Any]
    content_type: ContentType
    language: ContentLanguage
    created_at: datetime
    audio_url: Optional[str] = None

    @validator("audio_url", pre=False)
    def modify_audio_url(cls, audio_url: str):
        if audio_url is not None and not audio_url.startswith("http"):
            return get_url_for_storage_object(audio_url)
        return audio_url

    class Config:
        orm_mode = True


@router.get("/random-item", response_model=ContentItem, summary="Return random content item.")
async def random_item(
    content_type: ContentType,
    lang: ContentLanguage,
    exclude_ids: Optional[List[UUID]] = Query(default=None)
):
    db_item = await content_service.get_random_content_item(content_type, lang, exclude_ids)
    if db_item:
        return ContentItem.from_orm(db_item)
