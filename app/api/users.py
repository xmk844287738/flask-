import re

from app import db
from app.api.auth import token_auth
from app.models import User, Post, Comment
from flask import request, jsonify, url_for, g, current_app
from app.api import bp
from app.api.errors import bad_request, error_response
from datetime import datetime



# 注册新用户
@bp.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    if not data:
        # 返回错误消息
        return bad_request('You must post JSON data.')

    # 定义一个信息字典
    message = {}

    # 验证用户名
    if 'username' not in data or not data.get('username', None):
        message['username'] = 'Please provide a valid username.'

    # 验证邮箱地址
    pattern = '^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$'
    if 'email' not in data or not re.match(pattern, data.get('email', None)):
        message['email'] = 'Please provide a valid email address.'

    # 验证密码
    if 'password' not in data or not data.get('password',None):
        message['password'] = 'Please provide a valid password.'


    # 与数据库中的现有用户名进行比较
    if User.query.filter_by(username = data.get('username',None)).first():
        message['username'] = 'Please use a different username.'
        # message['username'] = '该用户名已被占用,请更换其他不同的名字!'


    # 与数据库中的用户邮箱进行比较
    if User.query.filter_by(email=data.get('email', None)).first():
        message['email'] = 'Please use a different email addres.'

    if message:
        return bad_request(message)


    user = User()
    user.from_dict(data, new_user=True)
    db.session.add(user)
    db.session.commit()
    response = jsonify(user.to_dict())
    response.status_code = 201

    # HTTP协议要求201响应包含一个值为新资源URL的Location头部
    response.headers['Location'] = url_for('api.get_user', id=user.id)
    return response



# 除 create_user() 之外的所有 API 视图函数需要添加 @token_auth.login_required 装饰器
# 返回所有用户的集合,分页
@bp.route('/users', methods=['GET'])
@token_auth.login_required
def get_users():
    page = request.args.get('page', current_app.config['USERS_PER_PAGE'], type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    data = User.to_collection_dict(User.query, page, per_page, 'api.get_users')
    return jsonify(data)


# 返回一个用户
@bp.route('/users/<int:id>', methods=['GET'])
@token_auth.login_required
# 此处的id => 当前个人主页的id
def get_user(id):
    # 更新数据库用户最后浏览个人主页的时间
    user = User.query.get_or_404(id)
    # now = g.current_user  当前登录用户
    # 判断当前登录用户 是否 与 当前个人主页的id 是否相同，相同 则刷新最后浏览个人主页的时间
    # (否则则属于浏览其他的 用户个人主页，不能进行刷新 最后浏览个人主页的时间 的动作)
    # 与User的ping()方法 类似 对应设置在 auth.py 下的 g.current_user.ping() 二者取其一
    if g.current_user == user:
        user.last_seen = datetime.utcnow()
        db.session.add(user)
        db.session.commit()
        return jsonify(user.to_dict(include_email=True))

    # 如果当前用户是查询其它用户，添加 是否已关注过该用户 的标志位
    data = user.to_dict()
    data['is_following'] = g.current_user.is_following(user)

    return jsonify(data)






# 修改一个用户
@bp.route('/users/<int:id>', methods=['PUT'])
def update_user(id):
    user = User.query.get_or_404(id)
    data = request.get_json()
    if not data:
        # 除id外 如果没有输入其他要修改的内容，返回错误信息
        return bad_request('You must post JSON data.')

    # 定义一个信息字典
    message = {}

    # 验证用户名
    if 'username' in data and not data.get('username', None):
        message['username'] = 'Please provide a valid username.'

    pattern = '^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$'
    if 'email' in data and not re.match(pattern, data.get('email', None)):
        message['email'] = 'Please provide a valid email address.'

    if 'username' in data and data['username'] != user.username and \
            User.query.filter_by(username=data['username']).first():
        message['username'] = 'Please use a different username.'
    if 'email' in data and data['email'] != user.email and \
            User.query.filter_by(email=data['email']).first():
        message['email'] = 'Please use a different email address.'

    if message:
        return bad_request(message)

    user.from_dict(data, new_user=False)
    db.session.commit()
    return jsonify(user.to_dict())


# 删除一个用户
@bp.route('/users/<int:id>', methods=['DELETE'])
def delete_user():
    pass


# 关注用户
@bp.route('/follow/<int:id>', methods=['GET'])
@token_auth.login_required
def follow(id):
    user = User.query.get_or_404(id)
    # 判断当前登录用户的 id 是否 与此时的 个人主页的id 一致
    if g.current_user == user:
        return bad_request('You cannot follow yourself.')

    # 判断当前登录用户的 是否已经关注了此 博主（作者）
    if g.current_user.is_following(user):
        return bad_request('You have already followed that user.')

    # 以上验证都通过,则可以执行关注此作者的动作
    g.current_user.follow(user)
    # 提交并更新 数据库记录
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': 'You are now following %d.' % id
    })


# 取消关注用户
@bp.route('/unfollow/<int:id>', methods=['GET'])
@token_auth.login_required
def unfollow(id):
    user = User.query.get_or_404(id)
    # 判断当前登录用户的 id 是否 与此时的 个人主页的id 一致
    if g.current_user == user:
        return bad_request("You cannot follow yourself.")

    # 判断当前登录用户的 是否已经关注了此 博主（作者）
    if not g.current_user.is_following(user):
        return bad_request("'You are not following this user.")
    # 以上验证都通过,则可以执行关注此作者的动作
    g.current_user.unfollow(user)
    # 提交并更新 数据库记录
    db.session.commit()

    return jsonify({
        'status': 'suceess',
        'message': 'You are not following %d anymore.' % id
    })


# 当前用户所关注的博主
@bp.route('/users/<int:id>/followeds/', methods=['GET'])
@token_auth.login_required
def get_followeds(id):
    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', current_app.config['USERS_PER_PAGE'], type=int),100)

    data = User.to_collection_dict(user.followereds, page, per_page, 'api.get_followeds', id=id)

    for item in data['items']:
        item['is_following'] = g.current_user.is_following(User.query.get(item['id']))

        # 获取当前用户开始关注该博主的时间
        res = db.engine.execute("select * from followers where follower_id={} and  followed_id={}".format(user.id, item['id']))
        item['timestamp'] = datetime.strptime(list(res)[0][2], '%Y-%m-%d %H:%M:%S.%f')

    return jsonify(data)

# 该作者(博主)所拥有的粉丝 （作者也是该网站的用户）
@bp.route('/users/<int:id>/followers/', methods=['GET'])
@token_auth.login_required
def get_followers(id):
    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', current_app.config['USERS_PER_PAGE'], type=int), 100)
    data = User.to_collection_dict(user.followers, page, per_page, 'api.get_followers', id=id)

    for item in data['items']:
        item['is_following'] = g.current_user.is_following(User.query.get(item['id']))

        # 获取 follower 开始关注该作者的时间
        res = db.engine.execute("select * from followers where follower_id={} and followed_id={}".format(item['id'], user.id))
        item['timestamp'] = datetime.strptime(list(res)[0][2], '%Y-%m-%d %H:%M:%S.%f')

    return jsonify(data)

# 返回该用户的所有文章文章列表
@bp.route('/users/<int:id>/posts', methods=['GET'])
@token_auth.login_required
def get_user_posts(id):
    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', current_app.config['POSTS_PER_PAGE'], type=int), 100)
    data = Post.to_collection_dict(user.posts.order_by(Post.timestamp.desc()), page, per_page, 'api.get_user_posts', id=id)

    return jsonify(data)

@bp.route('/users/<int:id>/followeds-posts/', methods=['GET'])
def get_user_followeds_posts(id):
    user = User.query.get_or_404(id)
    if g.current_user != user:
        return error_response(403)
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', current_app.config['POSTS_PER_PAGE'], type=int), 100)
    data = Post.to_collection_dict(user.followed_posts.order_by(Post.timestamp.desc()), page, per_page, 'api.get_user_followeds_posts', id=id)
    return jsonify(data)

# 返回该用户发表过的所有评论列表
@bp.route('/users/<int:id>/comments/', methods=['GET'])
@token_auth.login_required
def get_user_comments(id):
    user = User.query.get_or_404(id)
    # 判断当前用户
    if g.current_user != user:
        return error_response(403)

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', current_app.config['COMMENTS_PER_PAGE'], type=int), 100)
    data = Comment.to_collection_dict(user.comments.order_by(Comment.timestamp.desc()), page, per_page, 'api.get_user_comments', id=id)

    return jsonify(data)

# 返回该用户收到的评论
@bp.route('/users/<int:id>/recived-comments/', methods=['GET'])
@token_auth.login_required
def get_user_recived_comments(id):
    user = User.query.get_or_404(id)
    # 判断当前用户
    if g.current_user != user:
        return error_response(403)

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', current_app.config['COMMENTS_PER_PAGE'], type=int), 100)
    user_posts_ids = [post.id for post in g.current_user.posts.all()]
    data = Comment.to_collection_dict(
        Comment.query.filter(Comment.post_id.in_(user_posts_ids), Comment.author != g.current_user)
        .order_by(Comment.mark_read, Comment.timestamp.desc()), page, per_page, 'api.get_user_recived_comments', id=id)

    return jsonify(data)