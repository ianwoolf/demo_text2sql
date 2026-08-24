import json
from types import SimpleNamespace

import pytest

from app.llm.anthropic_sparksql import AnthropicSparkSQLProvider, InvalidProviderResponse
from app.metadata.local import LocalFileMetadataProvider
from app.transformations.models import TransformationSQLGenerateRequest
from app.transformations.preflight import build_generation_context
from test_transformation_generation import CATALOG_PATH, generation_payload


class FakeMessages:
    def __init__(self, text):
        self.text = text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.text)], model="claude-test", stop_reason="end_turn", usage=SimpleNamespace(input_tokens=100, output_tokens=40))


def provider_for(text):
    messages = FakeMessages(text)
    client = SimpleNamespace(messages=messages)
    return AnthropicSparkSQLProvider(model="claude-test", client=client), messages


def test_prompt_contains_selected_metadata_query_and_sink_only():
    output = {"status": "generated", "sufficiency": {"sufficient": True, "missing_information": [], "assumptions": []}, "sql": "SELECT 1 AS month", "referenced_tables": [], "output_columns": ["month"], "explanation": "test"}
    provider, messages = provider_for(json.dumps(output))
    request = TransformationSQLGenerateRequest.model_validate(generation_payload("llm"))
    catalog = LocalFileMetadataProvider().load_catalog({"path": str(CATALOG_PATH)})
    provider.generate(build_generation_context(request, catalog), request)
    sent = messages.calls[0]["messages"][0]["content"]
    assert request.requirement_text in sent
    assert request.sink.qualified_name in sent
    assert '"orders"' in sent and '"products"' not in sent
    assert len(messages.calls) == 1


def test_provider_accepts_json_fence_without_retry():
    output = {"status": "generated", "sufficiency": {"sufficient": True, "missing_information": [], "assumptions": []}, "sql": "SELECT 1 AS month", "referenced_tables": [], "output_columns": ["month"], "explanation": "test"}
    raw = f"```json\n{json.dumps(output)}\n```"
    provider, messages = provider_for(raw)
    request = TransformationSQLGenerateRequest.model_validate(generation_payload("llm"))
    catalog = LocalFileMetadataProvider().load_catalog({"path": str(CATALOG_PATH)})
    result = provider.generate(build_generation_context(request, catalog), request)
    assert result.output.sql == "SELECT 1 AS month"
    assert result.raw_response == raw
    assert len(messages.calls) == 1


def test_provider_logs_request_and_response_without_api_key(caplog):
    output = {"status": "generated", "sufficiency": {"sufficient": True, "missing_information": [], "assumptions": []}, "sql": "SELECT 1 AS month", "referenced_tables": [], "output_columns": ["month"], "explanation": "logged result"}
    messages = FakeMessages(json.dumps(output))
    provider = AnthropicSparkSQLProvider(api_key="super-secret-test-key", model="claude-test", client=SimpleNamespace(messages=messages), log_payloads=True)
    request = TransformationSQLGenerateRequest.model_validate(generation_payload("llm"))
    catalog = LocalFileMetadataProvider().load_catalog({"path": str(CATALOG_PATH)})
    with caplog.at_level("INFO", logger="datachat.anthropic_sparksql"):
        provider.generate(build_generation_context(request, catalog), request)
    logs = caplog.text
    assert "spark_sql_llm_request" in logs
    assert request.requirement_text in logs
    assert "spark_sql_llm_response" in logs
    assert "logged result" in logs
    assert "super-secret-test-key" not in logs


def test_provider_normalizes_boolean_sufficiency():
    output = {"status": "generated", "sufficiency": True, "sql": "SELECT 1 AS month", "referenced_tables": [], "output_columns": ["month"], "explanation": "compact response"}
    provider, _ = provider_for(json.dumps(output))
    request = TransformationSQLGenerateRequest.model_validate(generation_payload("llm"))
    catalog = LocalFileMetadataProvider().load_catalog({"path": str(CATALOG_PATH)})
    result = provider.generate(build_generation_context(request, catalog), request)
    assert result.output.sufficiency.sufficient is True
    assert result.output.sufficiency.missing_information == []


def test_provider_rejects_successful_generation_without_explanation():
    output = {
        "status": "generated",
        "sufficiency": {"sufficient": True, "missing_information": [], "assumptions": []},
        "sql": "SELECT 1 AS month",
        "referenced_tables": [],
        "output_columns": ["month"],
        "explanation": "   ",
    }
    provider, _ = provider_for(json.dumps(output))
    request = TransformationSQLGenerateRequest.model_validate(generation_payload("llm"))
    catalog = LocalFileMetadataProvider().load_catalog({"path": str(CATALOG_PATH)})

    with pytest.raises(InvalidProviderResponse, match="explanation"):
        provider.generate(build_generation_context(request, catalog), request)
