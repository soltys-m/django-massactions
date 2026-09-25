import json
from urllib.parse import unquote

from django.core import signing
from django.core.exceptions import ValidationError

from massactions.settings import get_selection_max_age

SELECTION_SALT = 'massactions.selection'


def sign_selection(selection):
    """
    Serialize the selection (dict or JSON string) and sign it with ``SECRET_KEY``.

    The value is tamper proof and expires (``MASSACTIONS_SELECTION_MAX_AGE``), but it is not secret:
    it is compressed JSON in base64. Nothing sensitive is stored in it, only ids and flags, and every id
    is re-validated against the config queryset anyway.
    """
    if isinstance(selection, (str, bytes)):
        selection = json.loads(selection)

    if not isinstance(selection, dict):
        raise ValueError('selection must be a dict')

    return signing.dumps(selection, salt=SELECTION_SALT, compress=True)


def unsign_selection(value, max_age=None):
    """Return the selection dict, or ``None`` when the value is missing, tampered with, expired or malformed."""
    if not value:
        return None

    if max_age is None:
        max_age = get_selection_max_age()

    try:
        data = signing.loads(unquote(value), salt=SELECTION_SALT, max_age=max_age)
    except (signing.BadSignature, ValueError, TypeError):  # SignatureExpired is a BadSignature
        return None

    return data if isinstance(data, dict) else None



def get_selection_cookie_name(user_id, key):
    return '%s_%s' % (user_id, key)


def parse_selection(cookie_value):
    """
    Decode the selection cookie written by the list page.
    Returns ``{'ids': [str], 'selectAll': bool, ...}`` or ``None`` when the cookie is missing, invalid or expired.
    """
    data = unsign_selection(cookie_value)

    if data is None:
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
