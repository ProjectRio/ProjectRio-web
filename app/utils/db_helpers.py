from flask import abort
from sqlalchemy import select
from ..models import db


def resolve_names(values, id_col, name_col, label, *, transform):
    """Resolve a list of human-supplied names to their DB ids.

    All supplied values must resolve or the request is aborted (400).
    Duplicate / case-variant inputs that map to the same row are allowed:
    validation is done against the deduplicated set of normalized names.

    Returns a list of ids, one per matched row (order not guaranteed; callers
    feed this into .in_() clauses where order and duplicates are irrelevant).
    """
    if not values:
        return []
    normalized = [transform(v) for v in values]
    rows = db.session.execute(
        select(id_col, name_col).where(name_col.in_(normalized))
    ).all()
    found = {row._mapping[name_col] for row in rows}
    if len(found) != len(set(normalized)):
        unknown = [v for v in values if transform(v) not in found]
        abort(400, f'Unknown {label}: {unknown}')
    return [row._mapping[id_col] for row in rows]


def sanitize_int_list(int_list, error_msg, upper_bound, lower_bound=0):
    if not int_list:
        return [], ''
    try:
        for index, item in enumerate(int_list):
            sanitized_id = int(int_list[index])
            if sanitized_id in range(lower_bound, upper_bound):
                int_list[index] = sanitized_id
            else:
                return None, error_msg
        return int_list, ''
    except ValueError:
        return None, error_msg
