from os.path import basename
from fastapi import APIRouter, UploadFile, HTTPException
from fastapi import WebSocket
from pydantic import BaseModel
from app.api.exceptions import APIException

from app.models.content import ContentLanguage
from app.services import factories, utils
from app.services.service import time_it

STREAMING_AUDIO_START_MESSAGE = bytes("==[START]==", "utf-8")
STREAMING_AUDIO_END_MESSAGE = bytes("==[END]==", "utf-8")
router = APIRouter()


class ConversationAIReply(BaseModel):
    reply_url: str


@router.post("/ask-ai", response_model=ConversationAIReply, summary="Main endpoint for conversations.")
async def conversation(lang: ContentLanguage, user_audio_reply: UploadFile):
    if user_audio_reply.content_type != "audio/ogg":
        raise HTTPException(status_code=400, detail="Only OGG format is supported for user replies.")

    conv_service = factories.conversation()
    reply_file_path = await conv_service.get_and_log_reply_for_audio(lang, user_audio_reply.file)
    upload_service = factories.upload()
    reply_upload_name = basename(reply_file_path)
    await upload_service.upload_ai_reply(reply_file_path, reply_upload_name)
    return ConversationAIReply(
        reply_url=utils.get_url_for_ai_reply_obj(reply_upload_name)
    )


@router.websocket("/ask-ai-stream")
async def conversation_stream(lang: ContentLanguage, websocket: WebSocket):
    await websocket.accept()

    voice_to_text_service = factories.voice_to_text(stream=True, stream_end_message=STREAMING_AUDIO_END_MESSAGE)
    try:
        while True:
            audio_data = await websocket.receive_bytes()
            if audio_data == STREAMING_AUDIO_START_MESSAGE:
                time_taken, vtt_resp = await time_it(voice_to_text_service.voice_to_text)(lang=lang, stream=websocket)
                await stream_reply_to_websocket(vtt_resp.transcription, lang, websocket)
                # time_taken, reply_audio_url = await time_it(reply_and_upload_to_cloud)(vtt_resp.transcription, lang)
                # await websocket.send_json({
                #     "reply_total_time_taken": time_taken,
                #     "transcription_text": vtt_resp.transcription,
                #     "transcription_approx_confidence": vtt_resp.confidence,
                #     "reply_audio_url": reply_audio_url,
                # })
            else:
                raise APIException(f"""
                    Unexpected content. Use \"{STREAMING_AUDIO_START_MESSAGE}\" to start
                     and \"{STREAMING_AUDIO_END_MESSAGE}\" to end the stream.
                """)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise APIException(f'Could not process audio: {exc}')
    finally:
        await websocket.close()


async def reply_and_upload_to_cloud(reply_to: str, lang: ContentLanguage):
    ai = factories.ai()
    ttv = factories.text_to_voice(stream=True)
    upload = factories.upload(stream=True)

    reply_stream = ai.reply_stream(reply_to)
    audio_stream = ttv.text_to_audio(lang, reply_stream)
    url = await upload.upload_ai_reply(audio_stream, "checkingout.ogg")
    return url


async def stream_reply_to_websocket(reply_to: str, lang: ContentLanguage, websocket: WebSocket):
    from google.cloud import texttospeech as gcp_tts
    ai = factories.ai()
    ttv = factories.text_to_voice(stream=True, audio_encoding=gcp_tts.AudioEncoding.MP3)

    reply_stream = ai.reply_stream(reply_to)
    audio_stream = ttv.text_to_audio(lang, reply_stream)
    async for audio_data in audio_stream:
        await websocket.send_bytes(audio_data)
