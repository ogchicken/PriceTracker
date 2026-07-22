from __future__ import annotations

from app.config import Settings
from app.providers.base import PriceProvider
from app.providers.brightdata import BrightDataClient
from app.providers.fake import FakePriceProvider


def build_price_provider(settings: Settings) -> PriceProvider:
    """Select the price provider for the current settings.

    Mirrors ``app.providers.email.build_email_provider``: the ``fake`` provider is
    only available in development and test and is refused everywhere else, as a
    second line of defence behind the ``guard_unsafe_modes`` config validator.
    """
    if settings.price_provider == "fake":
        if settings.environment in {"staging", "production"}:
            raise RuntimeError(
                "the fake price provider is not allowed outside development and test"
            )
        return FakePriceProvider(settings)
    return BrightDataClient(settings)
