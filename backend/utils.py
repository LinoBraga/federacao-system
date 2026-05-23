import unicodedata
import re


def normalize_name(name: str) -> str:
    if not name:
        return ""

    name = name.lower().strip()

    # remove acentos
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))

    # remove espaços extras
    name = re.sub(r"\s+", " ", name)

    return name