"""Language conversion for the Eco-Home API."""

DEFAULT_API_LANGUAGE = "nl_NL"

_API_LANGUAGE_BY_HOME_ASSISTANT_LANGUAGE = {
    "de": "de_DE",
    "en": "en_US",
    "es": "es_ES",
    "fr": "fr_FR",
    "it": "it_IT",
    "nl": "nl_NL",
    "zh": "zh_CN",
}


def api_language(home_assistant_language: str) -> str:
    """Convert a Home Assistant language code to an Eco-Home API locale."""
    base_language = home_assistant_language.replace("_", "-").split("-", 1)[0].lower()
    return _API_LANGUAGE_BY_HOME_ASSISTANT_LANGUAGE.get(
        base_language, DEFAULT_API_LANGUAGE
    )
