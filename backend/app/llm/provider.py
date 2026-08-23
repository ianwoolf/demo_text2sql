from __future__ import annotations
import json
from typing import Any
from openai import OpenAI


class LLMError(RuntimeError):
    pass


class LLMProvider:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=30) if api_key else None

    @property
    def configured(self) -> bool:
        return self.client is not None

    def generate_sql(self, question: str, metadata: dict, semantics: dict, history: list[dict]) -> str:
        if not self.client:
            raise LLMError("OPENAI_API_KEY is not configured.")
        prompt = (
            "You are a MySQL data analyst. Return one read-only SELECT query without Markdown. "
            "Use only the provided tables and columns and apply LIMIT 200 by default.\n"
            f"Metadata: {json.dumps(metadata, ensure_ascii=False)}\n"
            f"Business semantics: {json.dumps(semantics, ensure_ascii=False)}\n"
            f"Recent conversation: {json.dumps(history[-4:], ensure_ascii=False)}\nQuestion: {question}"
        )
        response = self.client.chat.completions.create(model=self.model, messages=[{"role": "user", "content": prompt}], temperature=0)
        content = response.choices[0].message.content or ""
        return self._strip_fence(content)

    def summarize(self, question: str, sql: str, rows: list[dict[str, Any]]) -> str:
        if not self.client:
            return f"Query completed with {len(rows)} result rows."
        prompt = f"Answer the question in two concise English sentences. Question: {question}\nSQL: {sql}\nResult: {json.dumps(rows[:30], ensure_ascii=False, default=str)}"
        response = self.client.chat.completions.create(model=self.model, messages=[{"role": "user", "content": prompt}], temperature=0.2)
        return response.choices[0].message.content or "Query completed."

    @staticmethod
    def _strip_fence(value: str) -> str:
        value = value.strip()
        if value.startswith("```sql"):
            value = value[len("```sql"):]
        elif value.startswith("```"):
            value = value[3:]
        if value.endswith("```"):
            value = value[:-3]
        return value.strip()
