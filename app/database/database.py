from functools import lru_cache
from typing import List

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession as SAAsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base

from app.config import Config


@lru_cache
def engine_factory():
    return create_async_engine(Config.get("ASYNC_DB_CONNECT"))


def db_session_factory():
    return async_sessionmaker(engine_factory(), expire_on_commit=False, class_=SAAsyncSession)()


Model = declarative_base()


async def store_models_to_db(models: List[Model]) -> List[Model]:
    async with db_session_factory() as session:
        session.add_all(models)
        try:
            await session.commit()
        except SQLAlchemyError as exc:
            await session.rollback()
            raise DBException(exc)
        for model in models:
            await session.refresh(model)
        session.expunge_all()
    return models


class DBException(Exception):
    pass
