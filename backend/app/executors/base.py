from typing import Protocol
from app.models import QueryResult


class QueryExecutorError(RuntimeError):
    code = "query_failed"


class TargetNotImplementedError(QueryExecutorError):
    code = "target_not_implemented"


class QueryExecutor(Protocol):
    def execute(self, sql: str, limit: int = 200) -> QueryResult: ...


def get_executor(target_type: str, config: dict | None = None) -> QueryExecutor:
    if target_type == "mock":
        from .mock import MockExecutor
        return MockExecutor(config or {})
    if target_type == "mysql":
        from .mysql import MySQLExecutor
        return MySQLExecutor(config or {})
    if target_type in {"spark_sql", "hive"}:
        from .unsupported import UnsupportedExecutor
        return UnsupportedExecutor(target_type)
    raise QueryExecutorError(f"Unknown query target: {target_type}")
