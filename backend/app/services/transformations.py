import json
from uuid import uuid4
from app.metadata import get_metadata_provider
from app.transformations.models import TransformationRequestData
from app.transformations.validator import validate_transformation
from .store import Store, now


class TransformationService:
    def __init__(self, store: Store):
        self.store = store

    def catalog(self):
        space = self.store.one("SELECT * FROM spaces WHERE id='sales-demo'")
        return get_metadata_provider(space["provider_type"]).load_catalog({"path": space["metadata_path"]})

    def create(self, data: TransformationRequestData) -> dict:
        validation = validate_transformation(data, self.catalog())
        if validation.status == "failed":
            raise ValueError("; ".join(validation.errors))
        snapshot = {**data.model_dump(), "validation": validation.model_dump(), "runner": {"type": "spark", "status": "not_configured"}}
        item = {"id": f"tr_{uuid4().hex[:10]}", "name": data.name, "status": "waiting_submit", "stage": "request_ready", "version": 1, "snapshot": snapshot, "created_by": "Alex Morgan", "created_at": now(), "updated_at": now()}
        self.store.execute("INSERT INTO transformation_requests VALUES (?,?,?,?,?,?,?,?,?)", (item["id"], item["name"], item["status"], item["stage"], item["version"], json.dumps(snapshot, ensure_ascii=False), item["created_by"], item["created_at"], item["updated_at"]))
        return item

    def get(self, request_id: str) -> dict:
        item = self.store.one("SELECT * FROM transformation_requests WHERE id=?", (request_id,))
        if not item:
            raise ValueError("Transformation request not found.")
        item["snapshot"] = json.loads(item["snapshot"])
        return item

    def list(self, status: str | None = None, query: str | None = None) -> list[dict]:
        items = self.store.rows("SELECT * FROM transformation_requests ORDER BY updated_at DESC")
        result = []
        for item in items:
            item["snapshot"] = json.loads(item["snapshot"])
            haystack = f"{item['name']} {json.dumps(item['snapshot'])}".lower()
            if status and item["status"] != status:
                continue
            if query and query.lower() not in haystack:
                continue
            result.append(item)
        return result

    def transition(self, request_id: str, action: str) -> dict:
        item = self.get(request_id)
        transitions = {
            ("waiting_submit", "submit"): ("waiting_approval", "approval_pending"),
            ("waiting_approval", "demo-approve"): ("waiting_approval", "runner_not_configured"),
            ("waiting_approval", "demo-succeed"): ("success", "execution_succeeded"),
            ("waiting_approval", "demo-fail"): ("failed", "execution_failed"),
        }
        next_state = transitions.get((item["status"], action))
        if not next_state:
            raise ValueError(f"Action {action} is not valid for status {item['status']}.")
        self.store.execute("UPDATE transformation_requests SET status=?,stage=?,updated_at=? WHERE id=?", (*next_state, now(), request_id))
        return self.get(request_id)

    def copy(self, request_id: str) -> dict:
        original = self.get(request_id)
        data = TransformationRequestData.model_validate(original["snapshot"])
        data.name = f"Copy of {data.name}"
        return self.create(data)

