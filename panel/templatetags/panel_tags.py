import json
import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def fromjson(value):
    try:
        return json.loads(value or "[]")
    except Exception:
        return []


class ParsedFile:
    def __init__(self, is_file=False, unique_id="", filename="", media_type="", raw=""):
        self.is_file    = is_file
        self.unique_id  = unique_id
        self.filename   = filename
        self.media_type = media_type
        self.raw        = raw


@register.filter
def parse_file_tag(content):
    if not content:
        return ParsedFile(raw=content or "")
    if content.startswith("[FILE:"):
        m = re.match(r"^\[FILE:([^:]*):([^:]*):(\w+)\]$", content)
        if m:
            return ParsedFile(
                is_file=True,
                unique_id=m.group(1),
                filename=m.group(2),
                media_type=m.group(3),
                raw=content,
            )
    return ParsedFile(raw=content)


@register.filter
def endswith(value, suffixes):
    """Usage: {{ value|endswith:'.pdf' }} or {{ value|endswith:'.pdf,.docx' }}"""
    if not value:
        return False
    for s in suffixes.split(","):
        if str(value).lower().endswith(s.strip().lower()):
            return True
    return False


@register.simple_tag
def multiply(a, b):
    try:
        return float(a) * float(b)
    except Exception:
        return 0


@register.filter
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def split(value, sep=","):
    """{{ 'a,b,c'|split:',' }} → ['a','b','c']"""
    return str(value).split(sep)


@register.filter
def replace(value, arg):
    """{{ value|replace:'T, ' }} → replaces T with space"""
    if "," not in arg:
        return value
    old, new = arg.split(",", 1)
    return str(value).replace(old, new)


@register.filter
def tojson(value):
    """Safe JSON encoding for use in JS: {{ value|tojson }}"""
    return mark_safe(json.dumps(str(value) if not isinstance(value, (dict, list)) else value))
