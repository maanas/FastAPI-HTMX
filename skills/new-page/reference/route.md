# The route file

`app/routes/view/<name>.py`. Read `app/routes/view/role.py` lines 1 to 60 for the shape; do not read
every route file.

## Skeleton

```python
<name>_view_route = APIRouter()
<name>_crud = SQLAlchemyCRUD[<Model>](<Model>)


@<name>_view_route.get("/<name>", response_class=HTMLResponse)
async def get_<name>(
    request: Request,
    db: CurrentAsyncSession,
    current_user: UserModelDB = Depends(current_active_user),
    csrf_protect: CsrfProtect = Depends(),
):
    ...
```

## Imports that already exist

| Need | From |
|---|---|
| `CurrentAsyncSession` | `app.database.db` |
| `current_active_user` | `app.database.security` |
| `SQLAlchemyCRUD` | `app.routes.view.view_crud` |
| `handle_error` | `app.routes.view.errors` |
| `templates` | `app.templates` |
| `CsrfProtect` | `fastapi_csrf_protect` |

## Rules

- Every handler takes `current_user = Depends(current_active_user)` unless the page is public. A
  superuser-only page checks `current_user.is_superuser` and raises `HTTPException(403)`.
- Reads and writes go through `SQLAlchemyCRUD[Model](Model)`. Do not write a second CRUD helper and
  do not put a query in the handler when the helper has the method.
- A page with a form: the `GET` creates the CSRF pair, sets the cookie and passes `csrf_token` to
  the template. A write handler goes: auth dependency, `await csrf_protect.validate_csrf(request)`,
  superuser or ownership check, then the form and model rows, never before.
- Form values: `nh3.clean(str(form.get("field")))`, then the Pydantic schema. Never store a raw
  form value.
- Errors: `except Exception as e: return handle_error("<template>", {...}, e)`, as in `role.py`. A
  unique violation or unknown foreign key id is a 4xx alert (catch `IntegrityError`, roll back),
  never a 500. Alert text is fixed server text: no client input, host, bucket or path.
- After `await db.rollback()` do not read `current_user` or another loaded row; copy the id or
  email into a local before the `try`. Never log an email, token or CSRF value.
- No blocking call (file, network, `time.sleep`) in an async handler.
- JSON does not come from `app/routes/view/`; a JSON route goes in `app/routes/api/`.
- Partial versus page, status codes and `HX-*` headers: the `htmx-patterns` skill,
  `reference/responses.md`.

## Schema

`app/schema/<name>.py`, Pydantic v2: `<Name>Base`, `<Name>Create`, with `Field(min_length=...,
max_length=...)` limits that match the model's columns. `app/schema/users.py` (`RoleCreate`) is the
pattern.
