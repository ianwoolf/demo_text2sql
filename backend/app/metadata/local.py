import json
from pathlib import Path
from typing import Any
import yaml
from pydantic import ValidationError
from app.models import Catalog
from .base import MetadataError


class LocalFileMetadataProvider:
    def load_catalog(self, source_config: dict[str, Any]) -> Catalog:
        path = Path(str(source_config.get("path", ""))).expanduser().resolve()
        if not path.is_file():
            raise MetadataError(f"Metadata file not found: {path}")
        try:
            if path.suffix.lower() in {".yaml", ".yml"}:
                raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            elif path.suffix.lower() == ".json":
                raw = json.loads(path.read_text(encoding="utf-8"))
            else:
                raise MetadataError("The local provider supports YAML and JSON only.")
            return Catalog.model_validate(raw)
        except (OSError, ValueError, ValidationError, yaml.YAMLError) as exc:
            if isinstance(exc, MetadataError):
                raise
            raise MetadataError(f"Invalid metadata file: {exc}") from exc
