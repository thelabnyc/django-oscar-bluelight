from django import template


register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Given a dictionary and a key, return the key's value
    """
    return dictionary.get(key)
