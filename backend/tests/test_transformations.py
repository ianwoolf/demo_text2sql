from pathlib import Path
import os

import pytest
from fastapi.testclient import TestClient

os.environ["APP_DATABASE_PATH"] = "/tmp/datachat-transformations-test.db"

from app.main import app


VALID_REQUEST = {
    "name": "Monthly regional sales",
    "requirement_text": "Calculate completed monthly sales and customer count by region.",
    "source": [
        {"dataset_id": "demo_sales.orders", "role": "primary", "alias": "o", "selected_columns": ["customer_id", "order_date", "amount", "status"]},
        {"dataset_id": "demo_sales.customers", "role": "auxiliary", "alias": "c", "selected_columns": ["customer_id", "region"]},
    ],
    "spark_sql": {
        "content": "SELECT date_format(o.order_date, 'yyyy-MM') AS month, c.region, SUM(o.amount) AS sales FROM orders o JOIN customers c ON o.customer_id = c.customer_id WHERE o.status = 'completed' GROUP BY date_format(o.order_date, 'yyyy-MM'), c.region",
        "version": 1,
        "generation_source": "mock"
    },
    "sink": {"catalog": "analytics", "database": "sales", "table": "monthly_region_sales", "write_mode": "overwrite", "partition_columns": ["month"], "description": "Monthly regional sales aggregate"},
}


def test_validator_rejects_unselected_source_and_missing_partition():
    from app.transformations.models import TransformationRequestData
    from app.transformations.validator import validate_transformation
    from app.metadata.local import LocalFileMetadataProvider

    data = TransformationRequestData.model_validate({
        **VALID_REQUEST,
        "spark_sql": {**VALID_REQUEST["spark_sql"], "content": "SELECT p.category, SUM(o.amount) AS sales FROM orders o JOIN products p ON o.product_id = p.product_id GROUP BY p.category"},
        "sink": {**VALID_REQUEST["sink"], "partition_columns": ["month"]},
    })
    catalog = LocalFileMetadataProvider().load_catalog({"path": str(Path(__file__).resolve().parents[2] / "config/metadata/demo-sales.yaml")})
    result = validate_transformation(data, catalog)
    assert result.status == "failed"
    assert "products" in " ".join(result.errors)
    assert "month" in " ".join(result.errors)


def test_validator_accepts_selected_sources_referenced_through_cte():
    from app.transformations.models import TransformationRequestData
    from app.transformations.validator import validate_transformation
    from app.metadata.local import LocalFileMetadataProvider

    sql = """WITH completed_orders AS (
        SELECT customer_id, order_date, amount
        FROM orders
        WHERE status = 'completed'
    )
    SELECT date_format(o.order_date, 'yyyy-MM') AS month,
           c.region,
           SUM(o.amount) AS sales
    FROM completed_orders o
    JOIN customers c ON o.customer_id = c.customer_id
    GROUP BY date_format(o.order_date, 'yyyy-MM'), c.region"""
    data = TransformationRequestData.model_validate({
        **VALID_REQUEST,
        "spark_sql": {**VALID_REQUEST["spark_sql"], "content": sql},
    })
    catalog = LocalFileMetadataProvider().load_catalog({"path": str(Path(__file__).resolve().parents[2] / "config/metadata/demo-sales.yaml")})
    result = validate_transformation(data, catalog)
    assert result.status == "passed", result.errors
    assert result.output_columns == ["month", "region", "sales"]


def test_request_lifecycle_create_submit_approve_and_succeed():
    db_path = Path(os.environ["APP_DATABASE_PATH"])
    db_path.unlink(missing_ok=True)
    with TestClient(app) as client:
        created_response = client.post("/api/transformation-requests", json=VALID_REQUEST)
        assert created_response.status_code == 200, created_response.text
        created = created_response.json()
        assert created["status"] == "waiting_submit"
        assert created["snapshot"]["source"][0]["role"] == "primary"
        assert created["snapshot"]["sink"]["table"] == "monthly_region_sales"

        submitted = client.post(f"/api/transformation-requests/{created['id']}/submit").json()
        assert submitted["status"] == "waiting_approval"
        assert submitted["stage"] == "approval_pending"

        approved = client.post(f"/api/transformation-requests/{created['id']}/demo-approve").json()
        assert approved["status"] == "waiting_approval"
        assert approved["stage"] == "runner_not_configured"

        succeeded = client.post(f"/api/transformation-requests/{created['id']}/demo-succeed").json()
        assert succeeded["status"] == "success"
        assert succeeded["stage"] == "execution_succeeded"
