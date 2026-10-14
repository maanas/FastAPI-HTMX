---
id: 2026-10-14-new-page-titles-urls-forms
status: proposed
target: skills/new-page/reference/checklist.md
metric: correctness
---
Evidence: log 2026-10-14, task "htmx leftovers", steps 1, 3b and 4: coder reported the new-page recipe silent on page titles, `path_for` and `submitted_form`; the rules are guarded by tests only after the fact. checklist.md is 25 lines, route.md is at 59 so the lines go to the checklist.
Change:
```diff
--- a/skills/new-page/reference/checklist.md
+++ b/skills/new-page/reference/checklist.md
@@ end
+- The page defines one literal `{% block title %}<View> | FastAPI HTMX{% endblock %}`; no `<title>` in a partial. Add the view to `VIEWS` in `app/tests/test_titles.py`.
+- URLs in templates use `path_for`, never `url_for`.
+- A failed form re-renders with `form` from `submitted_form`, so typed values stay.
```
Why: three rules the tests enforce become part of the recipe, not a failure found later.
