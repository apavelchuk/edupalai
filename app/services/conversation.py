from io import BytesIO
from typing import Optional
from tempfile import SpooledTemporaryFile
from pydantic import BaseModel
from collections.abc import AsyncIterator

from app.database.database import store_models_to_db
from app.models.conversation_reply_log import ConversationReplyLog
from app.models.content import ContentLanguage
from google.cloud import texttospeech as gcp_tts
from .integrations import gcp
from .service import Service, time_it
from . import factories


class Conversation(Service):
    async def get_and_log_reply_for_audio(self, lang: ContentLanguage, source_audio_file: SpooledTemporaryFile) -> str:
        source_audio_content = source_audio_file.read()
        vtt_time, vtt_resp = await self.get_text_for_audio(source_audio_content, lang)
        ai_reply_time, ai_resp = await self.get_ai_reply(lang, vtt_resp.text)
        ttv_time, dest_audio = await self.get_audio_for_text(lang, ai_resp)
        await log_response_to_db(
            ReplyLogEntry(
                lang=lang,
                user_reply=vtt_resp.transcript,
                user_reply_confidence_score=vtt_resp.confidence,
                vtt_time=vtt_time,
                ttv_time=ttv_time,
                ai_reply_length=len(ai_resp),
                ai_reply_time=ai_reply_time,
            )
        )
        return dest_audio

    @time_it
    async def get_text_for_audio(self, source_audio_content: BytesIO, lang: ContentLanguage) -> gcp.VTTResp:
        vtt_service = factories.voice_to_text()
        resp: gcp.VTTResp = await vtt_service.voice_to_text(lang, source_audio_content)
        return resp

    @time_it
    async def get_ai_reply(self, lang: ContentLanguage, text: str) -> str:
        ai = factories.ai()
        return ai.reply(text)

    @time_it
    async def get_audio_for_text(self, lang: ContentLanguage, text: str) -> str:
        ttv_service = factories.text_to_voice()
        out_audio: str = await ttv_service.text_to_voice(lang, text)
        return out_audio

    async def get_and_log_stream_reply(
        self, lang: ContentLanguage, incoming_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[bytes]:
        voice_to_text_service = factories.voice_to_text(stream=True)
        ai = factories.ai()
        ttv = factories.text_to_voice(stream=True, audio_encoding=gcp_tts.AudioEncoding.MP3)

        vtt_resp = await voice_to_text_service.voice_to_text(lang, incoming_stream)
        reply_stream = ai.reply_stream(vtt_resp.transcription)
        audio_stream = ttv.text_to_voice(lang, reply_stream)
        # TODO: Add logging here when needed
        async for audio_data in audio_stream:
            yield audio_data


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
