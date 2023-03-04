import uuid

from enum import Enum
from datetime import datetime
from sqlalchemy import Column, String, Text, JSON, DateTime
from sqlalchemy_utils.types.uuid import UUIDType
from sqlalchemy_utils.types.choice import ChoiceType

from app.database import Model


class ContentType(Enum):
    TALE = "t"
    FACT = "f"


class ContentLanguage(Enum):
    ENGLISH = "en"
    RUSSIAN = "ru"


class Content(Model):
    __tablename__ = "content"

    id = Column("id", UUIDType(), primary_key=True, default=uuid.uuid4)
    content = Column("content", JSON(), nullable=False)
    content_type = Column("content_type", ChoiceType(ContentType, impl=String()), nullable=False)
    language = Column("language", ChoiceType(ContentLanguage, impl=String()), nullable=False)
    audio_url = Column("audio_url", Text(), nullable=True)
    created_at = Column("created_at", DateTime(), default=datetime.utcnow, nullable=False)
