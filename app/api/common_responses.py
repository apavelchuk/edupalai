from pydantic import BaseModel


class GetWithOffsetAndLimit(BaseModel):
    limit: int
    offset: int
