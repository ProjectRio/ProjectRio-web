from flask import current_app as app
from flask import request
from datetime import datetime

cLoggedEndpoints       = ['endpoint_games', 'endpoint_detailed_stats', 'user_stats', 
                          'endpoint_batter_position', 'verify_email', 'request_password_change', 'key']
cLoggedEndpointsNoArgs = ['register', 'change_password', 'login']

@app.after_request
def after_request_func(response):    
    now = datetime.now()
    # dd/mm/YY H:M:S
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    
    #If HTTP request was not successful for any reason log a warning
    if (response.status_code >= 300):
        app.logger.warning(f'WARNING Datatime: {dt_string}  Endpoint: {request.endpoint}  RC: {response.status}  IP: {request.remote_addr} ')
    elif (request.endpoint in cLoggedEndpoints):
        app.logger.info(f'INFO    Datatime: {dt_string}  Endpoint: {request.endpoint}  RC: {response.status}  IP: {request.remote_addr}  Args: {request.args} ')
    elif (request.endpoint in cLoggedEndpointsNoArgs):
        app.logger.info(f' INFO    Datatime: {dt_string}  Endpoint: {request.endpoint}  RC: {response.status}  IP: {request.remote_addr} ')
    return response