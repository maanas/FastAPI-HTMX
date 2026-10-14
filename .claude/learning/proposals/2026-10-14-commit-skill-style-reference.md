---
id: 2026-10-14-commit-skill-style-reference
status: applied
applied: 2026-10-14
target: .claude/skills/commit/SKILL.md
metric: style
---
Evidence: 2026-10-14 "Housekeeping" steps 1 and 2: the committer noted that the commit skill points to `git log --format=%s -5 chore/starter-setup`, a branch that does not exist in this repo.
Change:
```diff
--- a/.claude/skills/commit/SKILL.md
+++ b/.claude/skills/commit/SKILL.md
@@ line 14
-(see `git log --format=%s -5 chore/starter-setup`):
+(see `git log --format=%s -5 main`):
```
Why: the committer reads the style from a real ref instead of reporting a dead branch every step.
