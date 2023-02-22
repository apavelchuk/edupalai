import anyio
import tempfile

from uuid import uuid4
from google.cloud import texttospeech as gcp_tts
from google.cloud.texttospeech_v1.types import cloud_tts
from gcloud.aio.auth import Token
from gcloud.aio.storage import Storage as StorageClient
from typing import Optional, Type
from enum import Enum

from app.config import Config
from app.logger import log_exec_time, logger_factory
from app.models.content import ContentLanguage
from ..service import Service


class TextToSpeech(Service):
    def __init__(self, lang: ContentLanguage, tts_client: gcp_tts.TextToSpeechAsyncClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.voice: AvailableVoice = get_voice_for_language(lang)
        self.tts_client: gcp_tts.TextToSpeechAsyncClient = tts_client

    @log_exec_time("text_to_mp3")
    async def text_to_mp3(self, text: str) -> str:
        text_input = gcp_tts.SynthesisInput(text=text)
        voice_params = self._get_voice_params()
        audio_config = gcp_tts.AudioConfig(audio_encoding=gcp_tts.AudioEncoding.MP3)
        response = await self.tts_client.synthesize_speech(
            input=text_input,
            voice=voice_params,
            audio_config=audio_config,
        )
        out_mp3_path = await self._store_response_to_file(response, "mp3")
        return out_mp3_path

    def _get_voice_params(self) -> gcp_tts.VoiceSelectionParams:
        voice_name = self.voice.value
        lang_code = "-".join(voice_name.split("-")[:2])
        return gcp_tts.VoiceSelectionParams(language_code=lang_code, name=voice_name)

    async def _store_response_to_file(self, response: cloud_tts.SynthesizeSpeechResponse, file_ext: str) -> str:
        path = f"{tempfile.gettempdir()}/{uuid4()}.{file_ext}"
        async with await anyio.open_file(path, 'wb') as f:
            await f.write(response.audio_content)
            await f.aclose()
        return path


class AvailableVoice(Enum):
    ENGLISH = Config.get("GCP_ENGLISH_VOICE")
    RUSSIAN = Config.get("GCP_RUSSIAN_VOICE")


def get_voice_for_language(lang: ContentLanguage):
    return {
        ContentLanguage.ENGLISH: AvailableVoice.ENGLISH,
        ContentLanguage.RUSSIAN: AvailableVoice.RUSSIAN,
    }[lang]


def text_to_speech_service_factory(
    lang: ContentLanguage,
    tts_client: Optional[gcp_tts.TextToSpeechAsyncClient] = None,
) -> TextToSpeech:
    if tts_client is None:
        tts_client = gcp_tts.TextToSpeechAsyncClient()
    logger = logger_factory("GCP TextToSpeech")
    return TextToSpeech(lang, tts_client, logger)


class Upload(Service):
    SCOPES = ('https://www.googleapis.com/auth/devstorage.read_write',)
    PUBLIC_CONTENT_BUCKET = Config.get("GCP_PUBLIC_CONTENT_BUCKET")

    def __init__(self, token_class: Type[Token], client_class: Type[StorageClient], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = token_class(service_file=Config.get("GOOGLE_APPLICATION_CREDENTIALS"), scopes=self.SCOPES)
        self.client_class = client_class

    @log_exec_time("upload_content_for_public_access")
    async def upload_content_for_public_access(self, source_path: str, dest_path: str) -> str:
        bucket = self.PUBLIC_CONTENT_BUCKET
        async with self.token as token:
            async with self.client_class(token=token) as client:
                resp: dict = await client.upload_from_filename(bucket, dest_path, source_path)
                return f"{bucket}/{resp['name']}"


def upload_service_factory(
    token_class: Optional[Type[Token]] = None,
    client_class: Optional[Type[StorageClient]] = None,
) -> Upload:
    if client_class is None:
        token_class = Token if token_class is None else token_class
        client_class = StorageClient
    logger = logger_factory("GCP Upload")
    return Upload(token_class, client_class, logger=logger)


def get_url_for_storage_object(obj_name_with_bucket: str) -> str:
    return f"https://storage.googleapis.com/{obj_name_with_bucket}"
