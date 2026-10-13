---
name: learning-report
description: Shows how the starter's dev team is learning - review rounds, findings, checker failures, corrections and tokens per step from .claude/learning/log.jsonl, and each applied rule change's metric before and after. Use when the user asks if the agents are improving, or before approving a retro proposal.
---
# Learning report

1. From the repo root: `uv run python .claude/skills/learning-report/report.py`
2. Show the output to the user.
3. For an applied rule whose metric did not drop after 3 or more steps, say so and name the proposal id. The next retro run proposes a revision.
4. Under "proposals waiting for approval", read each file in `.claude/learning/proposals/` and show its evidence and diff, so the user can approve or reject it.

Applying a decision (director only, after the user decides):
- approve: apply the diff to the target file, set `status: applied` and add `applied: YYYY-MM-DD` to the frontmatter, commit both in the task's branch.
- reject: set `status: rejected` and add `reason: <user's words>`. Retro does not propose it again.
