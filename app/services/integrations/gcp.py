from io import BytesIO
import anyio
import tempfile

from uuid import uuid4
from google.cloud import texttospeech as gcp_tts, speech as gcp_stt
from google.cloud.texttospeech_v1.types import cloud_tts
from gcloud.aio.auth import Token
from gcloud.aio.storage import Storage as StorageClient
from typing import Optional, Type
from enum import Enum

from pydantic import BaseModel

from app.config import Config
from app.logger import log_exec_time, logger_factory
from app.models.content import ContentLanguage
from app.services.exceptions import ServiceException
from ..service import Service


class TextToVoice(Service):
    def __init__(self, tts_client: gcp_tts.TextToSpeechAsyncClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tts_client: gcp_tts.TextToSpeechAsyncClient = tts_client

    # @log_exec_time("text_to_ogg")
    async def text_to_ogg(self, lang: ContentLanguage, text: str) -> str:
        text_input = gcp_tts.SynthesisInput(text=text)
        voice_params = self._get_voice_params(lang)
        audio_config = gcp_tts.AudioConfig(audio_encoding=gcp_tts.AudioEncoding.OGG_OPUS)
        response = await self.tts_client.synthesize_speech(
            input=text_input,
            voice=voice_params,
            audio_config=audio_config,
        )
        out_ogg_path = await self._store_response_to_file(response, "ogg")
        return out_ogg_path

    def _get_voice_params(self, lang: ContentLanguage) -> gcp_tts.VoiceSelectionParams:
        voice_name = get_voice_for_language(lang).value
        lang_code = "-".join(voice_name.split("-")[:2])
        return gcp_tts.VoiceSelectionParams(language_code=lang_code, name=voice_name)

    async def _store_response_to_file(self, response: cloud_tts.SynthesizeSpeechResponse, file_ext: str) -> str:
        path = f"{tempfile.gettempdir()}/{uuid4()}.{file_ext}"
        async with await anyio.open_file(path, "wb") as f:
            await f.write(response.audio_content)
        return path


class AvailableVoice(Enum):
    ENGLISH = Config.get("GCP_ENGLISH_VOICE")
    RUSSIAN = Config.get("GCP_RUSSIAN_VOICE")


def get_voice_for_language(lang: ContentLanguage):
    return {
        ContentLanguage.ENGLISH: AvailableVoice.ENGLISH,
        ContentLanguage.RUSSIAN: AvailableVoice.RUSSIAN,
    }[lang]


def text_to_voice_service_factory(
    tts_client: Optional[gcp_tts.TextToSpeechAsyncClient] = None,
) -> TextToVoice:
    if tts_client is None:
        tts_client = gcp_tts.TextToSpeechAsyncClient()
    logger = logger_factory("GCP TextToSpeech")
    return TextToVoice(tts_client, logger)


class VTTResp(BaseModel):
    text: str
    confidence: float


class VoiceToText(Service):
    def __init__(self, client: gcp_stt.SpeechAsyncClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client: gcp_stt.SpeechAsyncClient = client

    async def ogg_to_text(self, lang: ContentLanguage, source_audio_content: BytesIO) -> VTTResp:
        config = self.get_config(lang)
        req = gcp_stt.RecognizeRequest(
            audio=gcp_stt.RecognitionAudio(content=source_audio_content),
            config=config,
        )
        resp = await self.client.recognize(req)
        self.validate_response(resp)

        best_alternative = resp.results[0].alternatives[0]
        return VTTResp(
            text=best_alternative.transcript,
            confidence=best_alternative.confidence,
        )

    def get_config(self, lang: ContentLanguage) -> gcp_stt.RecognitionConfig:
        return gcp_stt.RecognitionConfig(
            language_code=content_lang_to_gcp_lang_code(lang),
            encoding=gcp_stt.RecognitionConfig.AudioEncoding.OGG_OPUS,
            enable_automatic_punctuation=True,
            use_enhanced=True,
            max_alternatives=1,
            sample_rate_hertz=48000,
        )

    def validate_response(self, resp: gcp_stt.RecognizeResponse):
        if not resp.results or not resp.results[0].alternatives:
            raise ServiceException("Could not SpeechToText audio file.", self.logger)


def content_lang_to_gcp_lang_code(lang: ContentLanguage) -> str:
    return {
        ContentLanguage.ENGLISH: "en-US",
        ContentLanguage.RUSSIAN: "ru-RU",
    }[lang]


def voice_to_text_service_factory(
    stt_client: Optional[gcp_stt.SpeechAsyncClient] = None,
) -> VoiceToText:
    if stt_client is None:
        stt_client = gcp_stt.SpeechAsyncClient()
    logger = logger_factory("GCP VoiceToText")
    return VoiceToText(stt_client, logger)


class AvailableBucket(Enum):
    PUBLIC_CONTENT = Config.get("GCP_PUBLIC_CONTENT_BUCKET")
    AI_REPLIES = Config.get("GCP_AI_REPLIES_BUCKET")


class Upload(Service):
    SCOPES = ("https://www.googleapis.com/auth/devstorage.read_write",)

    def __init__(self, token_class: Type[Token], client_class: Type[StorageClient], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = token_class(service_file=Config.get("GOOGLE_APPLICATION_CREDENTIALS"), scopes=self.SCOPES)
        self.client_class = client_class

    async def upload_public_content(self, source_path: str, dest_path: str) -> str:
        return await self._upload_obj(source_path, AvailableBucket.PUBLIC_CONTENT, dest_path)

    async def upload_ai_reply(self, source_path: str, dest_path: str) -> str:
        return await self._upload_obj(source_path, AvailableBucket.AI_REPLIES, dest_path)

    # @log_exec_time("upload_content_for_public_access")
    async def _upload_obj(self, source_path: str, bucket: AvailableBucket, dest_path: str):
        async with self.token as token:
            async with self.client_class(token=token) as client:
                resp: dict = await client.upload_from_filename(bucket.value, dest_path, source_path)
                return resp["name"]


def upload_service_factory(
    token_class: Optional[Type[Token]] = None,
    client_class: Optional[Type[StorageClient]] = None,
) -> Upload:
    client_class = StorageClient if client_class is None else client_class
    token_class = Token if token_class is None else token_class
    logger = logger_factory("GCP Upload")
    return Upload(token_class, client_class, logger=logger)


def get_url_for_storage_object(bucket: AvailableBucket, obj_name: str) -> str:
    return f"https://storage.googleapis.com/{bucket.value}/{obj_name}"


def get_url_for_public_content_obj(obj_name: str) -> str:
    return get_url_for_storage_object(AvailableBucket.PUBLIC_CONTENT, obj_name)


def get_url_for_ai_reply_obj(obj_name: str) -> str:
    return get_url_for_storage_object(AvailableBucket.AI_REPLIES, obj_name)
