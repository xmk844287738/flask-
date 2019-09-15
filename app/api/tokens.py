from flask import jsonify, g
from app import db
from app.api import bp
from app.api.auth import basic_auth, token_auth


@bp.route('/tokens', methods=['POST'])
@basic_auth.login_required
def get_token():
    token = g.current_user.get_jwt()  #current_user 当前用的数据信息
    db.session.commit()
    return jsonify({'token': token})


# 撤销 Token  JWT 没办法回收（不需要 DELETE /tokens），只能等它过期，所以有效时间别设置太长 待解决
# @bp.route('/tokens', methods=['DELETE'])    #DELETE 请求
# @token_auth.login_required
# def revoke_token():
#     g.current_user.revoke_token()
#     db.session.commit()
#     return '', 204