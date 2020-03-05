# 用户文章
from flask import request, g, jsonify, url_for, current_app
from app import db
from app.api import bp
from app.api.auth import token_auth
from app.api.errors import bad_request, error_response
from app.models import Post, Comment


# 添加一篇文章 只有通过 Token 认证的用户才能发表文章
@bp.route('/posts', methods=['POST'])
@token_auth.login_required
def create_post():
    data = request.get_json()
    if not data:
        return bad_request('You must post JSON data.')
    message = {}
    if 'title' not in data or not data.get('title'):
        message['title'] = 'Title is required.'
    elif len(data.get('title')) > 255:
        message['title'] = 'Title must less than 255 characters.'
    if 'body' not in data or not data.get('body'):
        message['body'] = 'Body is required.'
    if message:
        return bad_request(message)

    post = Post()
    post.from_dict(data)
    post.author = g.current_user  # 通过 auth.py 中 verify_token() 传递过来的（同一个request中，需要先进行 Token 认证）
    db.session.add(post)
    db.session.commit()
    response = jsonify(post.to_dict())
    response.status_code = 201
    # HTTP协议要求201响应包含一个值为新资源URL的Location头部
    response.headers['Location'] = url_for('api.get_post', id=post.id)

    return response



# 返回文章集合
# 不需要认证，游客也能访问前端首页，显示博客列表
@bp.route('/posts', methods=['GET'])
def get_posts():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', current_app.config['POSTS_PER_PAGE'], type=int), 100)
    data = Post.to_collection_dict(Post.query.order_by(Post.timestamp.desc()), page, per_page, 'api.get_posts')
    return jsonify(data)



# 返回一篇文章
# 不需要认证，游客也能查看文章详情
@bp.route('/posts/<int:id>', methods=['GET'])  # 查询 文章 帖子的 id
def get_post(id):
    post = Post.query.get_or_404(id)
    post.views += 1
    db.session.add(post)
    db.session.commit()
    return jsonify(post.to_dict())




# 修改一篇文章
# 必须通过 Token 认证，而且他还必须是该博客文章的作者才允许修改
@bp.route('/posts/<int:id>', methods=['PUT'])
@token_auth.login_required
def update_post(id):
    post = Post.query.get_or_404(id)
    if g.current_user != post.author:
        return error_response(403)

    # 以下操作与 添加文章的验证相同
    data = request.get_json()
    if not data:
        return bad_request('You must post JSON data.')

    message = {}
    if 'title' not in data or not data.get('title'):
        message['title'] = 'Title is required.'
    elif len(data.get('title')) > 255:
        message['title'] = 'Title must less than 255 characters.'

    if 'body' not in data or not data.get('body'):
        message['body'] = 'Body is required.'

    if message:
        return message

    post.from_dict(data)
    db.session.commit()
    return jsonify(post.to_dict())





# 删除一篇文章
# 必须通过 Token 认证，而且他还必须是该博客文章的作者才允许删除
@bp.route('/posts/<int:id>', methods=['DELETE'])
@token_auth.login_required
def delete_post(id):
    post = Post.query.get_or_404(id)
    # 验证当前用户
    if g.current_user != post.author:
        return error_response(403)

    db.session.delete(post)
    db.session.commit()
    return '', 204

# 返回当前文章下面的一级评论
# 此处的  id 为 post的id  post_id
@bp.route('/posts/<int:id>/comments/', methods=['GET'])
def get_post_comments(id):
    '''返回当前文章下面的一级评论'''
    post = Post.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = min(
        request.args.get(
            'per_page', current_app.config['COMMENTS_PER_PAGE'], type=int), 100)
    # 先获取一级评论
    data = Comment.to_collection_dict(
        post.comments.filter(Comment.parent==None).order_by(Comment.timestamp.desc()), page, per_page,
        'api.get_post_comments', id=id)
    # 再添加子孙到一级评论的 descendants 属性上
    for item in data['items']:
        comment = Comment.query.get(item['id'])
        descendants = [child.to_dict() for child in comment.get_descendants()]
        # 按 timestamp 排序一个字典列表
        from operator import itemgetter
        item['descendants'] = sorted(descendants, key=itemgetter('timestamp'))
    return jsonify(data)