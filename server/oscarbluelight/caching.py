from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.core.cache.backends.base import BaseCache
from django.utils.translation import gettext_lazy as _


class ConcreteFluentCache:
    def __init__(
        self,
        cache: BaseCache,
        key: str,
        timeout: int | None = None,
        version: int | None = None,
    ):
        self.cache = cache
        self.key = key
        self.timeout = timeout
        self.version = version

    def get(self, default: Any = None) -> Any:
        return self.cache.get(self.key, default=default, version=self.version)

    def set(self, value: Any) -> None:
        return self.cache.set(
            self.key, value, timeout=self.timeout, version=self.version
        )

    def add(self, value: Any) -> bool:
        return self.cache.add(
            self.key, value, timeout=self.timeout, version=self.version
        )

    def get_or_set(self, default: Callable[[], Any]) -> Any:
        return self.cache.get_or_set(
            self.key, default, timeout=self.timeout, version=self.version
        )

    def delete(self) -> bool:
        return self.cache.delete(self.key, version=self.version)

    def touch(self) -> bool:
        return self.cache.touch(self.key, timeout=self.timeout, version=self.version)


class CacheNamespace:
    def __init__(self, cache: BaseCache, name: str):
        self.cache = cache
        self.name = name

    @property
    def key(self) -> str:
        return f"oscarbluelight.cache-ns:{self.name}"

    @property
    def value(self) -> Any:
        return self.cache.get_or_set(self.key, 1, timeout=None)

    def invalidate(self) -> None:
        key = self.key
        try:
            self.cache.incr(key, delta=1)
        except ValueError:
            self.cache.set(key, 1, timeout=None)


class FluentCache:
    def __init__(
        self,
        cache: BaseCache,
        key_base: str,
        timeout: int | None = None,
        version: int | None = None,
    ):
        self.cache = cache
        self._key_base = key_base
        self._timeout = timeout
        self._version = version
        self._namespaces: list[CacheNamespace] = []
        self._key_parts: list[str] = []

    def timeout(self, ttl: int) -> FluentCache:
        self._timeout = ttl
        return self

    def namespaces(self, *args: CacheNamespace) -> FluentCache:
        self._namespaces = list(args)
        return self

    def key_parts(self, *args: str) -> FluentCache:
        self._key_parts = list(args)
        return self

    def concrete(self, **kwargs: int | str) -> ConcreteFluentCache:
        key = self.build_key(**kwargs)
        return ConcreteFluentCache(
            self.cache,
            key,
            timeout=self._timeout,
            version=self._version,
        )

    def build_key(self, **kwargs: int | str) -> str:
        key_fragments = [self._key_base]
        # Add in serialized namespaces
        for namespace in self._namespaces:
            fragment = f"ns:{namespace.name}:{namespace.value}"
            key_fragments.append(fragment)
        # Add in key parts
        for key_part in self._key_parts:
            if key_part not in kwargs:
                raise ValueError(
                    _("Cache key is missing value for key part: %s") % key_part
                )
            val = kwargs[key_part]
            fragment = f"p:{key_part}:{val}"
            key_fragments.append(fragment)
        return ".".join(key_fragments)
