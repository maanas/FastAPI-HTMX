import html

import nh3


def clean_text(value: object) -> str:
    """Form text without tags, as plain text.

    `nh3.clean` also escapes `&` and `<`, which Jinja autoescape then escapes a second
    time on output. Tags are stripped, then the entities are decoded again: the stored
    text is what the user typed, and the template escapes it once. No template renders
    these fields with `|safe`. A missing value (`None`) gives an empty string, not the
    text "None".
    """
    if value is None:
        return ""
    return html.unescape(nh3.clean(str(value), tags=set()))
