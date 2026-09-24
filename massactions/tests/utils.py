import json
from urllib.parse import quote

from massactions.helpers import encrypt_string, get_selection_cookie_name


def make_selection_cookie(user, key, ids=(), select_all=False):
    payload = json.dumps({
        'ids': [str(pk) for pk in ids],
        'selectAll': select_all,
        'user': str(user.id),
        'currentFilter': '',
    })
    return get_selection_cookie_name(user.id, key), quote(encrypt_string(payload))


def set_selection(client, user, key, ids=(), select_all=False):
    name, value = make_selection_cookie(user, key, ids, select_all)
    client.cookies[name] = value
