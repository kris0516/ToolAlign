"""Keys and equality for finite, parsed JSON without Python bool/number coercion.

Object key order and serialization whitespace do not matter; array order does.
Null, booleans, strings, numbers, arrays and objects remain distinct at every
depth. Parsed integer/float representations (1 versus 1.0, signed float zero)
are retained too. Non-JSON Python containers/keys and non-finite numbers fail.
This compares data only and never evaluates source text.
"""

import json


def _validate(value):
    kind = type(value)
    if value is None or kind in (str, bool, int, float):
        return
    if kind is list:
        for item in value:
            _validate(item)
        return
    if kind is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError("JSON object keys must be strings")
            _validate(item)
        return
    raise TypeError("Expected a JSON value")


def json_key(value):
    """Return an order-independent object key that preserves parsed JSON types."""
    _validate(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


def json_equal(before, after):
    return json_key(before) == json_key(after)
