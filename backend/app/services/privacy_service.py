from dataclasses import dataclass

try:
    from presidio_analyzer import Pattern, PatternRecognizer
    from presidio_analyzer import RecognizerResult
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig
except Exception:  # pragma: no cover
    Pattern = None
    PatternRecognizer = None
    RecognizerResult = None
    AnonymizerEngine = None
    OperatorConfig = None


@dataclass
class PIIAnonymizationResult:
    original_text: str
    anonymized_text: str
    entity_types: list[str]
    available: bool


class PrivacyService:
    def __init__(self) -> None:
        self.available = all(
            dependency is not None
            for dependency in (Pattern, PatternRecognizer, RecognizerResult, AnonymizerEngine, OperatorConfig)
        )
        self.anonymizer = AnonymizerEngine() if self.available else None
        self.recognizers = self._build_recognizers() if self.available else []

    def _build_recognizers(self) -> list[PatternRecognizer]:
        return [
            PatternRecognizer(
                supported_entity="EMAIL_ADDRESS",
                patterns=[Pattern("email", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", 0.9)],
            ),
            PatternRecognizer(
                supported_entity="PHONE_NUMBER",
                patterns=[Pattern("phone", r"(?:(?:\+?\d{1,3})?[-.\s()]*)?(?:\d[-.\s()]*){10,14}", 0.75)],
            ),
            PatternRecognizer(
                supported_entity="CREDIT_CARD",
                patterns=[Pattern("credit_card", r"\b(?:\d[ -]*?){13,19}\b", 0.7)],
            ),
            PatternRecognizer(
                supported_entity="US_SSN",
                patterns=[Pattern("ssn", r"\b\d{3}-\d{2}-\d{4}\b", 0.85)],
            ),
            PatternRecognizer(
                supported_entity="IP_ADDRESS",
                patterns=[
                    Pattern("ipv4", r"\b(?:\d{1,3}\.){3}\d{1,3}\b", 0.8),
                    Pattern("ipv6", r"\b(?:[A-Fa-f0-9]{1,4}:){2,7}[A-Fa-f0-9]{1,4}\b", 0.6),
                ],
            ),
            PatternRecognizer(
                supported_entity="IBAN_CODE",
                patterns=[Pattern("iban", r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b", 0.8)],
            ),
            PatternRecognizer(
                supported_entity="POSTAL_ADDRESS",
                patterns=[
                    Pattern(
                        "address",
                        r"\b\d{1,6}\s+[A-Za-z0-9.\s]+(?:Street|St|Road|Rd|Avenue|Ave|Lane|Ln|Drive|Dr|Blvd)\b",
                        0.55,
                    )
                ],
            ),
        ]

    def anonymize_text(self, text: str) -> PIIAnonymizationResult:
        raw = text or ""
        if not raw.strip() or not self.available or self.anonymizer is None:
            return PIIAnonymizationResult(
                original_text=raw,
                anonymized_text=raw,
                entity_types=[],
                available=self.available,
            )

        results: list[RecognizerResult] = []
        for recognizer in self.recognizers:
            try:
                results.extend(recognizer.analyze(text=raw, entities=recognizer.supported_entities, nlp_artifacts=None))
            except Exception:
                continue

        cleaned_results = self._dedupe_results(results)
        if not cleaned_results:
            return PIIAnonymizationResult(
                original_text=raw,
                anonymized_text=raw,
                entity_types=[],
                available=self.available,
            )

        operators = {
            result.entity_type: OperatorConfig("replace", {"new_value": f"<{result.entity_type.lower()}>"})
            for result in cleaned_results
        }
        anonymized = self.anonymizer.anonymize(text=raw, analyzer_results=cleaned_results, operators=operators)
        entity_types = []
        for result in cleaned_results:
            if result.entity_type not in entity_types:
                entity_types.append(result.entity_type)
        return PIIAnonymizationResult(
            original_text=raw,
            anonymized_text=anonymized.text,
            entity_types=entity_types,
            available=self.available,
        )

    @staticmethod
    def _dedupe_results(results: list[RecognizerResult]) -> list[RecognizerResult]:
        ordered = sorted(results, key=lambda item: (item.start, -(item.end - item.start), -item.score))
        selected: list[RecognizerResult] = []
        for candidate in ordered:
            overlap = False
            for existing in selected:
                if candidate.start < existing.end and candidate.end > existing.start:
                    overlap = True
                    break
            if not overlap:
                selected.append(candidate)
        return selected
