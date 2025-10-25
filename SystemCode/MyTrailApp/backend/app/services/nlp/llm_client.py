"""LLM adapter that talks to OpenAI using Structured Outputs."""
from __future__ import annotations

import json
import inspect
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from app.config import settings
from app.models.request import Center

from .preprocessor import PreprocessedQuery
from .prompts import DEVELOPER_PROMPT, SYSTEM_PROMPT


class RouteCriteriaLLMClient:
    """Thin wrapper around the OpenAI Responses API for structured parsing."""

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        schema_path: Optional[Path] = None,
        system_prompt: str = SYSTEM_PROMPT,
        developer_prompt: str = DEVELOPER_PROMPT,
        client: Any = None,
    ) -> None:
        self._model = model or settings.openai_model
        self._system_prompt = system_prompt
        self._developer_prompt = developer_prompt
        self._schema = self._load_schema(schema_path)
        self._client = client or self._build_client()

    @staticmethod
    def _load_schema(schema_path: Optional[Path]) -> Dict[str, Any]:
        path = schema_path or Path(__file__).with_name("routes_criteria_schemas.json")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:  # pragma: no cover - developer error
            raise RuntimeError(f"Schema file missing at {path}") from exc

    @staticmethod
    def _build_client() -> Any:
        api_key = settings.openai_api_key
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover - hard failure if lib missing
            raise RuntimeError("The openai package is required to use RouteCriteriaLLMClient") from exc

        return OpenAI(api_key=api_key, base_url=settings.openai_base_url or None)

    def parse(self, *, preprocessed: PreprocessedQuery, center: Center) -> Dict[str, Any]:
        if self._supports_structured_responses():
            response = self._client.responses.create(
                model=self._model,
                input=self._build_responses_messages(preprocessed, center),
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "RouteCriteria",
                        "schema": self._schema,
                        "strict": True,
                    },
                },
                temperature=0.2,
            )
        else:
            response = self._call_chat_completions(preprocessed, center)

        # Save the raw response to a local JSON file for debugging
        # self._save_response_for_debugging(response, preprocessed)

        return self._extract_json(response)

    def _build_responses_messages(
        self, preprocessed: PreprocessedQuery, center: Center
    ) -> Iterable[Dict[str, Any]]:
        locale_hint = preprocessed.language
        user_payload = {
            "language": locale_hint,
            "center": center.model_dump(),
            "normalized_query": preprocessed.normalized_text,
            "original_query": preprocessed.original_text,
            "contains_emojis": preprocessed.contains_emojis,
        }
        return [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": self._system_prompt,
                    }
                ],
            },
            {
                "role": "developer",
                "content": [
                    {
                        "type": "text",
                        "text": self._developer_prompt,
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "You will be given a JSON payload with the user's request metadata.\n"
                            "Infer a RouteCriteria object that satisfies the instructions.\n"
                            "Payload:\n" + json.dumps(user_payload, ensure_ascii=False)
                        ),
                    }
                ],
            },
        ]

    def _build_chat_messages(
        self, preprocessed: PreprocessedQuery, center: Center
    ) -> Iterable[Dict[str, Any]]:
        payload = json.dumps(
            {
                "language": preprocessed.language,
                "center": center.model_dump(),
                "normalized_query": preprocessed.normalized_text,
                "original_query": preprocessed.original_text,
                "contains_emojis": preprocessed.contains_emojis,
                "schema": self._schema,
            },
            ensure_ascii=False,
        )

        system_prompt = self._system_prompt
        if self._developer_prompt:
            system_prompt = (
                f"{self._system_prompt}\n\nDeveloper instructions:\n{self._developer_prompt}"
            )

        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "Convert the following payload into a RouteCriteria JSON object that"
                    " strictly matches the provided schema. Respond with JSON only.\n"
                    f"Payload:\n{payload}"
                ),
            },
        ]

    def _supports_structured_responses(self) -> bool:
        responses = getattr(self._client, "responses", None)
        if responses is None:
            return False
        create = getattr(responses, "create", None)
        if create is None:
            return False
        try:
            signature = inspect.signature(create)
        except (TypeError, ValueError):  # pragma: no cover - dynamic wrappers
            return True
        return "response_format" in signature.parameters

    def _call_chat_completions(
        self, preprocessed: PreprocessedQuery, center: Center
    ) -> Any:
        chat = getattr(self._client, "chat", None)
        if chat is None or not hasattr(chat, "completions"):
            raise RuntimeError(
                "OpenAI client does not support responses.json_schema or chat completions"
            )

        messages = list(self._build_chat_messages(preprocessed, center))
        return chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.2,
        )

    @staticmethod
    def _extract_json(response: Any) -> Dict[str, Any]:
        data = RouteCriteriaLLMClient._response_to_dict(response)

        # Responses API structure
        output = data.get("output", [])
        for item in output:
            content = item.get("content")
            if not content:
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if "json" in block:
                    return block["json"]
                text_value = RouteCriteriaLLMClient._extract_text_from_block(block)
                if text_value is not None:
                    maybe = RouteCriteriaLLMClient._safe_json_load(text_value)
                    if maybe is not None:
                        return maybe

        # Fallback for chat.completions style payloads
        choices = data.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            text_candidates: Iterable[str] = []

            content = message.get("content")
            if isinstance(content, str):
                text_candidates = [content]
            elif isinstance(content, Iterable):
                extracted: list[str] = []
                for segment in content:
                    if isinstance(segment, dict):
                        text_value = RouteCriteriaLLMClient._extract_text_from_block(segment)
                        if text_value:
                            extracted.append(text_value)
                    elif isinstance(segment, str):
                        extracted.append(segment)
                if extracted:
                    text_candidates = extracted

            for text in text_candidates:
                maybe = RouteCriteriaLLMClient._safe_json_load(text)
                if maybe is not None:
                    return maybe

        raise RuntimeError("Unable to extract JSON from LLM response")

    @staticmethod
    def _response_to_dict(response: Any) -> Dict[str, Any]:
        if isinstance(response, dict):
            return response
        for attr in ("model_dump", "dict", "to_dict"):
            if hasattr(response, attr):
                maybe = getattr(response, attr)()
                if isinstance(maybe, dict):
                    return maybe
        raise RuntimeError("Unexpected response type from OpenAI client")

    @staticmethod
    def _safe_json_load(text: str) -> Optional[Dict[str, Any]]:
        if not isinstance(text, str):
            return None
        candidate = text.strip()
        try:
            loaded = json.loads(candidate)
        except json.JSONDecodeError:
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            snippet = candidate[start : end + 1]
            try:
                loaded = json.loads(snippet)
            except json.JSONDecodeError:
                return None
        if isinstance(loaded, dict):
            return loaded
        return None

    @staticmethod
    def _extract_text_from_block(block: Dict[str, Any]) -> Optional[str]:
        if "text" in block:
            text_value = block["text"]
            if isinstance(text_value, dict):
                # Responses API: {"type": "output_text", "text": {"value": "..."}}
                inner = text_value.get("value")
                if isinstance(inner, str):
                    return inner
            elif isinstance(text_value, str):
                return text_value
        if "value" in block and isinstance(block["value"], str):
            return block["value"]
        return None

    # For debugging purposes, manually check responses
    def _save_response_for_debugging(self, response: Any, preprocessed: PreprocessedQuery) -> None:
        """Save the raw response to a local JSON file for debugging purposes."""
        try:
            import json
            import os
            from datetime import datetime
            
            # Convert response to dict if possible
            response_data = RouteCriteriaLLMClient._response_to_dict(response)
            
            # Create debug directory if it doesn't exist
            debug_dir = "debug_responses"
            os.makedirs(debug_dir, exist_ok=True)
            
            # Create filename with timestamp and query snippet
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            query_snippet = preprocessed.normalized_text[:30].replace(" ", "_")
            filename = f"{debug_dir}/llm_response_{timestamp}_{query_snippet}.json"
            
            # Save the response
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(response_data, f, indent=2, ensure_ascii=False)
                
            print(f"LLM response saved to: {filename}")
        except Exception:
            pass  # Ignore errors in debugging code