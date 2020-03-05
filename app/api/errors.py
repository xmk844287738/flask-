# 错误处理
from flask import jsonify
from werkzeug.http import HTTP_STATUS_CODES

from app.api import bp


def error_response(status_code, message=None):
    # 字典形式
    payload = {'error':HTTP_STATUS_CODES.get(status_code, 'Unknown error')}
    if message:
        payload['message'] = message

    response = jsonify(payload)
    response.status_code = status_code

    return response

# 最常见的错误 400：错误的请求
def bad_request(message):
    return error_response(400,message)


@bp.app_errorhandler(404)
def not_found_error(error):
    return error_response(404)

@bp.errorhandler(500)
def internal_error(error):
    return error_response(500)