import re
import unicodedata

ARC_REFERENCE_PHRASES: tuple[str, ...] = (
    "Orange Town",
    "Shells Town",
    "Baratie",
    "el Baratie",
    "Loguetown",
    "Arlong Park",
    "Drum Castle",
    "Alabasta",
    "Jaya",
    "Skypiea",
    "Whiskey Peak",
    "Water 7",
    "Sabaody",
    "Thriller Bark",
    "Amazon Lily",
    "Impel Down",
    "Marineford",
    "Whole Cake",
    "Broc Coli",
    "Isla Gyojin",
    "God Valley",
    "Egghead",
    "Reverie",
    "Marine",
)

_PREPOSITIONS = ("en", "desde", "del", "de", "a")
_ARTICLES = ("el", "la", "los", "las")

_SUFFIX_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = ()
_INLINE_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = ()


def _build_replacements() -> None:
    global _SUFFIX_REPLACEMENTS, _INLINE_REPLACEMENTS
    suffix_patterns: list[tuple[re.Pattern[str], str]] = []
    inline_patterns: list[tuple[re.Pattern[str], str]] = []

    article_group = "|".join(_ARTICLES)
    preposition_group = "|".join(_PREPOSITIONS)

    for phrase in ARC_REFERENCE_PHRASES:
        escaped = re.escape(phrase)
        suffix_patterns.append(
            (
                re.compile(
                    rf"\s+(?:{preposition_group})\s+(?:(?:{article_group})\s+)?{escaped}\s*$",
                    re.IGNORECASE,
                ),
                "",
            )
        )
        suffix_patterns.append(
            (
                re.compile(rf"\s+{escaped}\s*$", re.IGNORECASE),
                "",
            )
        )
        inline_patterns.append(
            (
                re.compile(rf"\s+en\s+{escaped}\s+", re.IGNORECASE),
                " ",
            )
        )

    suffix_patterns.extend(
        [
            (re.compile(r"\s+en el retorno a Sabaody\s*$", re.IGNORECASE), ""),
            (re.compile(r"\s+en los subsuelos de Alabasta\s*$", re.IGNORECASE), ""),
            (re.compile(r"\s+en el palacio real de Alabasta\s*$", re.IGNORECASE), ""),
            (re.compile(r"\s+de Alabasta\s*$", re.IGNORECASE), ""),
            (re.compile(r"\s+del Whole Cake\s*$", re.IGNORECASE), ""),
            (re.compile(r"\s+de Arlong Park\s*$", re.IGNORECASE), ""),
        ]
    )

    _SUFFIX_REPLACEMENTS = tuple(suffix_patterns)
    _INLINE_REPLACEMENTS = tuple(inline_patterns)


_build_replacements()


def sanitize_proximity_prompt_text(text: str) -> str:
    if not text:
        return text

    cleaned = text.strip()
    previous = None
    while cleaned != previous:
        previous = cleaned
        for pattern, replacement in _INLINE_REPLACEMENTS + _SUFFIX_REPLACEMENTS:
            cleaned = pattern.sub(replacement, cleaned).strip()
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned
