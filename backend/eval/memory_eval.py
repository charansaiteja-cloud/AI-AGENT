"""Offline and live evaluation for durable customer-fact extraction."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from backend.app.services.memory import ExtractedFact, MemoryExtractor
from backend.app.services.ollama import OllamaService

VALID_KINDS = frozenset(
    {
        "name",
        "company",
        "product",
        "operating_system",
        "issue",
        "preference",
        "account",
        "contact",
        "other",
    }
)


@dataclass(frozen=True)
class Case:
    """One labelled message and the facts a good extractor should retain."""

    message: str
    required_keywords: tuple[str, ...]
    forbidden_keywords: tuple[str, ...] = ()
    kind: str = "other"


DATASET: tuple[Case, ...] = (
    Case(
        message=("Hi, I'm Sarah Chen from Acme Corp. I use Ubuntu 24.04 on a Dell XPS 15."),
        required_keywords=("sarah", "acme", "ubuntu", "xps"),
        forbidden_keywords=("windows", "macos"),
        kind="name",
    ),
    Case(
        message="Please keep your answers short and skip the pleasantries.",
        required_keywords=("short",),
        forbidden_keywords=("verbose",),
        kind="preference",
    ),
    Case(
        message=("My Wi-Fi drops every 10 minutes after the laptop wakes from sleep."),
        required_keywords=("wi-fi", "drops", "sleep"),
        forbidden_keywords=("ethernet",),
        kind="issue",
    ),
    Case(
        message="My account ID is ACCT-4471 and I'm on the Enterprise plan.",
        required_keywords=("acct-4471", "enterprise"),
        forbidden_keywords=("free plan",),
        kind="account",
    ),
    Case(
        message="You can reach me at sarah.chen@example.com.",
        required_keywords=("sarah.chen@example.com",),
        kind="contact",
    ),
    Case(
        message=("We upgraded to Windows 11 last week and Outlook stopped syncing."),
        required_keywords=("windows 11", "outlook"),
        forbidden_keywords=("windows 10", "thunderbird"),
        kind="operating_system",
    ),
    Case(
        message="I don't have a ticket number yet, sorry.",
        required_keywords=(),
        forbidden_keywords=("ticket number is",),
        kind="other",
    ),
    Case(
        message="The VPN disconnects again, same as last month.",
        required_keywords=("vpn", "last month"),
        forbidden_keywords=("first time",),
        kind="issue",
    ),
)


class Extractor(Protocol):
    async def extract(self, message: str) -> list[ExtractedFact]: ...


class FixtureExtractor:
    """Deterministic extractor used to verify the scorer without a model.

    It returns one clean fact per required keyword. That makes fixture mode a
    test of the harness, not a measurement of Qwen3. Use ``--backend ollama``
    for a real measurement.
    """

    async def extract(self, message: str) -> list[ExtractedFact]:
        case = next((item for item in DATASET if item.message == message), None)
        if case is None:
            return []

        facts = [
            ExtractedFact(kind=case.kind, text=f"Customer mentioned {keyword}.")
            for keyword in case.required_keywords
        ]
        if not facts:
            facts.append(
                ExtractedFact(
                    kind="other",
                    text="Customer has not provided a ticket number yet.",
                )
            )
        return facts


@dataclass
class CaseResult:
    message: str
    facts: list[ExtractedFact]
    recall: float
    precision: float
    f1: float
    missing_keywords: list[str] = field(default_factory=list)
    irrelevant_facts: list[str] = field(default_factory=list)
    duplicate_facts: int = 0
    invalid_kinds: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "facts": [fact.text for fact in self.facts],
            "recall": round(self.recall, 4),
            "precision": round(self.precision, 4),
            "f1": round(self.f1, 4),
            "missing_keywords": self.missing_keywords,
            "irrelevant_facts": self.irrelevant_facts,
            "duplicate_facts": self.duplicate_facts,
            "invalid_kinds": self.invalid_kinds,
        }


@dataclass
class Report:
    cases: list[CaseResult]

    @property
    def recall(self) -> float:
        return _mean([case.recall for case in self.cases])

    @property
    def precision(self) -> float:
        return _mean([case.precision for case in self.cases])

    @property
    def f1(self) -> float:
        return _mean([case.f1 for case in self.cases])

    @property
    def duplicates(self) -> int:
        return sum(case.duplicate_facts for case in self.cases)

    @property
    def invalid_kinds(self) -> int:
        return sum(case.invalid_kinds for case in self.cases)

    def passed(self, min_recall: float, min_precision: float) -> bool:
        return (
            self.recall >= min_recall
            and self.precision >= min_precision
            and self.invalid_kinds == 0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "cases": [case.to_dict() for case in self.cases],
            "recall": round(self.recall, 4),
            "precision": round(self.precision, 4),
            "f1": round(self.f1, 4),
            "duplicates": self.duplicates,
            "invalid_kinds": self.invalid_kinds,
        }


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def score_case(case: Case, facts: list[ExtractedFact]) -> CaseResult:
    """Score one case using keyword coverage and fact relevance."""
    normalised = [fact.text.casefold() for fact in facts]
    joined = " ".join(normalised)

    missing = [keyword for keyword in case.required_keywords if keyword.casefold() not in joined]
    recall = (
        1.0
        if not case.required_keywords
        else (len(case.required_keywords) - len(missing)) / len(case.required_keywords)
    )

    relevant: list[str] = []
    irrelevant: list[str] = []
    for fact, text in zip(facts, normalised, strict=True):
        covers_required = any(keyword.casefold() in text for keyword in case.required_keywords)
        hits_forbidden = any(keyword.casefold() in text for keyword in case.forbidden_keywords)
        if hits_forbidden or (case.required_keywords and not covers_required):
            irrelevant.append(fact.text)
        else:
            relevant.append(fact.text)

    if not facts:
        precision = 0.0 if case.required_keywords else 1.0
    else:
        precision = len(relevant) / len(facts)

    f1 = 0.0 if recall + precision == 0 else 2 * recall * precision / (recall + precision)

    seen: set[str] = set()
    duplicates = 0
    for text in normalised:
        if text in seen:
            duplicates += 1
        seen.add(text)

    return CaseResult(
        message=case.message,
        facts=facts,
        recall=recall,
        precision=precision,
        f1=f1,
        missing_keywords=missing,
        irrelevant_facts=irrelevant,
        duplicate_facts=duplicates,
        invalid_kinds=sum(1 for fact in facts if fact.kind not in VALID_KINDS),
    )


async def evaluate(
    cases: Sequence[Case],
    extractor: Extractor,
) -> Report:
    results = []
    for case in cases:
        facts = await extractor.extract(case.message)
        results.append(score_case(case, facts))
    return Report(cases=results)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Measure durable-fact extraction. Fixture mode is offline and used "
            "in CI; ollama mode measures the real model."
        )
    )
    parser.add_argument("--backend", choices=["fixture", "ollama"], default="fixture")
    parser.add_argument("--model", default=None, help="Ollama model for live evaluation")
    parser.add_argument("--min-recall", type=float, default=0.8)
    parser.add_argument("--min-precision", type=float, default=0.8)
    parser.add_argument(
        "--output",
        choices=["json", "text"],
        default="json",
        help="report format (default: json)",
    )
    return parser


def _print_text(report: Report) -> None:
    print(
        f"cases={len(report.cases)} recall={report.recall:.3f} "
        f"precision={report.precision:.3f} f1={report.f1:.3f} "
        f"duplicates={report.duplicates} invalid_kinds={report.invalid_kinds}"
    )
    for case in report.cases:
        status = "ok" if case.recall >= 1.0 and case.precision >= 1.0 else "check"
        print(
            f"  [{status}] recall={case.recall:.2f} precision={case.precision:.2f} {case.message[:60]}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 0.0 <= args.min_recall <= 1.0 or not 0.0 <= args.min_precision <= 1.0:
        print("thresholds must be between 0 and 1", file=sys.stderr)
        return 2

    if args.backend == "fixture":
        extractor: Extractor = FixtureExtractor()
    else:
        ollama = OllamaService(model=args.model) if args.model else OllamaService()
        extractor = MemoryExtractor(ollama)

    report = asyncio.run(evaluate(DATASET, extractor))
    if args.output == "json":
        print(json.dumps(report.to_dict(), indent=2))
    else:
        _print_text(report)

    return 0 if report.passed(args.min_recall, args.min_precision) else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
