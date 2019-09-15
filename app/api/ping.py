from flask import jsonify

from app.api import bp

@bp.route('/ping', methods=['GET'])
def ping():
    return jsonify('pong')  #测试 前端Vue.js 8080端口与后端Flask API 5000 的连通性