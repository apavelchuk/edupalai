from io import BytesIO
from typing import Optional
from tempfile import SpooledTemporaryFile
from pydantic import BaseModel

from app.logger import logger_factory
from app.database.database import store_models_to_db
from app.models.conversation_reply_log import ConversationReplyLog
from app.models.content import ContentLanguage
from .integrations import gcp
from .service import Service, time_it


class Conversation(Service):
    async def get_and_log_reply_for_audio(self, lang: ContentLanguage, source_audio_file: SpooledTemporaryFile) -> str:
        source_audio_content = source_audio_file.read()
        vtt_time, vtt_resp = await self.get_text_for_audio(source_audio_content, lang)
        ai_reply_time, ai_resp = await self.get_ai_reply(lang, vtt_resp.text)
        ttv_time, dest_audio = await self.get_audio_for_text(lang, ai_resp)
        await log_response_to_db(ReplyLogEntry(
            lang=lang,
            user_reply=vtt_resp.text,
            user_reply_confidence_score=vtt_resp.confidence,
            vtt_time=vtt_time,
            ttv_time=ttv_time,
            ai_reply_length=len(ai_resp),
            ai_reply_time=ai_reply_time,
        ))
        return dest_audio

    @time_it
    async def get_text_for_audio(self, source_audio_content: BytesIO, lang: ContentLanguage) -> gcp.VTTResp:
        vtt_service = gcp.voice_to_text_service_factory()
        resp: gcp.VTTResp = await vtt_service.ogg_to_text(lang, source_audio_content)
        return resp

    @time_it
    async def get_ai_reply(self, lang: ContentLanguage, text: str) -> str:
        # TODO: AI response here
        return text

    @time_it
    async def get_audio_for_text(self, lang: ContentLanguage, text: str) -> str:
        ttv_service = gcp.text_to_voice_service_factory()
        out_audio: str = await ttv_service.text_to_ogg(lang, text)
        return out_audio


def conversation_service_factory() -> Conversation:
    return Conversation(logger=logger_factory("Conversation Service"))


class ReplyLogEntry(BaseModel):
    lang: ContentLanguage
    user_reply: str
    user_reply_confidence_score: Optional[float]
    vtt_time: Optional[float]
    ttv_time: Optional[float]
    ai_reply_length: Optional[int]
    ai_reply_time: Optional[float]
    # audio_uri?


async def log_response_to_db(log_entry: ReplyLogEntry):
    log_entry = ConversationReplyLog(
        user_reply=log_entry.user_reply,
        language=log_entry.lang,
        metrics={
            "user_reply_confidence_score": log_entry.user_reply_confidence_score,
            "vtt_time": log_entry.vtt_time,
            "ttv_time": log_entry.ttv_time,
            "ai_reply_length": log_entry.ai_reply_length,
            "ai_reply_time": log_entry.ai_reply_time,
        },
    )
    await store_models_to_db([log_entry])
