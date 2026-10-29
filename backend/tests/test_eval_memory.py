from __future__ import annotations

import json

import pytest

from backend.app.services.memory import ExtractedFact
from backend.eval.memory_eval import (
    DATASET,
    Case,
    FixtureExtractor,
    Report,
    evaluate,
    main,
    score_case,
)


def test_dataset_messages_are_unique() -> None:
    messages = [case.message for case in DATASET]
    assert len(messages) == len(set(messages))
    assert len(DATASET) >= 8


def test_perfect_facts_score_one() -> None:
    case = Case(message="x", required_keywords=("alpha", "beta"))
    facts = [
        ExtractedFact(kind="other", text="Customer mentioned alpha."),
        ExtractedFact(kind="other", text="Customer mentioned beta."),
    ]

    result = score_case(case, facts)

    assert result.recall == 1.0
    assert result.precision == 1.0
    assert result.f1 == 1.0
    assert result.missing_keywords == []


def test_missing_keyword_lowers_recall() -> None:
    case = Case(message="x", required_keywords=("alpha", "beta"))
    facts = [ExtractedFact(kind="other", text="Customer mentioned alpha.")]

    result = score_case(case, facts)

    assert result.recall == 0.5
    assert result.missing_keywords == ["beta"]
    assert result.precision == 1.0


def test_irrelevant_fact_lowers_precision() -> None:
    case = Case(message="x", required_keywords=("alpha",))
    facts = [
        ExtractedFact(kind="other", text="Customer mentioned alpha."),
        ExtractedFact(kind="other", text="Customer likes pizza."),
    ]

    result = score_case(case, facts)

    assert result.recall == 1.0
    assert result.precision == 0.5
    assert result.irrelevant_facts == ["Customer likes pizza."]


def test_forbidden_keyword_marks_fact_irrelevant() -> None:
    case = Case(
        message="x",
        required_keywords=("alpha",),
        forbidden_keywords=("windows",),
    )
    facts = [
        ExtractedFact(kind="other", text="Customer mentioned alpha on Windows."),
    ]

    result = score_case(case, facts)

    assert result.precision == 0.0
    assert result.irrelevant_facts


def test_duplicates_and_invalid_kinds_are_counted() -> None:
    case = Case(message="x", required_keywords=("alpha",))
    facts = [
        ExtractedFact(kind="other", text="Customer mentioned alpha."),
        ExtractedFact(kind="not-a-kind", text="Customer mentioned alpha."),
    ]

    result = score_case(case, facts)

    assert result.duplicate_facts == 1
    assert result.invalid_kinds == 1


def test_empty_facts_score_zero_when_keywords_are_required() -> None:
    case = Case(message="x", required_keywords=("alpha",))

    result = score_case(case, [])

    assert result.recall == 0.0
    assert result.precision == 0.0
    assert result.f1 == 0.0


def test_case_without_required_keywords_is_perfect_when_empty() -> None:
    case = Case(message="x", required_keywords=())

    result = score_case(case, [])

    assert result.recall == 1.0
    assert result.precision == 1.0


@pytest.mark.anyio
async def test_fixture_extractor_passes_the_dataset() -> None:
    report = await evaluate(DATASET, FixtureExtractor())

    assert report.recall == 1.0
    assert report.precision == 1.0
    assert report.invalid_kinds == 0
    assert report.passed(min_recall=0.8, min_precision=0.8)


def test_report_thresholds_can_fail() -> None:
    case = Case(message="x", required_keywords=("alpha", "beta"))
    result = score_case(case, [])
    report = Report(cases=[result])

    assert report.passed(0.1, 0.0) is False
    assert report.passed(0.5, 0.0) is False
    assert report.passed(0.0, 0.1) is False


def test_report_serialises_metrics() -> None:
    case = Case(message="x", required_keywords=("alpha",))
    report = Report(cases=[score_case(case, [])])

    payload = report.to_dict()

    assert payload["recall"] == 0.0
    assert payload["cases"][0]["message"] == "x"


def test_cli_fixture_mode_succeeds(capsys) -> None:
    assert main(["--backend", "fixture"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["recall"] == 1.0


def test_cli_text_mode(capsys) -> None:
    assert main(["--backend", "fixture", "--output", "text"]) == 0

    output = capsys.readouterr().out
    assert "recall=1.000" in output


def test_cli_rejects_invalid_thresholds(capsys) -> None:
    assert main(["--min-recall", "1.5"]) == 2
    assert "between 0 and 1" in capsys.readouterr().err
