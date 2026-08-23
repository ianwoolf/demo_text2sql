import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.metadata.local import LocalFileMetadataProvider
from app.transformations.models import TransformationSQLGenerateRequest


CATALOG_PATH = Path(__file__).resolve().parents[2] / "config/metadata/demo-sales.yaml"


def generation_payload(mode="mock"):
    return {
        "mode": mode,
        "requirement_text": "Calculate completed monthly sales by region.",
        "source": [
            {"dataset_id": "demo_sales.orders", "role": "primary", "alias": "o", "selected_columns": ["customer_id", "order_date", "amount", "status"]},
            {"dataset_id": "demo_sales.customers", "role": "auxiliary", "alias": "c", "selected_columns": ["customer_id", "region"]},
        ],
        "sink": {"catalog": "analytics", "database": "sales", "table": "monthly_region_sales", "write_mode": "overwrite", "partition_columns": ["month"], "description": "Monthly sales"},
    }


def test_generation_request_requires_complete_context():
    with pytest.raises(ValidationError):
        TransformationSQLGenerateRequest.model_validate({"mode": "llm"})


def test_capabilities_never_exposes_anthropic_key():
    with TestClient(app) as client:
        body = client.get("/api/capabilities").json()
    assert set(body["anthropic"]) == {"configured", "model"}
    assert "api_key" not in json.dumps(body).lower()


def test_preflight_rejects_unknown_selected_column():
    from app.transformations.preflight import MetadataPreflightError, build_generation_context

    request = TransformationSQLGenerateRequest.model_validate(generation_payload())
    request.source[0].selected_columns.append("missing_column")
    catalog = LocalFileMetadataProvider().load_catalog({"path": str(CATALOG_PATH)})
    with pytest.raises(MetadataPreflightError) as error:
        build_generation_context(request, catalog)
    assert "unknown_column" in {item["code"] for item in error.value.details}


def test_mock_generation_returns_typed_validated_result():
    with TestClient(app) as client:
        response = client.post("/api/transformation-sql/generate", json=generation_payload())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["generation_source"] == "mock"
    assert body["validation"]["status"] == "passed"
    assert body["sufficiency"]["sufficient"] is True
    assert body["stages"][-1]["name"] == "sparksql_validation"
