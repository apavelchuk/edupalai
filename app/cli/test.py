import click
import anyio
from app.models.content import ContentLanguage

from app.services import factories


async def foo_async():
    ai = factories.ai()
    reply_stream = ai.reply_stream("Hello how are you I'm fine thank you. Give me a couple of sentences as a response please.")
    ttv = factories.text_to_voice(stream=True)
    audio_stream = ttv.text_to_audio(ContentLanguage.ENGLISH, reply_stream)
    upload = factories.upload(stream=True)
    url = await upload.upload_ai_reply(audio_stream, "checkingout.ogg")


@click.command()
def command():
    anyio.run(foo_async)


if __name__ == "__main__":
    command()
