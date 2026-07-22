from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any

from app.models import Store


@dataclass(frozen=True, slots=True)
class TriggeredSnapshot:
    snapshot_id: str


class PriceProvider(abc.ABC):
    """Interface for triggering price snapshots and retrieving their results.

    Concrete providers translate a batch of product URLs into an asynchronous
    provider job (``trigger``) whose results are delivered later. The tracking
    pipeline only depends on this surface, so alternative providers (for example
    the development :class:`~app.providers.fake.FakePriceProvider`) can be swapped
    in without touching the worker or service layer.
    """

    @abc.abstractmethod
    def dataset_id_for(self, store: Store) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger(self, store: Store, urls: list[str]) -> TriggeredSnapshot:
        raise NotImplementedError

    @abc.abstractmethod
    async def fetch_snapshot(self, snapshot_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abc.abstractmethod
    async def aclose(self) -> None:
        raise NotImplementedError
