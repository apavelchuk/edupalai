import anyio
import tempfile

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from io import BytesIO
from uuid import uuid4
from fastapi import WebSocket
from google.cloud import texttospeech as gcp_tts, speech as gcp_stt
from google.cloud.speech_v1.types import cloud_speech as stt_types, RecognitionConfig

from gcloud.aio.auth import Token
from gcloud.aio.storage import Storage as StorageClient
from typing import Optional, Type, Awaitable
from enum import Enum

from pydantic import BaseModel

from google.cloud.speech_v1.services.speech import SpeechAsyncClient

from app.config import Config
from app.logger import log_exec_time, logger_factory
from app.models.content import ContentLanguage
from app.services.exceptions import ServiceException
from ..service import Service


def get_voice_params(lang: ContentLanguage) -> gcp_tts.VoiceSelectionParams:
    voice_name = get_voice_for_language(lang).value
    lang_code = "-".join(voice_name.split("-")[:2])
    return gcp_tts.VoiceSelectionParams(language_code=lang_code, name=voice_name)


class TextToVoice(Service):
    def __init__(
        self, tts_client: gcp_tts.TextToSpeechAsyncClient, audio_encoding: gcp_tts.AudioEncoding, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.tts_client: gcp_tts.TextToSpeechAsyncClient = tts_client
        self.audio_encoding = audio_encoding

    # @log_exec_time("text_to_audio")
    async def text_to_voice(self, lang: ContentLanguage, text: str) -> Awaitable[str]:
        text_input = gcp_tts.SynthesisInput(text=text)
        voice_params = get_voice_params(lang)
        audio_config = gcp_tts.AudioConfig(audio_encoding=self.audio_encoding)
        response = await self.tts_client.synthesize_speech(
            input=text_input,
            voice=voice_params,
            audio_config=audio_config,
        )
        out_ogg_path = await self._store_response_to_file(response.audio_content, "ogg")
        return out_ogg_path

    async def _store_audio_to_file(self, audio_content: bytes, file_ext: str) -> str:
        path = f"{tempfile.gettempdir()}/{uuid4()}.{file_ext}"
        async with await anyio.open_file(path, "wb") as f:
            await f.write(audio_content)
        return path


class StreamTextToVoice(TextToVoice):
    async def text_to_voice(
        self,
        lang: ContentLanguage,
        text_stream: AsyncIterator[str],
    ) -> AsyncIterator[bytes]:
        voice_params = get_voice_params(lang)
        audio_config = gcp_tts.AudioConfig(audio_encoding=self.audio_encoding, sample_rate_hertz=48000, pitch=0.0)

        async for text_chunk in text_stream:
            print("GPT says:", text_chunk)
            text_input = gcp_tts.SynthesisInput(text=text_chunk)
            response = await self.tts_client.synthesize_speech(
                input=text_input,
                voice=voice_params,
                audio_config=audio_config,
            )
            yield response.audio_content


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
    audio_encoding: Optional[gcp_tts.AudioEncoding] = gcp_tts.AudioEncoding.OGG_OPUS,
    stream: Optional[bool] = False,
) -> TextToVoice:
    if tts_client is None:
        tts_client = gcp_tts.TextToSpeechAsyncClient()
    logger = logger_factory("GCP TextToSpeech")
    if stream:
        return StreamTextToVoice(tts_client, audio_encoding, logger)
    return TextToVoice(tts_client, audio_encoding, logger)


class VTTResp(BaseModel):
    transcription: str
    confidence: float


class VoiceToText(Service):
    def __init__(self, client: gcp_stt.SpeechAsyncClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client: gcp_stt.SpeechAsyncClient = client

    async def ogg_to_text(self, lang: ContentLanguage, source_audio_content: BytesIO) -> VTTResp:
        config = self.get_config(lang, RecognitionConfig.AudioEncoding.OGG_OPUS)
        req = gcp_stt.RecognizeRequest(
            audio=gcp_stt.RecognitionAudio(content=source_audio_content),
            config=config,
        )
        resp = await self.client.recognize(req)
        self.validate_response(resp)

        best_alternative = resp.results[0].alternatives[0]
        return VTTResp(
            transcription=best_alternative.transcript,
            confidence=best_alternative.confidence,
        )

    async def voice_to_text(self, lang: ContentLanguage, source_audio_content: BytesIO) -> VTTResp:
        return await self.ogg_to_text(lang, source_audio_content)

    def get_config(self, lang: ContentLanguage, encoding: RecognitionConfig.AudioEncoding) -> gcp_stt.RecognitionConfig:
        return gcp_stt.RecognitionConfig(
            language_code=content_lang_to_gcp_lang_code(lang),
            encoding=encoding,
            enable_automatic_punctuation=True,
            model="latest_short",
            use_enhanced=False,
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


class VoiceToTextStream(VoiceToText):
    async def voice_to_text(
        self,
        lang: ContentLanguage,
        stream: AsyncIterator[bytes],
        encoding: Optional[RecognitionConfig.AudioEncoding] = RecognitionConfig.AudioEncoding.WEBM_OPUS,
    ) -> VTTResp:
        stream = await self.client.streaming_recognize(
            requests=self._request_generator_for_stream(stream, config=self.get_config(lang, encoding))
        )
        final_transcription = ""
        average_confidence = [0.0, 1]
        async for resp in stream:
            for interm_result in resp.results:
                best_alternative = interm_result.alternatives[0]
                final_transcription += best_alternative.transcript
                average_confidence[0] += best_alternative.confidence
                average_confidence[1] += 1
        return VTTResp(transcription=final_transcription, confidence=average_confidence[0] / average_confidence[1])

    async def _request_generator_for_stream(
        self,
        stream: AsyncIterator[bytes],
        config: stt_types.StreamingRecognitionConfig,
    ) -> AsyncIterator[stt_types.StreamingRecognizeRequest]:
        yield stt_types.StreamingRecognizeRequest(streaming_config=config)
        async for audio_data in stream:
            yield stt_types.StreamingRecognizeRequest(audio_content=audio_data)

    def get_config(
        self,
        lang: ContentLanguage,
        encoding: RecognitionConfig.AudioEncoding,
    ) -> stt_types.StreamingRecognitionConfig:
        return stt_types.StreamingRecognitionConfig(
            config=stt_types.RecognitionConfig(
                language_code=content_lang_to_gcp_lang_code(lang),
                encoding=encoding,
                sample_rate_hertz=48000,
                model="latest_short",
                audio_channel_count=1,
                enable_automatic_punctuation=True,
                use_enhanced=False,
                max_alternatives=1,
            ),
            interim_results=False,
        )


def voice_to_text_service_factory(
    stt_client: Optional[gcp_stt.SpeechAsyncClient] = None,
    stream: Optional[bool] = False,
) -> VoiceToText:
    if stt_client is None:
        stt_client = gcp_stt.SpeechAsyncClient()
    logger = logger_factory("GCP VoiceToText")
    if stream:
        return VoiceToTextStream(client=stt_client, logger=logger)
    return VoiceToText(stt_client, logger)


class AvailableBucket(Enum):
    PUBLIC_CONTENT = Config.get("GCP_PUBLIC_CONTENT_BUCKET")
    AI_REPLIES = Config.get("GCP_AI_REPLIES_BUCKET")


class Upload(Service):
    SCOPES = ("https://www.googleapis.com/auth/devstorage.read_write",)

    def __init__(self, token_class: Type[Token], client_class: Type[StorageClient], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token_class = token_class
        self.client_class = client_class

    @asynccontextmanager
    async def _new_session(self):
        token = self.token_class(service_file=Config.get("GOOGLE_APPLICATION_CREDENTIALS"), scopes=self.SCOPES)
        client = self.client_class(token=token)
        try:
            yield client
        finally:
            await client.close()
            await token.close()

    async def upload_public_content(self, source_path: str, dest_path: str) -> str:
        return await self._upload_obj(source_path, AvailableBucket.PUBLIC_CONTENT, dest_path)

    async def upload_ai_reply(self, source_path: str, dest_path: str) -> str:
        return await self._upload_obj(source_path, AvailableBucket.AI_REPLIES, dest_path)

    # @log_exec_time("upload_content_for_public_access")
    async def _upload_obj(self, source_path: str, bucket: AvailableBucket, dest_path: str):
        async with self._new_session() as client:
            resp: dict = await client.upload_from_filename(bucket.value, dest_path, source_path)
            await client.close()
            return resp["name"]


class UploadStream(Upload):
    async def upload_public_content(self, source_path: str, dest_path: str) -> str:
        raise NotImplementedError()

    async def upload_ai_reply(self, source_stream: AsyncIterator[bytes], dest_path: str) -> str:
        async with self._new_session() as client:
            async for reply_audio_chunk in source_stream:
                await self._stream_obj(client, reply_audio_chunk, AvailableBucket.AI_REPLIES, dest_path)
            return get_url_for_ai_reply_obj(dest_path)

    async def _stream_obj(
        self,
        client: StorageClient,
        data: bytes,
        bucket: AvailableBucket,
        dest_path: str,
    ) -> dict:
        return await client.upload(
            bucket=bucket.value,
            object_name=dest_path,
            file_data=data,
            content_type="audio/ogg",
            force_resumable_upload=True,
        )


def upload_service_factory(
    token_class: Optional[Type[Token]] = None,
    client_class: Optional[Type[StorageClient]] = None,
    stream: Optional[bool] = False,
) -> Upload:
    client_class = StorageClient if client_class is None else client_class
    token_class = Token if token_class is None else token_class
    logger = logger_factory("GCP Upload")
    if stream:
        return UploadStream(token_class, client_class, logger=logger)
    return Upload(token_class, client_class, logger=logger)


def get_url_for_storage_object(bucket: AvailableBucket, obj_name: str) -> str:
    return f"https://storage.googleapis.com/{bucket.value}/{obj_name}"


def get_url_for_public_content_obj(obj_name: str) -> str:
    return get_url_for_storage_object(AvailableBucket.PUBLIC_CONTENT, obj_name)


def get_url_for_ai_reply_obj(obj_name: str) -> str:
    return get_url_for_storage_object(AvailableBucket.AI_REPLIES, obj_name)
