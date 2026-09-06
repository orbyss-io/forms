"""Score explicitly collected multi-provider comprehension trials without invoking models or networks."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def score(questions: dict, trials: dict) -> dict:
    if questions.get("version") != "1.0" or trials.get("version") != "1.0":
        raise ValueError("Expected evaluation format 1.0")
    items = questions.get("questions")
    if not isinstance(items, list) or not items:
        raise ValueError("At least one human-authored question is required")
    by_id = {}
    for question in items:
        if set(question) != {"id", "prompt", "requiredFacts", "allowedCitations"}:
            raise ValueError("Question needs id, prompt, requiredFacts and allowedCitations")
        if not isinstance(question["id"], str) or question["id"] in by_id or not question["prompt"]:
            raise ValueError("Question identities must be unique")
        for name in ("requiredFacts", "allowedCitations"):
            if not isinstance(question[name], list) or not question[name] or not all(isinstance(v, str) and v for v in question[name]):
                raise ValueError("Questions require explicit facts and canonical citation allowlists")
        by_id[question["id"]] = question
    runs = trials.get("trials")
    if not isinstance(runs, list) or not runs:
        raise ValueError("No collected trials were supplied")
    results, seen = [], set()
    for run in runs:
        if set(run) != {"provider", "model", "version", "trial", "representation", "answers"}:
            raise ValueError("Each trial needs provider, model, version, trial, representation and answers")
        if not all(isinstance(run[k], str) and run[k] for k in ("provider", "model", "version")):
            raise ValueError("Provider/model/version evidence is required")
        if type(run["trial"]) is not int or run["trial"] < 1 or run["representation"] not in {"html", "markdown"}:
            raise ValueError("Trials need a positive ordinal and a known representation")
        key = tuple(run[k] for k in ("provider", "model", "version", "trial", "representation"))
        if key in seen:
            raise ValueError("Duplicate trial")
        seen.add(key)
        answers = run["answers"]
        if not isinstance(answers, list) or len(answers) != len(by_id):
            raise ValueError("Every trial must answer every identical fixture question")
        answered = set()
        for answer in answers:
            if set(answer) != {"questionId", "answer", "citations"} or answer["questionId"] not in by_id or answer["questionId"] in answered:
                raise ValueError("Unknown/duplicate/incomplete answer")
            answered.add(answer["questionId"])
            if not isinstance(answer["answer"], str) or not isinstance(answer["citations"], list) or not all(isinstance(c, str) for c in answer["citations"]):
                raise ValueError("Answer text and citation list are required")
            question = by_id[answer["questionId"]]
            # A deliberately limited lexical metric. Negation, entailment and unsupported additions
            # require independent human/semantic adjudication; substring hits are not truth scores.
            found = [fact for fact in question["requiredFacts"] if re.search(r"(?<!\w)" + re.escape(fact) + r"(?!\w)", answer["answer"], flags=re.I)]
            citations = answer["citations"]
            results.append({**{k: run[k] for k in ("provider", "model", "version", "trial", "representation")},
                "questionId": answer["questionId"], "literalFactCoverage": len(found) / len(question["requiredFacts"]),
                "missingLiteralFacts": [fact for fact in question["requiredFacts"] if fact not in found],
                "canonicalCitationMatch": bool(citations) and all(c in question["allowedCitations"] for c in citations),
                "semanticAdjudication": "required"})
    return {"version": "1.0", "results": results, "providers": sorted({run["provider"] for run in runs}),
            "limitations": "Lexical fact coverage and citation allowlist only. Not factual entailment, discovery/ranking, or universal model performance. Review negation, qualifiers, unsupported claims and actual citation support independently."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", required=True)
    parser.add_argument("--trials", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    report = Path(args.report)
    if report.exists():
        raise ValueError("Evaluation evidence already exists; use a new report path")
    result = score(json.loads(Path(args.questions).read_text(encoding="utf-8")), json.loads(Path(args.trials).read_text(encoding="utf-8")))
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("x", encoding="utf-8") as output:
        json.dump(result, output, indent=2)
    print(f"Scored {len(result['results'])} collected answers; semantic adjudication remains required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
