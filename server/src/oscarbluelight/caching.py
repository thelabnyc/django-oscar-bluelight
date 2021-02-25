from django.utils.translation import gettext_lazy as _


class ConcreteFluentCache(object):
    def __init__(self, cache, key, timeout=None, version=None):
        self.cache = cache
        self.key = key
        self.timeout = timeout
        self.version = version

    def get(self, default=None):
        return self.cache.get(self.key, default=default, version=self.version)

    def set(self, value):
        return self.cache.set(
            self.key, value, timeout=self.timeout, version=self.version
        )

    def add(self, value):
        return self.cache.add(
            self.key, value, timeout=self.timeout, version=self.version
        )

    def get_or_set(self, default):
        return self.cache.get_or_set(
            self.key, default, timeout=self.timeout, version=self.version
        )

    def delete(self):
        return self.cache.delete(self.key, version=self.version)

    def touch(self):
        return self.cache.touch(self.key, timeout=self.timeout, version=self.version)


class CacheNamespace(object):
    def __init__(self, cache, name):
        self.cache = cache
        self.name = name

    @property
    def key(self):
        return "oscarbluelight.cache-ns:{}".format(self.name)

    @property
    def value(self):
        return self.cache.get_or_set(self.key, 1, timeout=None)

    def invalidate(self):
        key = self.key
        try:
            self.cache.incr(key, delta=1)
        except ValueError:
            self.cache.set(key, 1, timeout=None)


class FluentCache(object):
    def __init__(self, cache, key_base, timeout=None, version=None):
        self.cache = cache
        self._key_base = key_base
        self._timeout = timeout
        self._version = version
        self._namespaces = []
        self._key_parts = []

    def timeout(self, ttl):
        self._timeout = ttl
        return self

    def namespaces(self, *args):
        self._namespaces = args
        return self

    def key_parts(self, *args):
        self._key_parts = args
        return self

    def concrete(self, **kwargs):
        key = self.build_key(**kwargs)
        return ConcreteFluentCache(
            self.cache, key, timeout=self._timeout, version=self._version
        )

    def build_key(self, **kwargs):
        key_fragments = [self._key_base]
        # Add in serialized namespaces
        for namespace in self._namespaces:
            fragment = "ns:{}:{}".format(namespace.name, namespace.value)
            key_fragments.append(fragment)
        # Add in key parts
        for key_part in self._key_parts:
            if key_part not in kwargs:
                raise ValueError(
                    _("Cache key is missing value for key part: %s") % key_part
                )
            val = kwargs[key_part]
            fragment = "p:{}:{}".format(key_part, val)
            key_fragments.append(fragment)
        return ".".join(key_fragments)
