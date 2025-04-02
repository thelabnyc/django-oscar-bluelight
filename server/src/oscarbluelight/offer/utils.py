from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

from django.utils.translation import gettext_lazy as _

from .constants import Conjunction

if TYPE_CHECKING:
    from django_stubs_ext import StrOrPromise


def get_conjoiner(conjunction: str) -> StrOrPromise:
    labels = {
        Conjunction.AND: _(" and "),
        Conjunction.OR: _(" or "),
    }
    return labels[conjunction]


def human_readable_conjoin(
    conjunction: str,
    _strings: list[StrOrPromise] | Generator[StrOrPromise],
    empty: StrOrPromise | None = None,
) -> StrOrPromise:
    strings = list(_strings)
    if len(strings) <= 0 and empty is not None:
        return empty
    return get_conjoiner(conjunction).join(str(s) for s in strings)
