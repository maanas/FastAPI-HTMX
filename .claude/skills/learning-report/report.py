import json
import sys
from collections import Counter
from pathlib import Path

LEARNING = Path(".claude/learning")


def load_steps() -> list[dict]:
    log = LEARNING / "log.jsonl"
    if not log.exists():
        sys.exit(f"No log at {log}. Run the retro agent at the end of a task first.")
    steps = []
    for n, line in enumerate(log.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            sys.exit(f"{log}:{n} is not valid JSON ({e}). Fix or remove that line.")
        if row.get("type") == "step":
            steps.append(row)
    return steps


def load_proposals() -> list[dict]:
    proposals = []
    for path in sorted((LEARNING / "proposals").glob("*.md")):
        parts = path.read_text().split("---")
        if len(parts) < 3:
            sys.exit(f"{path} has no --- frontmatter. Add id, status, target, metric.")
        meta = dict(line.split(":", 1) for line in parts[1].strip().splitlines() if ":" in line)
        proposals.append({k.strip(): v.split("#")[0].strip() for k, v in meta.items()})
    return proposals


def value(step: dict, metric: str) -> float | None:
    if metric == "rounds":
        return step.get("review_rounds")
    if metric.startswith("tokens:"):
        return (step.get("tokens") or {}).get(metric[7:])
    found = sum(f.get("category") == metric for f in step.get("findings", []))
    failed = sum(f.get("id") == metric for f in (step.get("checker") or {}).get("failures", []))
    return found + failed


def mean(steps: list[dict], metric: str) -> str:
    values = [v for v in (value(s, metric) for s in steps) if v is not None]
    if not values:
        return "n/a"
    return f"{sum(values) / len(values):.2f} ({len(values)} steps)"


def main() -> None:
    steps = load_steps()
    proposals = load_proposals()
    print(f"{len(steps)} steps, {len({s.get('task') for s in steps})} tasks")
    print(f"review rounds per step: {mean(steps, 'rounds')}")
    for agent in ("coder", "reviewer", "checker", "committer"):
        print(f"tokens {agent} per step: {mean(steps, 'tokens:' + agent)}")

    cats = Counter(f.get("category") for s in steps for f in s.get("findings", []))
    fails = Counter(
        f.get("id") for s in steps for f in (s.get("checker") or {}).get("failures", [])
    )
    print("findings by category:", dict(cats.most_common()) or "none")
    print("checker failures:", dict(fails.most_common(10)) or "none")
    print("corrections:", sum(len(s.get("corrections", [])) for s in steps))

    print("\nrule changes (metric per step, before -> after):")
    for p in proposals:
        if p.get("status") != "applied" or not p.get("applied"):
            continue
        before = [s for s in steps if s.get("date", "") < p["applied"]]
        after = [s for s in steps if s.get("date", "") >= p["applied"]]
        m = p.get("metric", "")
        print(f"  {p.get('id')} [{m}]: {mean(before, m)} -> {mean(after, m)}")
    pending = [p.get("id") for p in proposals if p.get("status") == "proposed"]
    print("\nproposals waiting for approval:", pending or "none")


if __name__ == "__main__":
    main()
