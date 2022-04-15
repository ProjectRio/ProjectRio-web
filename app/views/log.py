from flask import current_app as app
from flask import request

cLoggedEndpoints = ['endpoint_games', 'endpoint_detailed_stats']

@app.after_request
def after_request_func(response):
    print("LOG")
    print(request.endpoint)
    if (request.endpoint in cLoggedEndpoints):
        app.logger.info(f'Datatime: {response.date}  Endpoint: {request.endpoint}  RC: {response.status}  IP: {request.remote_addr}  Args: {request.args} ')
    return response