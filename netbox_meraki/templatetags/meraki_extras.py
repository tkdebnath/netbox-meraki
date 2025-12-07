# Template tags for NetBox Meraki plugin
from django import template

register = template.Library()


@register.filter
def lookup(dictionary, key):
    """
    Template filter to get a value from a dictionary by key
    Usage: {{ dict|lookup:key }}
    """
    if dictionary is None:
        return None
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''
