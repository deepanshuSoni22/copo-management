# academics/templatetags/academics_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Allows dictionary lookup using a variable key in templates."""
    return dictionary.get(key)