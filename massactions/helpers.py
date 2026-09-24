import base64
import json
import random
import string
from urllib.parse import unquote

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from django.core.exceptions import ValidationError

KEY_LENGTH = 16


def encrypt_string(string_to_encrypt):
    key = ''.join(random.choices(string.ascii_letters + string.digits, k=KEY_LENGTH))
    padded = pad(string_to_encrypt.encode(), 16)
    cipher = AES.new(key.encode('utf-8'), AES.MODE_ECB)
    return base64.b64encode(cipher.encrypt(padded)).decode('utf-8') + key


def decrypt_string(string_to_decrypt):
    key = string_to_decrypt[-KEY_LENGTH:]
    enc = base64.b64decode(string_to_decrypt[:-KEY_LENGTH])
    cipher = AES.new(key.encode('utf-8'), AES.MODE_ECB)
    return unpad(cipher.decrypt(enc), 16).decode('utf-8')


def get_selection_cookie_name(user_id, key):
    return '%s_%s' % (user_id, key)


def parse_selection(cookie_value):
    """
    Decode the selection cookie written by the list page.
    Returns ``{'ids': [str], 'selectAll': bool, ...}`` or ``None`` when the cookie is missing or malformed.
    """
    if not cookie_value:
        return None

    try:
        data = json.loads(decrypt_string(unquote(cookie_value)))
    except (ValueError, TypeError, IndexError):
        return None

    if not isinstance(data, dict):
        return None

    ids = data.get('ids') or []

    if not isinstance(ids, (list, tuple)):
        return None

    return {
        'ids': [str(pk) for pk in ids],
        'selectAll': bool(data.get('selectAll')),
        'user': data.get('user'),
        'currentFilter': data.get('currentFilter'),
    }


def clean_ids(model, ids):
    """Drop values that cannot be a primary key of ``model`` instead of raising at query time."""
    pk_field = model._meta.pk
    cleaned = []

    for value in ids:
        if value in (None, ''):
            continue
        try:
            cleaned.append(pk_field.to_python(value))
        except (ValidationError, ValueError, TypeError):
            continue

    return cleaned


def apply_selection(queryset, selection):
    ids = clean_ids(queryset.model, selection.get('ids') or [])

    if selection.get('selectAll'):
        return queryset.exclude(pk__in=ids) if ids else queryset

    return queryset.filter(pk__in=ids)


def set_selection_done_cookie(response, cookie_name, success=True):
    """Tell the list page (JS) to clear the stored selection after a finished action."""
    response.set_cookie(cookie_name, 'True' if success else 'False')
    return response
