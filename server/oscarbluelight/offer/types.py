from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oscar.apps.basket.models import Line

    AffectedLine = tuple[Line, Decimal, int]
    AffectedLines = list[AffectedLine]

    # Type for (price, line) tuples returned by get_applicable_lines
    LinesTuple = tuple[Decimal, Line]
