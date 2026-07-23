import pytest

from app.models import Store
from app.providers.adapters import (
    AdapterError,
    NormalizedProduct,
    StoreAdapter,
    adapter_registry,
)


@pytest.mark.parametrize(
    ("url", "store", "external_id", "canonical"),
    [
        (
            "https://smile.amazon.co.uk/gp/product/B08N5WRWNW?tag=ignored",
            Store.AMAZON,
            "B08N5WRWNW",
            "https://www.amazon.co.uk/dp/B08N5WRWNW",
        ),
        (
            "https://www.amazon.com/dp/b08n5wrwnw/ref=something",
            Store.AMAZON,
            "B08N5WRWNW",
            "https://www.amazon.com/dp/B08N5WRWNW",
        ),
        (
            "https://www.ebay.de/itm/some-title/123456789012?hash=abc",
            Store.EBAY,
            "123456789012",
            "https://www.ebay.de/itm/123456789012",
        ),
    ],
)
def test_parse_and_canonicalize(
    url: str,
    store: Store,
    external_id: str,
    canonical: str,
) -> None:
    result = adapter_registry.parse(url)
    assert result.store is store
    assert result.external_id == external_id
    assert result.canonical_url == canonical


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/dp/B08N5WRWNW",
        "https://www.amazon.com/s?k=keyboard",
        "https://www.ebay.com/sch/i.html?_nkw=keyboard",
        "https://www.ebay.com/itm/123456789012?LH_Auction=1",
        "file:///etc/passwd",
        # `smile.` is an Amazon-only prefix; the browser check in
        # apps/web/src/lib/store-url.ts must agree, or the UI accepts a URL the
        # API then rejects with a 422.
        "https://smile.ebay.com/itm/123456789012",
        "https://evil-amazon.com/dp/B08N5WRWNW",
    ],
)
def test_rejects_unsupported_or_non_product_urls(url: str) -> None:
    with pytest.raises(AdapterError):
        adapter_registry.parse(url)


def test_accepts_http_and_canonicalizes_to_https() -> None:
    # The browser-side check mirrors this: it must not reject http outright.
    result = adapter_registry.parse("http://www.amazon.com/dp/B08N5WRWNW")

    assert result.canonical_url == "https://www.amazon.com/dp/B08N5WRWNW"


def test_adapter_subclass_must_declare_its_host_rules() -> None:
    # `supports_host` is concrete and reads these, so ABC cannot enforce them.
    # Without the __init_subclass__ guard an incomplete adapter imports fine and
    # raises AttributeError on the first URL a user submits.
    with pytest.raises(TypeError, match="host_prefixes"):

        class Incomplete(StoreAdapter):
            store = Store.AMAZON
            domains = frozenset({"example.com"})

            def parse(self, url: str) -> NormalizedProduct:  # pragma: no cover
                raise AdapterError("unused")
