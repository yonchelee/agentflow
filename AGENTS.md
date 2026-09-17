# Agent instructions

Human-authored project instructions belong outside the managed block below. The automation only rewrites text between the markers.

<!-- AUTO-MODEL-ROUTING:START -->
## Model routing

> Generated from official OpenAI documentation. Do not hand-edit this section.

| Tier | Current model | Reasoning | Use for | Fallback | Status |
|---|---|---|---|---|---|
| FAST | `gpt-5.6-luna` | low | Typos, formatting, renames, tiny CSS/UI edits, repetitive local changes | STANDARD | verified |
| STANDARD | `gpt-5.6-terra` | medium | Routine implementation, tests, debugging, ordinary refactors | DEEP | verified |
| DEEP | `gpt-5.6-sol` | high | Complex debugging, large refactors, coupled subsystems, design decisions | FRONTIER | verified |
| FRONTIER | `gpt-6-astra` | high | Hardest end-to-end work, failed prior attempts, high uncertainty or correctness risk | DEEP | verified |

### Routing rules

- Route by capability tier, not by hardcoded model names in task instructions.
- Prefer the least expensive/lowest-latency tier that can reliably satisfy the task.
- Escalate `FAST → STANDARD → DEEP → FRONTIER` after failure, rising uncertainty, broad coupling, or material correctness risk.
- De-escalate mechanical subtasks even when the parent task uses a stronger tier.
- Parallelize independent subtasks when safe; the parent agent must integrate and verify the result.
- Preview/experimental models never replace a stable route automatically; keep a stable fallback.
- Do not infer capability from version numbers alone. Official OpenAI guidance is required for promotion to a stable tier.
<!-- AUTO-MODEL-ROUTING:END -->
