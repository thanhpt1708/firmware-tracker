"""Configuration models using Pydantic."""

from typing import Self

import yaml
from pydantic import BaseModel, Field, model_validator


class ModelConfig(BaseModel):
    """Configuration for a single tracked model."""

    id: str = Field(..., description="Unique identifier/slug for the model")
    name: str = Field(..., description="Display name for the model")
    url: str = Field(default="", description="Base firmware directory URL or portal URL")
    brand: str = Field(default="draytek", description="Brand: 'draytek' or 'hikvision'")
    region: str = Field(default="Asia", description="Region preference for Hikvision (e.g. Asia, Europe)")
    model_name_match: str | None = Field(default=None, description="Optional custom string to match in catalog")
    enabled: bool = Field(default=True, description="Whether to monitor this model")

    @model_validator(mode="after")
    def validate_url(self) -> Self:
        if self.brand.lower() == "hikvision" and not self.url:
            self.url = "https://www.hikvision.com/en/support/download/firmware/"
        elif self.brand.lower() == "draytek" and not self.url:
            raise ValueError("URL is required for DrayTek models")
        return self


class TrackerConfig(BaseModel):
    """Root configuration containing models grouped by vendor or flat list."""

    draytek: list[ModelConfig] = Field(default_factory=list, description="DrayTek models")
    hikvision: list[ModelConfig] = Field(default_factory=list, description="Hikvision models")
    models: list[ModelConfig] = Field(default_factory=list, description="Legacy flat list of models")

    @model_validator(mode="before")
    @classmethod
    def set_brand_defaults(cls, data: object) -> object:
        if isinstance(data, dict):
            # Auto-assign brand='draytek' for items in draytek list
            if "draytek" in data and isinstance(data["draytek"], list):
                for item in data["draytek"]:
                    if isinstance(item, dict) and "brand" not in item:
                        item["brand"] = "draytek"
            # Auto-assign brand='hikvision' for items in hikvision list
            if "hikvision" in data and isinstance(data["hikvision"], list):
                for item in data["hikvision"]:
                    if isinstance(item, dict) and "brand" not in item:
                        item["brand"] = "hikvision"
        return data

    @classmethod
    def from_yaml(cls, path: str) -> Self:
        """Load and validate configuration from YAML file."""
        with open(path, encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}
        return cls.model_validate(raw_data)

    def get_all_models(self) -> list[ModelConfig]:
        """Return all models combined from all vendor sections."""
        return self.draytek + self.hikvision + self.models

    def get_enabled_models(self) -> list[ModelConfig]:
        """Return only models with enabled=True."""
        return [m for m in self.get_all_models() if m.enabled]
