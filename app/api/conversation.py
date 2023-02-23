from os.path import basename
from fastapi import APIRouter, UploadFile, HTTPException
from pydantic import BaseModel

from app.models.content import ContentLanguage
from app.services.conversation import conversation_service_factory
from app.services.integrations import gcp

router = APIRouter()


class ConversationAIReply(BaseModel):
    reply_url: str


@router.post("/ask-ai", response_model=ConversationAIReply, summary="Main endpoint for conversations.")
async def conversation(lang: ContentLanguage, user_audio_reply: UploadFile):
    if user_audio_reply.content_type != "audio/ogg":
        raise HTTPException(status_code=400, detail="Only OGG format is supported for user replies.")

    conv_service = conversation_service_factory()
    reply_file_path = await conv_service.get_and_log_reply_for_audio(lang, user_audio_reply.file)
    upload_service = gcp.upload_service_factory()
    reply_upload_name = basename(reply_file_path)
    await upload_service.upload_ai_reply(reply_file_path, reply_upload_name)
    return ConversationAIReply(
        reply_url=gcp.get_url_for_ai_reply_obj(reply_upload_name)
    )
