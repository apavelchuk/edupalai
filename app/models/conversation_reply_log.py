import uuid
import sqlalchemy as sa

from datetime import datetime
from sqlalchemy_utils.types.uuid import UUIDType
from sqlalchemy_utils.types.choice import ChoiceType

from app.database import Model
from app.models.content import ContentLanguage


class ConversationReplyLog(Model):
    __tablename__ = "conversation_reply_log"

    id = sa.Column(UUIDType(), primary_key=True, default=uuid.uuid4)
    user_reply = sa.Column(sa.Text(), nullable=False)
    language = sa.Column(ChoiceType(ContentLanguage, impl=sa.String()), nullable=False)
    metrics = sa.Column(sa.JSON(), nullable=True)
    created_at = sa.Column(sa.DateTime(), default=datetime.utcnow, nullable=False)
    # user_uuid?
