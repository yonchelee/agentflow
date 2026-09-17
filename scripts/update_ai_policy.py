#!/usr/bin/env python3
"""Refresh capability-tier model routing from official OpenAI documentation.

Safety properties:
- Only allowlisted OpenAI domains are read.
- Existing stable routes are never silently replaced by an unknown model.
- Unknown/new models are recorded for review.
- Generated timestamps are intentionally omitted so unchanged runs produce no diff.
- Human-authored text outside managed markers is never modified.
"""

from __future__ import annotations

import html
import json
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / ".ai" / "models.generated.json"
ROUTING_PATH = ROOT / ".ai" / "routing.generated.md"
MANAGED_DOCS = [ROOT / "AGENTS.md", ROOT / "CLAUDE.md"]

SOURCES = [
    "https://developers.openai.com/api/docs/models",
    "https://developers.openai.com/api/docs/models/all",
    "https://developers.openai.com/api/docs/guides/latest-model",
]
ALLOWED_HOSTS = {"developers.openai.com", "openai.com", "help.openai.com"}

# Known-good capability families. These are fallback seeds, not permanent truth.
# A route is updated only when the model is still present in official docs.
SEED_ROUTES = {
    "FRONTIER": {
        "model": "gpt-6-astra",
        "reasoning": "high",
        "fallback": "DEEP",
        "evidence": "most capable / hardest end-to-end work",
    },
    "DEEP": {
        "model": "gpt-5.6-sol",
        "reasoning": "high",
        "fallback": "FRONTIER",
        "evidence": "complex professional work",
    },
    "STANDARD": {
        "model": "gpt-5.6-terra",
        "reasoning": "medium",
        "fallback": "DEEP",
        "evidence": "balances intelligence and cost",
    },
    "FAST": {
        "model": "gpt-5.6-luna",
        "reasoning": "low",
        "fallback": "STANDARD",
        "evidence": "cost-sensitive, high-volume workloads",
    },
}

START = "<!-- AUTO-MODEL-ROUTING:START -->"
END = "<!-- AUTO-MODEL-ROUTING:END -->"

MODEL_ID_RE = re.compile(r"\bgpt-(?:\d+(?:\.\d+)*)(?:-[a-z0-9]+(?:-[a-z0-9]+)*)?\b", re.I)


def fetch_text(url: str) -> str:
    host = urlparse(url).hostname
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"Refusing non-OpenAI source: {url}")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "agentflow-model-policy/1.0 (+https://github.com/yonchelee/agentflow)"},
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        raw = response.read().decode("utf-8", errors="replace")
    # Sufficient for keyword/model discovery; we intentionally do not execute JS.
    raw = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<style\b[^>]*>.*?</style>", " ", raw, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(text)).strip().lower()


def load_previous() -> dict:
    if not REGISTRY_PATH.exists():
        return {}
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def discover() -> tuple[set[str], dict[str, list[str]]]:
    discovered: set[str] = set()
    source_models: dict[str, list[str]] = {}
    successful_sources = 0

    for url in SOURCES:
        try:
            text = fetch_text(url)
        except Exception as exc:  # network/docs outage must not corrupt routing
            print(f"warning: failed to read {url}: {exc}", file=sys.stderr)
            continue
        successful_sources += 1
        models = sorted({m.lower() for m in MODEL_ID_RE.findall(text)})
        source_models[url] = models
        discovered.update(models)

    if successful_sources < 2:
        raise RuntimeError(
            f"Only {successful_sources} official sources were reachable; refusing to rewrite routing."
        )
    return discovered, source_models


def build_registry(discovered: set[str], source_models: dict[str, list[str]]) -> dict:
    previous = load_previous()
    previous_routes = previous.get("routes", {}) if isinstance(previous, dict) else {}

    routes: dict[str, dict] = {}
    warnings: list[str] = []

    for tier, seed in SEED_ROUTES.items():
        candidate = seed["model"]
        if candidate in discovered:
            routes[tier] = dict(seed)
            routes[tier]["status"] = "verified"
        elif tier in previous_routes and previous_routes[tier].get("model"):
            # Do not auto-replace an established route merely because docs changed or parsing failed.
            routes[tier] = dict(previous_routes[tier])
            routes[tier]["status"] = "review-required"
            warnings.append(
                f"{tier}: expected {candidate} was not found in current official model docs; previous route preserved."
            )
        else:
            routes[tier] = dict(seed)
            routes[tier]["status"] = "review-required"
            warnings.append(f"{tier}: {candidate} could not be verified; seed retained for manual review.")

    routed_models = {route["model"] for route in routes.values()}
    # Only surface modern families as review candidates; ignore old historical IDs linked in docs.
    review_candidates = sorted(
        m
        for m in discovered
        if m not in routed_models
        and re.match(r"^gpt-(?:5\.[3-9]|6(?:\.|-))", m)
    )

    # Preserve explicit preview treatment for Spark when it is visible in docs.
    experimental = []
    for model in review_candidates:
        if "spark" in model:
            experimental.append(
                {
                    "model": model,
                    "channel": "preview-or-specialized",
                    "stable_route": False,
                    "fallback_tier": "STANDARD",
                }
            )

    return {
        "policy_version": 1,
        "sources": SOURCES,
        "routes": routes,
        "review_candidates": review_candidates,
        "experimental": experimental,
        "warnings": warnings,
        "source_observations": source_models,
    }


def render_routing(registry: dict) -> str:
    routes = registry["routes"]
    lines = [
        "## Model routing",
        "",
        "> Generated from official OpenAI documentation. Do not hand-edit this section.",
        "",
        "| Tier | Current model | Reasoning | Use for | Fallback | Status |",
        "|---|---|---|---|---|---|",
    ]
    use_for = {
        "FAST": "Typos, formatting, renames, tiny CSS/UI edits, repetitive local changes",
        "STANDARD": "Routine implementation, tests, debugging, ordinary refactors",
        "DEEP": "Complex debugging, large refactors, coupled subsystems, design decisions",
        "FRONTIER": "Hardest end-to-end work, failed prior attempts, high uncertainty or correctness risk",
    }
    for tier in ("FAST", "STANDARD", "DEEP", "FRONTIER"):
        route = routes[tier]
        lines.append(
            f"| {tier} | `{route['model']}` | {route['reasoning']} | {use_for[tier]} | {route['fallback']} | {route['status']} |"
        )

    lines += [
        "",
        "### Routing rules",
        "",
        "- Route by capability tier, not by hardcoded model names in task instructions.",
        "- Prefer the least expensive/lowest-latency tier that can reliably satisfy the task.",
        "- Escalate `FAST → STANDARD → DEEP → FRONTIER` after failure, rising uncertainty, broad coupling, or material correctness risk.",
        "- De-escalate mechanical subtasks even when the parent task uses a stronger tier.",
        "- Parallelize independent subtasks when safe; the parent agent must integrate and verify the result.",
        "- Preview/experimental models never replace a stable route automatically; keep a stable fallback.",
        "- Do not infer capability from version numbers alone. Official OpenAI guidance is required for promotion to a stable tier.",
    ]

    if registry.get("review_candidates"):
        lines += [
            "",
            "### Review candidates",
            "",
            "New or unrouted model IDs were observed in official docs. They require review before becoming a stable route:",
            "",
        ]
        lines.extend(f"- `{m}`" for m in registry["review_candidates"])

    if registry.get("warnings"):
        lines += ["", "### Warnings", ""]
        lines.extend(f"- {w}" for w in registry["warnings"])

    return "\n".join(lines).rstrip() + "\n"


def replace_managed_block(path: Path, generated: str) -> None:
    block = f"{START}\n{generated.rstrip()}\n{END}"
    if path.exists():
        original = path.read_text(encoding="utf-8")
        if START in original and END in original:
            pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
            updated = pattern.sub(block, original)
        else:
            updated = original.rstrip() + "\n\n" + block + "\n"
    else:
        title = "# Agent instructions" if path.name == "AGENTS.md" else "# Claude instructions"
        intro = (
            "\n\nHuman-authored project instructions belong outside the managed block below. "
            "The automation only rewrites text between the markers.\n\n"
        )
        updated = title + intro + block + "\n"
    path.write_text(updated, encoding="utf-8")


def main() -> int:
    discovered, source_models = discover()
    registry = build_registry(discovered, source_models)
    routing = render_routing(registry)

    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    ROUTING_PATH.write_text(routing, encoding="utf-8")
    for doc in MANAGED_DOCS:
        replace_managed_block(doc, routing)

    print("AI model routing refreshed from official OpenAI sources.")
    if registry["warnings"]:
        print("Warnings require review:")
        for warning in registry["warnings"]:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
