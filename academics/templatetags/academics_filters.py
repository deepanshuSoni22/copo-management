# academics/templatetags/academics_filters.py
from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Allows accessing dictionary items by key in Django templates.
    Usage: {{ my_dict|get_item:my_key }}
    """
    if isinstance(dictionary, dict): # Ensure it's actually a dictionary
        return dictionary.get(key)
    return None # Return None if not a dict to avoid errors