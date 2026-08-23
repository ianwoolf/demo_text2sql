import json
from pathlib import Path
from app.models import QueryResult


class MockExecutor:
    def __init__(self, config: dict):
        self.fixture_path = Path(config.get("fixture_path", ""))

    def execute(self, sql: str, limit: int = 200) -> QueryResult:
        fixtures = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        match = next((item for item in fixtures.values() if item["sql"].split(" LIMIT")[0].lower() in sql.lower()), None)
        if match is None:
            match = next(iter(fixtures.values()))
        rows = match["rows"][:limit]
        return QueryResult(columns=match["columns"], rows=rows, truncated=len(match["rows"]) > limit)

