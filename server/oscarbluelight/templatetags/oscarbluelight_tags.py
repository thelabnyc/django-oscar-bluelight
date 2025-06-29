from typing import TypeVar

from django import template

register = template.Library()

T = TypeVar("T")


@register.filter
def get_item(dictionary: dict[str, T], key: str) -> T | None:
    """
    Given a dictionary and a key, return the key's value
    """
    return dictionary.get(key)
