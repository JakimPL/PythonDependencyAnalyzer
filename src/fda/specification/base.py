from pydantic import BaseModel, ConfigDict


class Specification(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
        frozen=True,
        use_enum_values=True,
    )
