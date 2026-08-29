from fastapi.testclient import TestClient

from app.services.pricing import calculate_order_total
from establishment_service.app.main import app


client = TestClient(app)


def test_calculate_order_total():
    result = calculate_order_total(
        items=[
            {
                "price": 500,
                "quantity": 2,
            }
        ],
        delivery_price=199,
        discount=100,
    )

    assert result["items_total"] == 1000
    assert result["total_price"] == 1099


def test_establishment_accepts_available_product():
    response = client.post(
        "/integration/orders/validate",
        json={
            "items": [
                {
                    "external_id": "pizza-margherita",
                    "quantity": 1,
                    "expected_price": "599.00",
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["accepted"] is True


def test_establishment_detects_changed_price():
    response = client.post(
        "/integration/orders/validate",
        json={
            "items": [
                {
                    "external_id": "pizza-margherita",
                    "quantity": 1,
                    "expected_price": "100.00",
                }
            ]
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["accepted"] is False
    assert body["conflicts"][0]["type"] == "price_changed"