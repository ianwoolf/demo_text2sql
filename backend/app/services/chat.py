from __future__ import annotations
import json
from pathlib import Path
from time import perf_counter
from app.executors import get_executor
from app.llm import LLMProvider
from app.metadata import get_metadata_provider
from app.models import SemanticContext
from app.sql_guard import guard_sql
from .store import Store


def _score(question: str, keywords: list[str]) -> int:
    lowered = question.lower()
    return sum(2 if keyword.lower() in lowered else 0 for keyword in keywords)


class ChatService:
    def __init__(self, store: Store, fixture_path: Path, llm: LLMProvider):
        self.store = store
        self.fixture_path = fixture_path
        self.llm = llm

    def ask(self, conversation_id: str, question: str) -> dict:
        conversation = self.store.one("SELECT * FROM conversations WHERE id=?", (conversation_id,))
        if not conversation:
            raise ValueError("Conversation not found.")
        space = self.store.one("SELECT * FROM spaces WHERE id=?", (conversation["space_id"],))
        semantics_raw = self.store.one("SELECT payload FROM semantics WHERE space_id=?", (space["id"],))
        semantics = SemanticContext.model_validate_json(semantics_raw["payload"] if semantics_raw else "{}")
        catalog = get_metadata_provider(space["provider_type"]).load_catalog({"path": space["metadata_path"]})
        self.store.add_message(conversation_id, "user", question)
        fixtures = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        fixture = max(fixtures.values(), key=lambda item: _score(question, item["keywords"]))
        mock_mode = space["target_type"] == "mock"
        trusted = next((item for item in semantics.examples if item.get("question") == question and item.get("trusted")), None)
        history = self.store.rows("SELECT role, content FROM messages WHERE conversation_id=? ORDER BY created_at", (conversation_id,))
        if trusted:
            sql = trusted["sql"]
            source = "trusted"
        elif mock_mode:
            sql = fixture["sql"]
            source = "mock"
        else:
            sql = self.llm.generate_sql(question, catalog.model_dump(), semantics.model_dump(), history)
            source = "ai"
        allowed = {table.name for table in catalog.tables if table.enabled}
        guarded_sql = guard_sql(sql, allowed)
        executor = get_executor(space["target_type"], {"fixture_path": str(self.fixture_path), "dsn_env": "MYSQL_DSN"})
        started_at = perf_counter()
        result = executor.execute(guarded_sql)
        duration_ms = round((perf_counter() - started_at) * 1000, 1)
        answer = fixture["answer"] if mock_mode else self.llm.summarize(question, guarded_sql, result.rows)
        chart = fixture.get("chart") if mock_mode else self._suggest_chart(result.columns, result.rows)
        referenced_tables = sorted({name for name in allowed if name.lower() in guarded_sql.lower()})
        payload = {
            "question": question, "answer": answer, "sql": guarded_sql, "columns": result.columns, "rows": result.rows,
            "chart": chart,
            "followups": fixture.get("followups", []),
            "provenance": {"mode": "mock" if mock_mode else "live", "source": source, "trusted": bool(trusted), "target": space["target_type"]},
            "referenced_tables": referenced_tables,
            "dataset": {"catalog": catalog.name, "schema": catalog.schema_name, "tables": referenced_tables, "provider": space["provider_type"]},
            "execution": {"status": "succeeded", "target": space["target_type"], "row_count": len(result.rows), "truncated": result.truncated, "duration_ms": duration_ms},
            "visualization": ({"status": "rendered", **chart} if chart else {"status": "table_only", "type": None, "x_key": None, "y_keys": []}),
            "steps": ["context_selected", "sql_generated", "sql_guarded", "query_executed", "answer_presented"],
        }
        message = self.store.add_message(conversation_id, "assistant", answer, payload)
        return {**message, **payload}

    @staticmethod
    def _suggest_chart(columns: list[str], rows: list[dict]) -> dict | None:
        if len(columns) >= 2 and rows and isinstance(rows[0].get(columns[1]), (int, float)):
            return {"type": "bar", "x_key": columns[0], "y_keys": [columns[1]]}
        return None
