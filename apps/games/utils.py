# apps/games/utils.py
"""
Funciones utilitarias generales y agnósticas del dominio juego.
"""
import re
from typing import Any, List, Optional, Dict

__all__ = [
    "parse_to_float",
    "numeric_feedback",
    "to_list",
]

# ----------------------------------------------------------------------
# Conversión de strings numéricos → float
# ----------------------------------------------------------------------
def parse_to_float(value: Any) -> Optional[float]:
    """Convierte un string con separadores europeos/americanos a float."""
    if value is None:
        return None

    match = re.search(r"[-+]?\d[\d.,]*", str(value))
    if not match:
        return None

    num_str = match.group()

    if num_str.count(".") > 1 and num_str.count(",") == 0:
        num_str = num_str.replace(".", "")
    elif num_str.count(",") > 1 and num_str.count(".") == 0:
        num_str = num_str.replace(",", "")
    elif "." in num_str and "," in num_str:
        if num_str.rfind(",") > num_str.rfind("."):
            num_str = num_str.replace(".", "").replace(",", ".")
        else:
            num_str = num_str.replace(",", "")
    elif "," in num_str:
        num_str = num_str.replace(",", ".")

    try:
        return float(num_str)
    except ValueError:
        return None


# ----------------------------------------------------------------------
# Feedback numérico (“Más / Menos”)
# ----------------------------------------------------------------------
def numeric_feedback(guess: Optional[float], target: Optional[float]) -> Dict[str, str]:
    if guess is None or target is None:
        return {"arrow": "", "hint": "Incorrecto"}
    if guess == target:
        return {"arrow": "", "hint": ""}
    return {
        "arrow": "▲" if guess < target else "▼",
        "hint": "Más" if guess < target else "Menos",
    }


# ----------------------------------------------------------------------
# Normalizar campos multi-valor a lista[str]
# ----------------------------------------------------------------------
def to_list(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return list(raw)
    return [s.strip() for s in str(raw).split(",") if s.strip()]
