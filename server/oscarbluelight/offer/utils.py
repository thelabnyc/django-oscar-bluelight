from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING
import functools
import logging

from django.conf import settings
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from .constants import Conjunction
from .line_filters import DefaultLineFilterStrategy

if TYPE_CHECKING:
    from django_stubs_ext import StrOrPromise

    from .line_filters import BaseLineFilterStrategy

logger = logging.getLogger(__name__)


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


@functools.lru_cache(maxsize=10)
def _get_line_filter_strategy_inst(cls_path: str | None) -> BaseLineFilterStrategy:
    if cls_path:
        strategy_class = import_string(cls_path)
        return strategy_class()
    return DefaultLineFilterStrategy()


def get_line_filter_strategy() -> BaseLineFilterStrategy:
    """
    Get the configured line filtering strategy instance.

    Uses OSCARBLUELIGHT_LINE_FILTER_STRATEGY setting to load a custom strategy class.
    Falls back to DefaultLineFilterStrategy if no setting is provided or import fails.

    Returns:
        BaseLineFilterStrategy: Instance of the configured strategy class
    """

    strategy_path = getattr(settings, "OSCARBLUELIGHT_LINE_FILTER_STRATEGY", None)
    return _get_line_filter_strategy_inst(strategy_path)
