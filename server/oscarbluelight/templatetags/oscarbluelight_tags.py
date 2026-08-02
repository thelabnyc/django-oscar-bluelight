from django import template

register = template.Library()


@register.filter
def get_item[T](dictionary: dict[str, T], key: str) -> T | None:
    """
    Given a dictionary and a key, return the key's value
    """
    return dictionary.get(key)
