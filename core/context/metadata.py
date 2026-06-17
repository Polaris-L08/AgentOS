import uuid

from pydantic import BaseModel, Field


class ContextMetadata(BaseModel):

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))