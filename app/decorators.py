from flask import abort, request
from .models import db, RioUser, UserGroupUser, UserGroup, ApiKey
from functools import wraps
import time

'''
Accepts an array of UserGroups who have permission to use this endpoint
'''
def api_key_check(acceptable_user_groups):
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            print(acceptable_user_groups)
            # Check if api_key is provided
            in_api_key = request.args.get('api_key')
            if not in_api_key:
                abort(409, 'No api_key provided')

            # Check if valid Api Key
            api_key = ApiKey.query.filter_by(api_key=in_api_key).first()
            if not api_key:
                abort(409, "Invalid api_key")
            
            # Check if valid RioUser connected to this ApiKey
            rio_user = RioUser.query.filter_by(api_key_id=api_key.id).first()
            if not rio_user:
                abort(409, 'No matching user')

            # Check if RioUser has correct group privledge
            user_groups = db.session.query(
                UserGroup.name
            ).join(
                UserGroupUser
            ).join(
                RioUser
            ).filter(
                RioUser.id == rio_user.id
            )
            
            for group in user_groups:
                if group.name in acceptable_user_groups:
                    api_key.total_pings += 1
                    api_key.pings_daily += 1
                    api_key.pings_weekly += 1
                    api_key.last_ping_date = int(time.time())
                    db.session.add(api_key)
                    db.session.commit()

                    func(*args, **kwargs)
                    return
            return abort(409, 'You do not have valid permissions to use this endpoint.')
        return decorated_function
    return decorator