from decimal import Decimal

import httpx
import pytest

from app.config import Settings
from app.models import AvailabilityStatus, Store
from app.providers.brightdata import BrightDataClient, money_to_minor, normalize_result


@pytest.mark.parametrize(
    ("value", "currency", "expected"),
    [
        ("$1,234.56", "USD", 123456),
        ("12,34 €", "EUR", 1234),
        (Decimal("10.005"), "USD", 1001),
        ("1200", "JPY", 1200),
        ("1.234", "KWD", 1234),
    ],
)
def test_money_to_minor(value: object, currency: str, expected: int) -> None:
    assert money_to_minor(value, currency) == expected


@pytest.mark.parametrize("value", [None, "", "-1.00", float("inf"), True])
def test_money_rejects_invalid_values(value: object) -> None:
    with pytest.raises(ValueError):
        money_to_minor(value)


def test_normalizes_amazon_result() -> None:
    result = normalize_result(
        Store.AMAZON,
        {
            "asin": "b08n5wrwnw",
            "final_price": "$19.99",
            "currency": "usd",
            "shipping_cost": "Free shipping",
            "availability": "In Stock",
            "title": "Example",
            "timestamp": "2026-07-21T00:00:00Z",
        },
    )
    assert result.external_id == "B08N5WRWNW"
    assert result.price_minor == 1999
    assert result.item_price_minor == 1999
    assert result.shipping_price_minor == 0
    assert result.currency == "USD"
    assert result.availability is AvailabilityStatus.IN_STOCK
    assert result.title == "Example"


def test_identifier_can_be_recovered_from_provider_url() -> None:
    result = normalize_result(
        Store.EBAY,
        {
            "url": "https://www.ebay.com/itm/widget/123456789012",
            "price": "40.00",
            "currency_code": "USD",
        },
    )
    assert result.external_id == "123456789012"


def test_effective_price_includes_mandatory_shipping() -> None:
    result = normalize_result(
        Store.EBAY,
        {
            "item_id": "123456789012",
            "price": "40.00",
            "shipping_cost": "5.99",
            "currency": "USD",
            "listing_type": "FixedPrice",
        },
    )
    assert result.item_price_minor == 4000
    assert result.shipping_price_minor == 599
    assert result.price_minor == 4599


def test_provider_result_rejects_ebay_auction() -> None:
    with pytest.raises(ValueError, match="auction"):
        normalize_result(
            Store.EBAY,
            {
                "item_id": "123456789012",
                "price": "10.00",
                "currency": "USD",
                "listing_type": "Auction",
            },
        )


@pytest.mark.asyncio
async def test_fake_provider_never_makes_http_request() -> None:
    def reject_request(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"unexpected paid provider request: {request.url}")

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(reject_request))
    client = BrightDataClient(
        Settings(environment="test", fake_provider_enabled=True),
        http_client=http_client,
    )
    try:
        snapshot = await client.trigger(Store.AMAZON, ["https://www.amazon.com/dp/B08N5WRWNW"])
        assert snapshot.fake is True
    finally:
        await http_client.aclose()


@pytest.mark.asyncio
async def test_live_trigger_configures_authenticated_result_webhook() -> None:
    def handle_request(request: httpx.Request) -> httpx.Response:
        assert request.url.params["endpoint"] == "https://api.example.test/webhooks/bright-data"
        assert request.url.params["uncompressed_webhook"] == "true"
        assert request.url.params["webhook_header_Authorization"] == "Bearer webhook-secret"
        return httpx.Response(200, json={"snapshot_id": "snapshot-123"})

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handle_request))
    client = BrightDataClient(
        Settings(
            environment="development",
            fake_provider_enabled=False,
            bright_data_api_token="token",
            bright_data_amazon_dataset_id="amazon-dataset",
            bright_data_ebay_dataset_id="ebay-dataset",
            bright_data_webhook_url="https://api.example.test/webhooks/bright-data",
            bright_data_webhook_secret="webhook-secret",
        ),
        http_client=http_client,
    )
    try:
        snapshot = await client.trigger(
            Store.AMAZON,
            ["https://www.amazon.com/dp/B08N5WRWNW"],
        )
        assert snapshot.snapshot_id == "snapshot-123"
    finally:
        await http_client.aclose()
