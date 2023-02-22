from fastapi import FastAPI

# from exceptions import register_exceptions
from app.api.content import router as content_router

app = FastAPI()
app.include_router(content_router, prefix="/content")

# app.include_router(user_router, prefix="/users")
# register_exceptions(app)
