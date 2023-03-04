from fastapi import FastAPI

# from exceptions import register_exceptions
from app.api.content import router as content_router
from app.api.conversation import router as conversation_router
from app.web.index import router as web_index_router


app = FastAPI()
app.include_router(content_router, prefix="/content")
app.include_router(conversation_router, prefix="/conversation")
app.include_router(web_index_router, prefix="")

# app.include_router(user_router, prefix="/users")
# register_exceptions(app)
