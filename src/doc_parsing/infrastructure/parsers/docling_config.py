from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DoclingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["docling"] = Field(default="docling")
    picture_description: bool = False
    picture_prompt: str | None = None
    images_scale: float | None = None
    generate_picture_images: bool = False

    @model_validator(mode="after")
    def _validate_picture_prompt(self) -> DoclingConfig:
        if self.picture_prompt is not None and not self.picture_description:
            raise ValueError("picture_prompt requires picture_description=true")
        return self
