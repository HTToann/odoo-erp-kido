# utils/authz.py
from functools import wraps
from flask import abort
from flask_login import current_user


def roles_required(*roles):
    def deco(fn):
        @wraps(fn)
        def inner(*a, **kw):
            if not current_user.is_authenticated:
                abort(401)
            if not current_user.has_role(*roles):
                abort(403)
            return fn(*a, **kw)

        return inner

    return deco
