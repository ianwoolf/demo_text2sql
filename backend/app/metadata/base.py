from typing import Any, Protocol
from app.models import Catalog


class MetadataError(ValueError):
    pass


class MetadataProvider(Protocol):
    def load_catalog(self, source_config: dict[str, Any]) -> Catalog: ...


def get_metadata_provider(provider_type: str) -> MetadataProvider:
    if provider_type == "local":
        from .local import LocalFileMetadataProvider
        return LocalFileMetadataProvider()
    if provider_type == "collibra":
        raise MetadataError("The Collibra Provider is reserved but not connected in this POC.")
    raise MetadataError(f"Unknown metadata provider: {provider_type}")
