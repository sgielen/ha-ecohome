import pytest

from custom_components.ecohome.language import api_language


@pytest.mark.parametrize(
    ("home_assistant_language", "expected"),
    [
        ("en", "en_US"),
        ("en-GB", "en_US"),
        ("nl", "nl_NL"),
        ("de-DE", "de_DE"),
        ("fr", "fr_FR"),
        ("es-ES", "es_ES"),
        ("it", "it_IT"),
        ("zh-Hans", "zh_CN"),
        ("unsupported", "nl_NL"),
    ],
)
def test_api_language(home_assistant_language, expected):
    assert api_language(home_assistant_language) == expected
