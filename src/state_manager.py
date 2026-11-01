"""State manager for storing and retrieving tracking history."""

import json
import os
from typing import Any, Dict, Optional

from packaging.version import InvalidVersion, parse as parse_version


def is_new_or_different(known_version: Optional[str], detected_version: str) -> bool:
    """Check if detected version is new or newer than known version.

    Uses packaging.version.parse for reliable PEP 440 comparison.
    Falls back to string inequality if version strings are non-standard.
    """
    if not known_version:
        return True

    known_clean = known_version.strip().lstrip("vV")
    detected_clean = detected_version.strip().lstrip("vV")

    if known_clean == detected_clean:
        return False

    try:
        return parse_version(detected_clean) > parse_version(known_clean)
    except (InvalidVersion, TypeError):
        return known_clean != detected_clean


class StateManager:
    """Manages reading and writing state.json."""

    def __init__(self, state_file: str = "data/state.json"):
        self.state_file = state_file

    def load(self) -> Dict[str, Any]:
        """Load state dictionary from file."""
        if not os.path.exists(self.state_file):
            return {}
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except Exception:
            return {}

    def save(self, state: Dict[str, Any]) -> None:
        """Save state dictionary to file."""
        os.makedirs(os.path.dirname(os.path.abspath(self.state_file)), exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
            f.write("\n")

    def get_model(self, state: Dict[str, Any], model_id: str) -> Optional[Dict[str, Any]]:
        """Get model information from state."""
        return state.get(model_id)

    def update_model(
        self, state: Dict[str, Any], model_id: str, info: Dict[str, Any]
    ) -> None:
        """Update model record in state."""
        state[model_id] = info
