from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..mixins import BluelightBasketLineMixin as Line

    AffectedLine = tuple[Line, Decimal, int]
    AffectedLines = list[AffectedLine]
