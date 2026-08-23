from typing import Literal
from pydantic import BaseModel, Field


class SourceDataset(BaseModel):
    dataset_id: str
    role: Literal["primary", "auxiliary"]
    alias: str
    selected_columns: list[str] = Field(default_factory=list)


class SparkSQLArtifact(BaseModel):
    content: str
    version: int = 1
    generation_source: Literal["mock", "anthropic", "manual"] = "mock"


class SinkDataset(BaseModel):
    catalog: str
    database: str
    table: str
    write_mode: Literal["append", "overwrite"]
    partition_columns: list[str] = Field(default_factory=list)
    description: str = ""

    @property
    def qualified_name(self) -> str:
        return f"{self.catalog}.{self.database}.{self.table}"


class SparkSQLValidation(BaseModel):
    status: Literal["passed", "failed"]
    referenced_tables: list[str] = Field(default_factory=list)
    output_columns: list[str] = Field(default_factory=list)
    joins: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class TransformationRequestData(BaseModel):
    name: str
    requirement_text: str
    source: list[SourceDataset]
    spark_sql: SparkSQLArtifact
    sink: SinkDataset


class JobReference(BaseModel):
    status: str
    message: str


class PreviousAttempt(BaseModel):
    sql: str
    validation_errors: list[str] = Field(default_factory=list)


class TransformationSQLGenerateRequest(BaseModel):
    mode: Literal["mock", "llm"]
    requirement_text: str = Field(min_length=1, max_length=4000)
    source: list[SourceDataset] = Field(min_length=1)
    sink: SinkDataset
    previous_attempt: PreviousAttempt | None = None


class SufficiencyResult(BaseModel):
    sufficient: bool
    missing_information: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class GenerationStage(BaseModel):
    name: str
    status: Literal["succeeded", "failed", "skipped"]
    message: str = ""


class ProviderMetadata(BaseModel):
    name: str
    model: str = ""
    latency_ms: int = 0
    stop_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


class TransformationSQLGenerateResponse(BaseModel):
    status: Literal["generated", "insufficient_context", "failed"]
    generation_source: Literal["mock", "anthropic"]
    content: str | None = None
    version: int = 1
    explanation: str = ""
    sufficiency: SufficiencyResult
    validation: SparkSQLValidation | None = None
    stages: list[GenerationStage] = Field(default_factory=list)
    provider: ProviderMetadata | None = None
    raw_response: str | None = None
