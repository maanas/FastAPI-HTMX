import pytest

from ..core.text import clean_text


@pytest.mark.parametrize(
    "typed, stored",
    [
        ("Tom & Jerry", "Tom & Jerry"),
        ("a < b", "a < b"),
        ("<b>bold</b> text", "bold text"),
        ("<script>alert(1)</script>ok", "ok"),
        ("say &quot;hi&quot;", 'say "hi"'),
        (None, ""),
    ],
)
def test_clean_text_strips_tags_and_keeps_characters(typed, stored):
    assert clean_text(typed) == stored
