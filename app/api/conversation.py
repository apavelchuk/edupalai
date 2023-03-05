import traceback

from os.path import basename
from fastapi import APIRouter, UploadFile, HTTPException
from fastapi import WebSocket
from pydantic import BaseModel
from app.api.exceptions import APIException
from collections.abc import AsyncIterator

from app.models.content import ContentLanguage
from app.services import factories, utils

STREAMING_AUDIO_START_MESSAGE = bytes("==[START]==", "utf-8")
STREAMING_AUDIO_END_MESSAGE = bytes("==[END]==", "utf-8")
router = APIRouter()


class AIReplyWithURL(BaseModel):
    reply_url: str


@router.post("/ask-ai", response_model=AIReplyWithURL, summary="Main endpoint for conversations.")
async def conversation(lang: ContentLanguage, user_audio_reply: UploadFile):
    if user_audio_reply.content_type != "audio/ogg":
        raise HTTPException(status_code=400, detail="Only OGG format is supported for user replies.")

    conv_service = factories.conversation()
    reply_file_path = await conv_service.get_and_log_reply_for_audio(lang, user_audio_reply.file)
    upload_service = factories.upload()
    reply_upload_name = basename(reply_file_path)
    await upload_service.upload_ai_reply(reply_file_path, reply_upload_name)
    return AIReplyWithURL(reply_url=utils.get_url_for_ai_reply_obj(reply_upload_name))


@router.websocket("/ask-ai-stream")
async def conversation_stream(lang: ContentLanguage, websocket: WebSocket):
    await websocket.accept()

    conv_service = factories.conversation()
    try:
        while True:
            audio_data = await websocket.receive_bytes()
            if audio_data == STREAMING_AUDIO_START_MESSAGE:
                reply_stream = conv_service.get_and_log_stream_reply(lang, websocket_user_audio_stream(websocket))
                async for reply_data in reply_stream:
                    await websocket.send_bytes(reply_data)
            else:
                raise APIException(
                    f"""
                    Unexpected content. Use \"{STREAMING_AUDIO_START_MESSAGE}\" to start
                     and \"{STREAMING_AUDIO_END_MESSAGE}\" to end the stream.
                """
                )
    except Exception:
        raise APIException(f"Could not process audio: \n {traceback.format_exc()}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


async def websocket_user_audio_stream(websocket: WebSocket) -> AsyncIterator[bytes]:
    while (audio_data := await websocket.receive_bytes()) != STREAMING_AUDIO_END_MESSAGE:
        yield audio_data


async def reply_and_upload_to_cloud(reply_to: str, lang: ContentLanguage):
    ai = factories.ai()
    ttv = factories.text_to_voice(stream=True)
    upload = factories.upload(stream=True)

    reply_stream = ai.reply_stream(reply_to)
    audio_stream = ttv.text_to_voice(lang, reply_stream)
    url = await upload.upload_ai_reply(audio_stream, "checkingout.ogg")
    return url
