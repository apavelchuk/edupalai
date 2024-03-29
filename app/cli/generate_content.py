import click
import anyio

from app.models.content import ContentLanguage, ContentType
from app.services.content import generate_new_content_and_store_in_db


@click.command()
@click.option("--content-type", help="Content type. Must be one of ContentType enum values.", required=True)
@click.option("--count", default=1, help="Number of entries to generate.", type=int)
@click.option("--lang", default=ContentLanguage.ENGLISH, help="Language to generate content in.", type=ContentLanguage)
def command(content_type: str, count: int, lang: ContentLanguage):
    content_type = ContentType(content_type)
    models = anyio.run(generate_new_content_and_store_in_db, content_type, lang, count)
    click.echo(click.style(f"Successfully generated {len(models)} models.", fg="green"))


if __name__ == "__main__":
    command()
