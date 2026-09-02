"""
Text quality checks that the original profiling.py did not do: a check for private data
(PII) inside free text columns, and a casing/format consistency check for categorical text
columns.

Why this is a separate module: profiling.py's numeric outlier check only applies to number
columns. Text quality problems (private data hidden in a comment field, "Active" vs "active"
vs "ACTIVE" in a status column) were not caught at all. This closes that gap.

Why PII detection runs locally: the pipeline's rule is that the AI never sees raw client rows,
only a compact schema summary (see model_kpi_generator.py). If a free text column's raw sample
values were included in that summary, real personal data could reach OpenAI. So PII detection,
and the redaction that follows it, both run locally with Presidio, before anything is added to
the schema summary or saved to outputs/profiling.json. No raw matched text is ever kept, only
counts.
"""
import re

import pandas as pd

FREE_TEXT_MIN_AVG_LENGTH = 40  # avg chars; below this, treat the column as categorical, not free text
FREE_TEXT_MIN_DISTINCT_RATIO = 0.5  # most values must be distinct, not a repeated set of labels

PII_ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "LOCATION",
    "CREDIT_CARD",
    "IBAN_CODE",
]

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine

    # Presidio defaults to the large spaCy model (en_core_web_lg, ~400MB) unless told
    # otherwise. This project only installs the small model (en_core_web_sm, ~15MB), so the
    # engine is pointed at that explicitly, matching what's documented in the README.
    _nlp_engine = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        }
    ).create_engine()
    _analyzer = AnalyzerEngine(nlp_engine=_nlp_engine, supported_languages=["en"])
    _anonymizer = AnonymizerEngine()
    PRESIDIO_AVAILABLE = True
except Exception as e:
    # Presidio (or its spaCy model) is not installed. The pipeline still runs, just with a
    # much weaker, regex-only PII check. Printed loudly so this isn't a silent quality drop.
    print(
        f"Presidio could not be set up ({e}); falling back to a regex-only PII check "
        "(email and phone only, no name/location detection)."
    )
    _analyzer = None
    _anonymizer = None
    PRESIDIO_AVAILABLE = False

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\-. ]{7,}\d)")


def is_free_text_column(series: pd.Series) -> bool:
    """Long, mostly-unique strings (a comment, a narrative) count as free text.
    Short, repeated strings (a status, a category) count as categorical."""
    s = series.dropna().astype(str)
    if s.empty:
        return False
    avg_length = s.str.len().mean()
    distinct_ratio = s.nunique() / len(s)
    return avg_length >= FREE_TEXT_MIN_AVG_LENGTH and distinct_ratio >= FREE_TEXT_MIN_DISTINCT_RATIO


def _scan_value_regex(value: str) -> set[str]:
    found = set()
    if _EMAIL_RE.search(value):
        found.add("EMAIL_ADDRESS")
    if _PHONE_RE.search(value):
        found.add("PHONE_NUMBER")
    return found


def scan_column_for_pii(series: pd.Series, sample_size: int = 200) -> dict:
    """Scans up to `sample_size` non-null values for PII. Returns aggregate counts and
    percentages per entity type only, never the raw matched text or which rows matched.

    For a large table, `series` may itself already be a sample of the full column (see
    profiling.py's SAMPLE_ROW_THRESHOLD), and this function samples again on top of that, down
    to `sample_size`, since an NLP pass over every value would be slow even though it is free
    and local. So a "pct" in the result is a percentage of THIS function's own sample_size (its
    true size is returned as "sample_size" in the result), not of the whole column or table.
    """
    s = series.dropna().astype(str)
    if s.empty:
        return {}

    sample = s.sample(min(sample_size, len(s)), random_state=0)
    counts = {entity: 0 for entity in PII_ENTITIES}

    for value in sample:
        if PRESIDIO_AVAILABLE:
            results = _analyzer.analyze(text=value, language="en", entities=PII_ENTITIES)
            hit_types = {r.entity_type for r in results}
        else:
            hit_types = _scan_value_regex(value)
        for entity in hit_types:
            counts[entity] = counts.get(entity, 0) + 1

    n = len(sample)
    entity_findings = {
        entity: {"count": count, "pct": round(count / n * 100, 1)}
        for entity, count in counts.items()
        if count > 0
    }
    if not entity_findings:
        return {}
    return {"sample_size": n, "entities": entity_findings}


def redact_sample(value: str) -> str:
    """Masks any detected PII in a single string, for safe use as a 'sample value' in the
    schema summary sent to the LLM, or in outputs/profiling.json."""
    if not isinstance(value, str) or not value:
        return value

    if PRESIDIO_AVAILABLE:
        results = _analyzer.analyze(text=value, language="en", entities=PII_ENTITIES)
        if not results:
            return value
        return _anonymizer.anonymize(text=value, analyzer_results=results).text

    redacted = _EMAIL_RE.sub("<EMAIL_ADDRESS>", value)
    redacted = _PHONE_RE.sub("<PHONE_NUMBER>", redacted)
    return redacted


def check_casing_consistency(series: pd.Series) -> dict:
    """For a categorical text column, flags values that appear in more than one casing or
    spacing variant (e.g. 'Active', 'active', 'ACTIVE'). Returns one entry per normalized
    value that has more than one surface form, with each form's count."""
    s = series.dropna().astype(str)
    if s.empty:
        return {}

    variants: dict[str, dict[str, int]] = {}
    for value in s:
        normalized = " ".join(value.strip().lower().split())
        if not normalized:
            continue
        variants.setdefault(normalized, {})
        variants[normalized][value] = variants[normalized].get(value, 0) + 1

    return {
        normalized: forms
        for normalized, forms in variants.items()
        if len(forms) > 1
    }
