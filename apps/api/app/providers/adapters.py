from __future__ import annotations

import abc
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

from app.models import Store


class AdapterError(ValueError):
    """Raised when a submitted URL is not a supported product page."""


@dataclass(frozen=True, slots=True)
class NormalizedProduct:
    store: Store
    external_id: str
    canonical_url: str
    region: str


class StoreAdapter(abc.ABC):
    """Base for store adapters.

    ``domains`` and ``host_prefixes`` are the single source of truth for which
    URLs PriceTracker accepts. They are exported to ``docs/marketplaces.json`` by
    ``scripts/export_marketplaces.py`` and generated into the frontend, so the
    browser-side check cannot drift from this one. Never restate them elsewhere.
    """

    store: Store
    domains: frozenset[str]
    host_prefixes: tuple[str, ...]

    def __init_subclass__(cls, **kwargs: object) -> None:
        # `supports_host` reads these, but they are annotations rather than
        # abstract methods, so ABC cannot enforce them. Without this an adapter
        # that omits one imports and instantiates fine, then raises
        # AttributeError on the first URL a user submits.
        super().__init_subclass__(**kwargs)
        missing = [name for name in ("store", "domains", "host_prefixes") if not hasattr(cls, name)]
        if missing:
            raise TypeError(f"{cls.__name__} must define {', '.join(missing)}")

    def base_domain(self, host: str) -> str:
        for prefix in self.host_prefixes:
            if host.startswith(prefix):
                return host[len(prefix) :]
        return host

    def supports_host(self, host: str) -> bool:
        return self.base_domain(host) in self.domains

    @abc.abstractmethod
    def parse(self, url: str) -> NormalizedProduct:
        """Parse locally. Implementations must never request the submitted URL."""
        raise NotImplementedError


def _safe_url(url: str) -> tuple[str, str, str, str]:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise AdapterError("invalid URL") from exc
    if parsed.scheme.lower() not in {"http", "https"}:
        raise AdapterError("URL must use http or https")
    if not parsed.hostname or parsed.username or parsed.password or port is not None:
        raise AdapterError("URL host is invalid")
    return (
        parsed.hostname.lower().rstrip("."),
        parsed.path,
        parsed.query,
        parsed.fragment,
    )


class AmazonAdapter(StoreAdapter):
    store = Store.AMAZON
    domains = frozenset(
        {
            "amazon.com",
            "amazon.ca",
            "amazon.com.mx",
            "amazon.com.br",
            "amazon.co.uk",
            "amazon.de",
            "amazon.fr",
            "amazon.it",
            "amazon.es",
            "amazon.nl",
            "amazon.se",
            "amazon.pl",
            "amazon.com.au",
            "amazon.co.jp",
            "amazon.in",
            "amazon.sg",
            "amazon.ae",
            "amazon.sa",
        }
    )
    host_prefixes = ("www.", "smile.", "m.")
    _product_path = re.compile(
        r"(?:^|/)(?:dp|gp/product|gp/aw/d)/([A-Z0-9]{10})(?:[/?]|$)",
        re.IGNORECASE,
    )

    def parse(self, url: str) -> NormalizedProduct:
        host, path, _, _ = _safe_url(url)
        domain = self.base_domain(host)
        if domain not in self.domains:
            raise AdapterError("unsupported Amazon region")
        match = self._product_path.search(path)
        if not match:
            raise AdapterError("Amazon URL is not a supported product page")
        asin = match.group(1).upper()
        return NormalizedProduct(
            store=self.store,
            external_id=asin,
            canonical_url=f"https://www.{domain}/dp/{asin}",
            region=domain.removeprefix("amazon."),
        )


class EbayAdapter(StoreAdapter):
    store = Store.EBAY
    domains = frozenset(
        {
            "ebay.com",
            "ebay.ca",
            "ebay.co.uk",
            "ebay.de",
            "ebay.fr",
            "ebay.it",
            "ebay.es",
            "ebay.com.au",
            "ebay.at",
            "ebay.be",
            "ebay.ch",
            "ebay.ie",
            "ebay.nl",
            "ebay.pl",
            "ebay.com.sg",
        }
    )
    host_prefixes = ("www.", "m.")
    _item_path = re.compile(r"(?:^|/)itm/(?:[^/?]+/)?(\d{9,15})(?:[/?]|$)", re.IGNORECASE)
    _auction_terms = {"auction", "bid", "bidding"}

    def parse(self, url: str) -> NormalizedProduct:
        host, path, query, fragment = _safe_url(url)
        domain = self.base_domain(host)
        if domain not in self.domains:
            raise AdapterError("unsupported eBay region")
        lowered_parts = f"{query}&{fragment}".lower()
        params = parse_qs(query, keep_blank_values=True)
        explicit_auction = any(
            "auction" in key.lower()
            or key.lower() in self._auction_terms
            or any(value.lower() in self._auction_terms for value in values)
            for key, values in params.items()
        )
        if explicit_auction or any(
            marker in lowered_parts for marker in ("lh_auction=1", "listingtype=auction")
        ):
            raise AdapterError("eBay auction URLs are not supported")
        match = self._item_path.search(path)
        if not match:
            raise AdapterError("eBay URL is not a supported fixed-price item page")
        item_id = match.group(1)
        return NormalizedProduct(
            store=self.store,
            external_id=item_id,
            canonical_url=f"https://www.{domain}/itm/{item_id}",
            region=domain.removeprefix("ebay."),
        )


class AdapterRegistry:
    def __init__(self, adapters: list[StoreAdapter]) -> None:
        self._adapters = adapters

    @property
    def adapters(self) -> tuple[StoreAdapter, ...]:
        return tuple(self._adapters)

    def parse(self, url: str) -> NormalizedProduct:
        host, _, _, _ = _safe_url(url)
        for adapter in self._adapters:
            if adapter.supports_host(host):
                return adapter.parse(url)
        raise AdapterError("unsupported store host")


adapter_registry = AdapterRegistry([AmazonAdapter(), EbayAdapter()])
