from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=10_000)


class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, max_length=10_000)


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        """SQLite хранит время без таймзоны — явно помечаем его UTC."""
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.isoformat()
