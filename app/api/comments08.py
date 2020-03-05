# 用户评论
from flask import request, g, jsonify, url_for, current_app

from app import db
from app.api import bp
from app.api.auth import token_auth
from app.api.errors import bad_request, error_response
from app.models import Post, Comment


# 添加新评论 只有通过 Token 认证的用户才能添加新评论
@bp.route('/comments/', methods=['POST'])
@token_auth.login_required
def create_comment():
    data = request.get_json()
    if not data:
        return bad_request('You must post JSON data.')

    if 'body' not in data or not data.get('body').strip():
        return bad_request('Body is required.')
    if 'post_id' not in data or not data.get('post_id'):
        return bad_request('Post id is required.')

    post = Post.query.get_or_404(int(data.get('post_id')))
    comment = Comment()
    comment.from_dict(data)
    # 通过 auth.py 中 verify_token() 传递过来的（同一个request中，需要先进行 Token 认证）
    comment.author = g.current_user
    comment.post = post

    db.session.add(comment)
    db.session.commit()
    response = jsonify(comment.to_dict())
    response.status_code = 201
    # HTTP协议要求201响应包含一个值为新资源URL的Location头部
    response.headers['Location'] = url_for('api.get_comment', id=comment.id)

    return response



# 返回评论集合
@bp.route('/comments/', methods=['GET'])
# token_auth 登录验证
@token_auth.login_required
def get_comments():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', current_app.config['COMMENTS_PER_PAGE'], type=int), 100)
    data = Comment.to_collection_dict(Comment.query.order_by(Comment.timestamp.desc()), page, per_page, 'api.get_comments')
    return jsonify(data)



# 返回一个评论
@bp.route('/comments/<int:id>', methods=['GET'])  # 查询 文章 帖子的 id
@token_auth.login_required
def get_comment(id):
    comment = Comment.query.get_or_404(id)

    return jsonify(comment.to_dict())




# 修改一个评论
# 必须通过 Token 认证，而且他还必须是该博客文章的作者才允许修改
@bp.route('/comments/<int:id>', methods=['PUT'])
@token_auth.login_required
def update_comment(id):
    comment = Comment.query.get_or_404(id)
    if g.current_user != comment.author and g.current_user != comment.post.author:
        return error_response(403)

    # 以下操作与 添加文章的验证相同
    data = request.get_json()
    if not data:
        return bad_request('You must post JSON data.')

    # if 'body' not in data or not data.get('body'):
    #     return bad_request('Body is required.')

    comment.from_dict(data)
    db.session.commit()
    return jsonify(comment.to_dict())





# 删除一个评论
# 必须通过 Token 认证，而且他还必须是该博客文章的作者才允许删除
@bp.route('/comments/<int:id>', methods=['DELETE'])
@token_auth.login_required
def delete_comment(id):
    comment = Comment.query.get_or_404(id)
    # 验证当前用户
    if g.current_user != comment.author and g.current_user != comment.post.author:
        return error_response(403)

    db.session.delete(comment)
    db.session.commit()
    return '', 204


