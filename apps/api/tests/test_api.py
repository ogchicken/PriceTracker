from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"]


def test_metrics(client: TestClient) -> None:
    client.get("/healthz")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "pricetracker_http_requests_total" in response.text


def test_protected_api_requires_bearer_token(client: TestClient) -> None:
    response = client.get("/api/v1/watches")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_required_routes_are_in_openapi(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/watches" in paths
    assert paths["/api/v1/watches"]["post"]["responses"].get("202")
    assert "get" in paths["/api/v1/watches/{watch_id}"]
    assert "/api/v1/watches/{watch_id}/history" in paths
    assert "/api/v1/notifications" in paths
    assert "/api/v1/me/preferences" in paths
    assert "/api/v1/webhooks/bright-data" in paths
    assert "/api/v1/webhooks/clerk" in paths
