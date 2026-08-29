"""Bounded English lookup through the community Free Dictionary API."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from urllib.parse import quote

from brain.runtime.external.config import free_dictionary_enabled
from brain.runtime.external.gateway import EventSink, ExternalAPIGateway, ExternalGatewayError
from brain.runtime.external.models import ExternalAPIRequest

FREE_DICTIONARY_API_ID = "free_dictionary"
DICTIONARY_TOOL_NAME = "dictionary_lookup"
_WORD = re.compile(r"^[A-Za-z]+(?:['-][A-Za-z]+)*$")


@dataclass(frozen=True, slots=True)
class DictionaryLookupInput:
    word: str

    def normalized(self) -> str:
        raw = str(self.word or "")
        if "\r" in raw or "\n" in raw or "\x00" in raw:
            raise ValueError("invalid_word")
        word = unicodedata.normalize("NFC", raw).strip()
        if not 1 <= len(word) <= 64 or not _WORD.fullmatch(word):
            raise ValueError("invalid_word")
        return word.lower()


@dataclass(frozen=True, slots=True)
class DictionaryLookupResult:
    word: str
    phonetics: list[str]
    meanings: list[dict[str, object]]
    provider: str
    provenance: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _text(value: object, limit: int) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()[:limit]


def _normalize(data: object, provenance: dict[str, object]) -> DictionaryLookupResult:
    if not isinstance(data, list) or not data or not all(isinstance(x, dict) for x in data[:3]):
        raise ExternalGatewayError("provider_schema_error")
    word = _text(data[0].get("word"), 100)
    if word is None:
        raise ExternalGatewayError("provider_schema_error")
    phonetics: list[str] = []
    meanings: list[dict[str, object]] = []
    for entry in data[:3]:
        for item in (
            entry.get("phonetics", [])[:5] if isinstance(entry.get("phonetics"), list) else []
        ):
            if (
                isinstance(item, dict)
                and (text := _text(item.get("text"), 200))
                and text not in phonetics
            ):
                phonetics.append(text)  # Audio URLs are deliberately ignored.
        raw_meanings = entry.get("meanings", [])
        for meaning in raw_meanings[:5] if isinstance(raw_meanings, list) else []:
            if not isinstance(meaning, dict) or not (
                part := _text(meaning.get("partOfSpeech"), 100)
            ):
                continue
            definitions = []
            raw_defs = meaning.get("definitions", [])
            for definition in raw_defs[:3] if isinstance(raw_defs, list) else []:
                if not isinstance(definition, dict) or not (
                    body := _text(definition.get("definition"), 1000)
                ):
                    continue
                item: dict[str, object] = {"definition": body}
                if example := _text(definition.get("example"), 1000):
                    item["example"] = example
                definitions.append(item)
            if definitions:
                synonyms = (
                    [_text(x, 100) for x in meaning.get("synonyms", [])[:10]]
                    if isinstance(meaning.get("synonyms"), list)
                    else []
                )
                antonyms = (
                    [_text(x, 100) for x in meaning.get("antonyms", [])[:10]]
                    if isinstance(meaning.get("antonyms"), list)
                    else []
                )
                meanings.append(
                    {
                        "part_of_speech": part,
                        "definitions": definitions,
                        "synonyms": [x for x in synonyms if x],
                        "antonyms": [x for x in antonyms if x],
                    }
                )
    if not meanings:
        raise ExternalGatewayError("provider_schema_error")
    return DictionaryLookupResult(
        word, phonetics[:10], meanings[:15], "Free Dictionary API", provenance
    )


def lookup_dictionary(
    value: DictionaryLookupInput,
    *,
    gateway: ExternalAPIGateway,
    global_enabled: bool | None = None,
    provider_enabled: bool | None = None,
    event_sink: EventSink | None = None,
) -> DictionaryLookupResult:
    word = value.normalized()
    path = "/api/v2/entries/en/" + quote(word, safe="'-")
    try:
        response = gateway.execute(
            ExternalAPIRequest(api_id=FREE_DICTIONARY_API_ID, method="GET", path=path),
            global_enabled=global_enabled,
            provider_enabled=(
                free_dictionary_enabled() if provider_enabled is None else provider_enabled
            ),
            event_sink=event_sink,
        )
    except ExternalGatewayError as exc:
        if getattr(exc, "status_code", None) == 404:
            raise ExternalGatewayError("word_not_found") from None
        raise
    return _normalize(response.data, dict(response.provenance))
