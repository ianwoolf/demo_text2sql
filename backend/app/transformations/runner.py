from typing import Protocol
from .models import JobReference, TransformationRequestData


class SparkJobRunner(Protocol):
    def submit(self, request: TransformationRequestData) -> JobReference: ...


class UnavailableSparkJobRunner:
    def submit(self, request: TransformationRequestData) -> JobReference:
        return JobReference(status="runner_not_configured", message="SparkJobRunner is not configured for this POC.")

