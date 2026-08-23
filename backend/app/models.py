from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class Column(BaseModel):
    name: str
    data_type: str
    description: str = ""
    nullable: bool = True
    primary_key: bool = False
    sample_values: list[Any] = Field(default_factory=list)


class Table(BaseModel):
    name: str
    description: str = ""
    owner: str = "Unassigned"
    data_tier: Literal["T1", "T2", "T3"] = "T1"
    enabled: bool = True
    columns: list[Column]


class Relation(BaseModel):
    left: str
    right: str
    description: str = ""


class Catalog(BaseModel):
    name: str
    schema_name: str = "public"
    tables: list[Table]
    relations: list[Relation] = Field(default_factory=list)


class SemanticContext(BaseModel):
    instructions: list[str] = Field(default_factory=list)
    terms: list[dict[str, str]] = Field(default_factory=list)
    metrics: list[dict[str, str]] = Field(default_factory=list)
    joins: list[dict[str, str]] = Field(default_factory=list)
    examples: list[dict[str, Any]] = Field(default_factory=list)


class QueryResult(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    truncated: bool = False


class AskRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class FeedbackRequest(BaseModel):
    rating: Literal["positive", "negative", "review"]
    comment: str = ""


class SpaceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    target_type: Literal["mock", "mysql", "spark_sql", "hive"] | None = None
    provider_type: Literal["local", "collibra"] | None = None
    instructions: list[str] | None = None
