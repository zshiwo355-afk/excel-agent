import math
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any


def _normalize_float(value: float) -> float | None:
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def _numpy_scalar_to_python(value: Any) -> Any:
    if hasattr(value, "item") and callable(value.item):
        try:
            return value.item()
        except Exception:
            return value
    return value


def to_jsonable(value: Any) -> Any:
    value = _numpy_scalar_to_python(value)

    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        return _normalize_float(value)

    if isinstance(value, (datetime, date, time)):
        return value.isoformat()

    if isinstance(value, Decimal):
        try:
            return _normalize_float(float(value))
        except Exception:
            return str(value)

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]

    if hasattr(value, "to_pydatetime") and callable(value.to_pydatetime):
        try:
            return value.to_pydatetime().isoformat()
        except Exception:
            pass

    if hasattr(value, "to_pytimedelta") and callable(value.to_pytimedelta):
        try:
            return str(value.to_pytimedelta())
        except Exception:
            pass

    if hasattr(value, "tolist") and callable(value.tolist):
        try:
            return to_jsonable(value.tolist())
        except Exception:
            pass

    return str(value)
