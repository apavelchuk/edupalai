from typing import Optional
from app.logger import logger_factory
from google.cloud import texttospeech as gcp_tts
from .integrations import gcp, openai as oai
from .conversation import Conversation


def conversation() -> Conversation:
    return Conversation(logger=logger_factory("Conversation Service"))


def upload(stream: Optional[bool] = False) -> gcp.Upload:
    return gcp.upload_service_factory(stream=stream)


def voice_to_text(stream: Optional[bool] = False, stream_end_message: Optional[bytes] = None) -> gcp.VoiceToText:
    return gcp.voice_to_text_service_factory(stream=stream, stream_end_message=stream_end_message)


def text_to_voice(
    stream: Optional[bool] = False,
    audio_encoding: Optional[gcp_tts.AudioEncoding] = gcp_tts.AudioEncoding.OGG_OPUS,
) -> gcp.TextToVoice:
    return gcp.text_to_voice_service_factory(stream=stream, audio_encoding=audio_encoding)


def ai() -> oai.AI:
    return oai.openai_service_factory()
