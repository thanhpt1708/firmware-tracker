"""Configuration models using Pydantic."""

from typing import List
from pydantic import BaseModel, Field
import yaml


class ModelConfig(BaseModel):
    """Configuration for a single DrayTek model."""

    id: str = Field(..., description="Unique identifier/slug for the model")
    name: str = Field(..., description="Display name for the model")
    url: str = Field(..., description="Base firmware directory URL")
    enabled: bool = Field(default=True, description="Whether to monitor this model")


class TrackerConfig(BaseModel):
    """Root configuration containing all models."""

    models: List[ModelConfig] = Field(default_factory=list, description="List of tracked models")

    @classmethod
    def from_yaml(cls, path: str) -> "TrackerConfig":
        """Load and validate configuration from YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}
        return cls.model_validate(raw_data)

    def get_enabled_models(self) -> List[ModelConfig]:
        """Return only models with enabled=True."""
        return [m for m in self.models if m.enabled]

