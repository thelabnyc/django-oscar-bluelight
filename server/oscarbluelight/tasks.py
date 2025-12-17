from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from functools import partial
from typing import TYPE_CHECKING, Generic, assert_never
import sys

from django.conf import settings
from django.db import transaction

if TYPE_CHECKING:
    from celery.app.task import Task as _CeleryTask
    from celery.result import AsyncResult as _CeleryAsyncResult

    try:
        from django_tasks.base import Task as _DjTask
        from django_tasks.base import TaskResult as _DjTaskResult
    except ImportError:  # django-tasks prior to 0.9.0
        from django_tasks.task import Task as _DjTask  # type:ignore
        from django_tasks.task import TaskResult as _DjTaskResult  # type:ignore
else:
    _CeleryTask = Callable
    _CeleryAsyncResult = Generic
    _DjTask = Callable
    _DjTaskResult = Generic


class BackendType(StrEnum):
    CELERY = "celery"
    DJANGO_TASKS = "django-tasks"


class Task[**P, T]:
    backend_type: BackendType

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        raise NotImplementedError()

    def enqueue(self, *args: P.args, **kwargs: P.kwargs) -> None:
        raise NotImplementedError()


class CeleryTask[**P, T](Task[P, T]):
    fn: _CeleryTask[P, T]

    def __init__(self, fn: Callable[P, T]) -> None:
        from celery import shared_task

        self.fn = shared_task(ignore_result=True)(fn)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.fn(*args, **kwargs)

    def enqueue(self, *args: P.args, **kwargs: P.kwargs) -> None:
        self.fn.apply_async(
            args=args,
            kwargs=kwargs,
            countdown=10,
        )


class DjTasksTask[**P, T](Task[P, T]):
    fn: _DjTask[P, T]

    def __init__(self, fn: Callable[P, T]) -> None:
        from django_tasks import task

        self.fn = task()(fn)

    @property
    def enqueue_on_commit(self) -> bool:
        """
        Normally we don't want to send the task until after commit. But, this
        doesn't work with tests since a commit wraps the whole test. So, send
        immediately then.
        """
        is_unit_test = "test" in sys.argv
        return not is_unit_test

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.fn.call(*args, **kwargs)

    def enqueue(self, *args: P.args, **kwargs: P.kwargs) -> None:
        if self.enqueue_on_commit:
            transaction.on_commit(partial(self.fn.enqueue, *args, **kwargs))
        else:
            self.fn.enqueue(*args, **kwargs)


def task[**P, T](fn: Callable[P, T]) -> Task[P, T]:
    btype_str = getattr(settings, "OSCAR_BLUELIGHT_TASKS_BACKEND", None)
    if btype_str is None:
        try:
            import celery  # NOQA

            btype_str = "celery"
        except ImportError:
            try:
                import django_tasks  # NOQA

                btype_str = "django-tasks"
            except ImportError:
                btype_str = "unknown"

    btype = BackendType(btype_str)
    if btype == BackendType.CELERY:
        return CeleryTask(fn)
    if btype == BackendType.DJANGO_TASKS:
        return DjTasksTask(fn)
    assert_never(btype)
