FROM python:3.10-alpine

ENV ASYNC_DB_CONNECT="postgresql+asyncpg://edupalai:edupalai@edupalai-db/edupalai"

RUN apk update && apk add postgresql-dev python3-dev gcc musl-dev linux-headers libc-dev g++

COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt

WORKDIR /app
CMD ["uvicorn", "--host", "0.0.0.0", "fastapi_app:app", "--reload"]
