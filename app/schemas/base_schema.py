from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base for every payload: immutable, and unknown fields are an error."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)
