import json
import logging

from app.models import Catalog
from app.llm.anthropic_sparksql import AnthropicSparkSQLProvider
from app.transformations.models import GenerationStage, ProviderMetadata, SufficiencyResult, TransformationSQLGenerateRequest, TransformationSQLGenerateResponse
from app.transformations.preflight import build_generation_context
from app.transformations.validator import validate_spark_sql


logger = logging.getLogger("datachat.transformation_generation")


MOCK_SQL = """WITH completed_orders AS (
  SELECT customer_id, order_date, amount
  FROM orders
  WHERE status = 'completed'
)
SELECT date_format(o.order_date, 'yyyy-MM') AS month,
       c.region,
       SUM(o.amount) AS sales,
       COUNT(DISTINCT o.customer_id) AS customer_count
FROM completed_orders o
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY date_format(o.order_date, 'yyyy-MM'), c.region"""


class TransformationGenerationService:
    def __init__(self, provider: AnthropicSparkSQLProvider):
        self.provider = provider

    def generate(self, request: TransformationSQLGenerateRequest, catalog: Catalog) -> TransformationSQLGenerateResponse:
        stages = [GenerationStage(name="metadata_validation", status="succeeded")]
        context = build_generation_context(request, catalog)
        stages.append(GenerationStage(name="source_sufficiency", status="succeeded"))
        if request.mode == "mock":
            sql, explanation = MOCK_SQL, "Deterministic demo SparkSQL for the selected sales datasets."
            sufficiency = SufficiencyResult(sufficient=True)
            provider = ProviderMetadata(name="mock", model="deterministic-demo")
            raw = None
            stages.append(GenerationStage(name="anthropic_generation", status="skipped", message="Mock mode selected."))
            source = "mock"
        else:
            generated = self.provider.generate(context, request)
            output = generated.output
            stages.append(GenerationStage(name="anthropic_generation", status="succeeded"))
            if not output.sufficiency.sufficient or output.status == "insufficient_context":
                return TransformationSQLGenerateResponse(status="insufficient_context", generation_source="anthropic", explanation=output.explanation, sufficiency=output.sufficiency, stages=stages, provider=generated.provider, raw_response=generated.raw_response)
            sql, explanation, sufficiency = output.sql, output.explanation, output.sufficiency
            provider, raw, source = generated.provider, generated.raw_response, "anthropic"
        validation = validate_spark_sql(sql or "", request, catalog)
        logger.info("spark_sql_validation mode=%s sql=%s validation=%s", request.mode, sql or "", json.dumps(validation.model_dump(), ensure_ascii=False))
        stages.append(GenerationStage(name="sparksql_validation", status="succeeded" if validation.status == "passed" else "failed"))
        return TransformationSQLGenerateResponse(status="generated" if validation.status == "passed" else "failed", generation_source=source, content=sql, explanation=explanation, sufficiency=sufficiency, validation=validation, stages=stages, provider=provider, raw_response=raw)
