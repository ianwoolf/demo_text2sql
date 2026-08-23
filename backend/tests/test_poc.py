from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.metadata.local import LocalFileMetadataProvider
from app.sql_guard import UnsafeSQLError, guard_sql


def test_local_metadata_loads_demo_catalog():
    path = Path(__file__).resolve().parents[2] / "config/metadata/demo-sales.yaml"
    catalog = LocalFileMetadataProvider().load_catalog({"path": str(path)})
    assert {table.name for table in catalog.tables} == {"customers", "orders", "products", "order_items"}
    assert {table.name: table.owner for table in catalog.tables} == {
        "customers": "CRM Team",
        "orders": "Sales Operations",
        "products": "Merchandising",
        "order_items": "Commerce Platform",
    }
    assert {table.name: table.data_tier for table in catalog.tables} == {
        "customers": "T2",
        "orders": "T1",
        "products": "T2",
        "order_items": "T1",
    }


def test_sql_guard_rejects_write_and_bounds_select():
    with pytest.raises(UnsafeSQLError):
        guard_sql("DELETE FROM orders", {"orders"})
    assert guard_sql("SELECT order_id FROM orders", {"orders"}).endswith("LIMIT 200")


def test_mock_chat_feedback_journey():
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok", "mode": "demo"}
        spaces = client.get("/api/spaces").json()
        conversation = client.post("/api/conversations", json={"space_id": spaces[0]["id"]}).json()
        answer = client.post(f"/api/conversations/{conversation['id']}/messages", json={"content": "Show monthly sales this year"})
        assert answer.status_code == 200, answer.text
        body = answer.json()
        assert body["rows"] and body["provenance"]["mode"] == "mock"
        assert body["dataset"] == {
            "catalog": "Sales Analytics Demo",
            "schema": "demo_sales",
            "tables": ["orders"],
            "provider": "local",
        }
        assert body["execution"]["status"] == "succeeded"
        assert body["execution"]["target"] == "mock"
        assert body["execution"]["row_count"] == 6
        assert body["visualization"] == {
            "status": "rendered",
            "type": "line",
            "x_key": "month",
            "y_keys": ["sales"],
        }
        response = client.post(f"/api/messages/{body['id']}/feedback", json={"rating": "negative", "comment": "Demo review"})
        assert response.status_code == 200
        assert client.get("/api/reviews?status=pending").json()
