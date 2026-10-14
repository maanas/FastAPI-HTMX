from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, pass_context, select_autoescape

APP_DIR = Path(__file__).resolve().parent


@pass_context
def path_for(context, name, **params):
    """Path of a named route (`/get_role/3`), never scheme and host: htmx runs with
    selfRequestsOnly, so an absolute url_for() breaks behind a proxy."""
    return str(context["request"].app.url_path_for(name, **params))


# Jinja2 environment: auto-reload on, HTML autoescape on (`{{ value }}` is escaped;
# use `| tojson` inside a JS or JSON attribute, `| safe` only for server-made HTML)
jinja_env = Environment(
    loader=FileSystemLoader(APP_DIR / "templates"),
    auto_reload=True,
    autoescape=select_autoescape(["html", "xml"]),
)
jinja_env.globals["path_for"] = path_for

# Use the custom environment in Jinja2Templates
templates = Jinja2Templates(env=jinja_env)
