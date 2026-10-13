from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Jinja2 environment: auto-reload on, HTML autoescape on (`{{ value }}` is escaped;
# use `| tojson` inside a JS or JSON attribute, `| safe` only for server-made HTML)
jinja_env = Environment(
    loader=FileSystemLoader("app/templates"),
    auto_reload=True,
    autoescape=select_autoescape(["html", "xml"]),
)

# Use the custom environment in Jinja2Templates
templates = Jinja2Templates(env=jinja_env)
