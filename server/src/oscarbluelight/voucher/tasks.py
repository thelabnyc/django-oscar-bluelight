from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING
import logging

from ..tasks import task

if TYPE_CHECKING:
    from django_stubs_ext import StrOrPromise

logger = logging.getLogger(__name__)


@task
def update_child_vouchers(voucher_id: int) -> None:
    from .models import Voucher

    parent = Voucher.objects.get(pk=voucher_id)
    parent.update_children()


@task
def add_child_codes(
    voucher_id: int,
    auto_generate_count: int = 0,
    custom_codes: Sequence[str] = [],
) -> tuple[list[StrOrPromise], int]:
    from .models import Voucher

    parent = Voucher.objects.get(pk=voucher_id)
    errors, success_count = parent.create_children(
        auto_generate_count=auto_generate_count, custom_codes=custom_codes
    )
    parent.save()
    for error in errors:
        logger.warning(error)
    return errors, success_count
