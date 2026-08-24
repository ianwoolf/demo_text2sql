from __future__ import annotations
import json
import logging
from time import perf_counter
from typing import Any
from uuid import uuid4
from anthropic import Anthropic
from pydantic import BaseModel, ValidationError, model_validator
from app.transformations.models import ProviderMetadata, SufficiencyResult, TransformationSQLGenerateRequest
from app.transformations.preflight import GenerationContext


logger = logging.getLogger("datachat.anthropic_sparksql")


SYSTEM_PROMPT = """You are a senior data engineer generating Apache Spark SQL.
Determine whether the selected datasets and supplied metadata are sufficient for the user's transformation requirement. If sufficient, generate exactly one read-only Spark SQL query. If insufficient, do not invent tables, columns, joins, filters, business definitions, or assumptions.
Rules:
- Use only supplied datasets and columns and prefer supplied join relationships.
- Report any inferred join as an assumption.
- Generate SELECT or WITH ... SELECT only; never generate DDL, DML, cache, command, or filesystem operations.
- Use Apache Spark SQL syntax and qualify ambiguous columns.
- Give every output expression a stable, unique name and preserve requested sink partition columns.
- When status is generated, explanation is required and must concisely explain the selected sources, joins, filters, aggregations, and how the query satisfies the user's requirement.
- When the metadata is insufficient, explanation must state what information is missing and sql must be null.
- Return JSON only with status, sufficiency, sql, referenced_tables, output_columns, and explanation. No Markdown fences."""


class ProviderError(RuntimeError):
    code = "provider_error"


class InvalidProviderResponse(ProviderError):
    code = "invalid_provider_response"


class ModelOutput(BaseModel):
    status: str
    sufficiency: SufficiencyResult
    sql: str | None = None
    referenced_tables: list[str] = []
    output_columns: list[str] = []
    explanation: str = ""

    @model_validator(mode="after")
    def require_generated_explanation(self):
        if self.status == "generated" and not self.explanation.strip():
            raise ValueError("explanation is required when status is generated")
        return self


class ProviderGenerationResult(BaseModel):
    output: ModelOutput
    raw_response: str
    provider: ProviderMetadata


class AnthropicSparkSQLProvider:
    def __init__(self, api_key: str = "", base_url: str = "https://api.anthropic.com", model: str = "", timeout: float = 60, client: Any = None, log_payloads: bool = True):
        self.model = model
        self.client = client or (Anthropic(api_key=api_key, base_url=base_url, timeout=timeout) if api_key else None)
        self.log_payloads = log_payloads

    @property
    def configured(self) -> bool:
        return self.client is not None and bool(self.model)

    def generate(self, context: GenerationContext, request: TransformationSQLGenerateRequest) -> ProviderGenerationResult:
        if not self.configured:
            error = ProviderError("Anthropic is not configured. Set ANTHROPIC_API_KEY and ANTHROPIC_MODEL.")
            error.code = "anthropic_not_configured"
            raise error
        payload = {
            "requirement": request.requirement_text,
            "primary_source": context.primary_source,
            "selected_sources": [table.model_dump() for table in context.datasets],
            "known_relations": context.relations,
            "sink": request.sink.model_dump() | {"qualified_name": request.sink.qualified_name},
            "previous_attempt": request.previous_attempt.model_dump() if request.previous_attempt else None,
        }
        request_id = f"llm_{uuid4().hex[:10]}"
        if self.log_payloads:
            logger.info("spark_sql_llm_request request_id=%s model=%s payload=%s", request_id, self.model, json.dumps(payload, ensure_ascii=False, default=str))
        started = perf_counter()
        try:
            response = self.client.messages.create(model=self.model, max_tokens=4096, temperature=0, system=SYSTEM_PROMPT, messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
            raw = "".join(block.text for block in response.content if getattr(block, "type", "") == "text").strip()
            if self.log_payloads:
                logger.info("spark_sql_llm_response request_id=%s model=%s raw_response=%s", request_id, getattr(response, "model", self.model), raw)
            candidate = raw
            if candidate.startswith("```") and candidate.endswith("```"):
                first_line, separator, fenced_body = candidate.partition("\n")
                if not separator or first_line.lower() not in {"```", "```json"}:
                    raise InvalidProviderResponse("Anthropic returned unsupported Markdown instead of JSON.")
                candidate = fenced_body[:-3].strip()
            parsed = json.loads(candidate)
            if isinstance(parsed.get("sufficiency"), bool):
                parsed["sufficiency"] = {
                    "sufficient": parsed["sufficiency"],
                    "missing_information": parsed.get("missing_information", []),
                    "assumptions": parsed.get("assumptions", []),
                }
            output = ModelOutput.model_validate(parsed)
        except InvalidProviderResponse:
            raise
        except (json.JSONDecodeError, ValidationError) as exc:
            raise InvalidProviderResponse(f"Anthropic returned invalid structured JSON: {exc}") from exc
        except Exception as exc:
            raise ProviderError(f"Anthropic request failed: {type(exc).__name__}") from exc
        usage = getattr(response, "usage", None)
        metadata = ProviderMetadata(name="anthropic", model=getattr(response, "model", self.model), latency_ms=round((perf_counter()-started)*1000), stop_reason=getattr(response, "stop_reason", None), input_tokens=getattr(usage, "input_tokens", None), output_tokens=getattr(usage, "output_tokens", None))
        logger.info("spark_sql_llm_usage request_id=%s model=%s latency_ms=%s stop_reason=%s input_tokens=%s output_tokens=%s", request_id, metadata.model, metadata.latency_ms, metadata.stop_reason, metadata.input_tokens, metadata.output_tokens)
        return ProviderGenerationResult(output=output, raw_response=raw, provider=metadata)
