"""Modeles Pydantic pour le form filler."""

from pydantic import BaseModel, Field
from typing import Optional


class FieldPosition(BaseModel):
    x: float = 0
    y: float = 0
    w: float = 30
    h: float = 3
    page: int = 0


class DetectedField(BaseModel):
    id: str
    label: str
    field_type: str = "text"
    position: FieldPosition = Field(default_factory=FieldPosition)
    description: str = ""
    required: bool = False
    group: str = "autre"
    options: list[str] = Field(default_factory=list)
    value: Optional[str] = None
    placeholder: str = ""
    profile_key: Optional[str] = None


class AnalysisResult(BaseModel):
    form_title: str = "Formulaire"
    form_type: str = ""
    description: str = ""
    fields: list[DetectedField] = Field(default_factory=list)
    page_count: int = 1
    warnings: list[str] = Field(default_factory=list)
