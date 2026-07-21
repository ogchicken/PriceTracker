"""External provider and store adapter integrations."""

from app.providers.adapters import (
    AdapterError,
    NormalizedProduct,
    StoreAdapter,
    adapter_registry,
)

__all__ = ["AdapterError", "NormalizedProduct", "StoreAdapter", "adapter_registry"]
