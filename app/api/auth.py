

from flask import g
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
from app import db
from app.models import User
from app.api.errors import error_response





basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth()

# 用于验证用户请求是否有token，并且token真实存在，还在有效期内
@token_auth.verify_token
def verify_token(token):
    g.current_user = User.verify_jwt(token) if token else None

    if g.current_user:
        # 每次认证通过后（即将访问资源API），调用User的ping()方法 更新 last_seen  时间； 与user文件下的get_user（id）方法类似 二者取其一
        # g.current_user.ping()
        db.session.commit()

    return g.current_user is not None

# Token Auth 认证失败的情况下返回错误响应
@token_auth.error_handler
def token_auth_error():
    return error_response(401)


# 验证用户的用户名和密码
@basic_auth.verify_password
def verify_password(username, password):
    user = User.query.filter_by(username=username).first()
    if user is None:
        return False
    g.current_user = user
    return user.check_password(password)

# 验证失败返回错误相遇代码
@basic_auth.error_handler
def basic_auth_error():
    return error_response(401)


