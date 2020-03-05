# 数据库模型
from _md5 import md5
import jwt
from flask import url_for, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
import base64
from datetime import datetime, timedelta
import os


# 考虑到后续会创建 Post 等数据模型，所以在 app/models.py 中
# 设计一个通用类 PaginatedAPIMixin

class PaginatedAPIMixin(object):
    @staticmethod
    def to_collection_dict(query, page, per_page, endpoint, **kwargs):
        resources = query.paginate(page, per_page, False)
        data = {
            'items': [item.to_dict() for item in resources.items],
            '_meta': {
                'page': page,
                'per_page': per_page,
                'total_pages': resources.pages,
                'total_items': resources.total
            },
            '_links': {
                'self': url_for(endpoint, page=page, per_page=per_page,
                                **kwargs),
                'next': url_for(endpoint, page=page + 1, per_page=per_page,
                                **kwargs) if resources.has_next else None,
                'prev': url_for(endpoint, page=page - 1, per_page=per_page,
                                **kwargs) if resources.has_prev else None
            }
        }
        return data


#   代表左侧用户实体（即关注者/粉丝）已关注的右侧用户列表（即被关注者/大神们）
followers = db.Table('followers', db.Column('follower_id', db.Integer, db.ForeignKey('user.id')), db.Column('followed_id', db.Integer, db.ForeignKey('user.id')), db.Column('timestamp', db.DateTime, default=datetime.utcnow))

# 评论点赞
comments_likes = db.Table('comments_likes',
         db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
         db.Column('comment_id', db.Integer, db.ForeignKey('comments.id')),
         db.Column('timestamp', db.DateTime, default=datetime.utcnow))

class User(PaginatedAPIMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    # 加密后的密码
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)

    # 反向引用，直接查询出当前用户的所有博客文章; 同时，Post实例中会有 author 属性
    # dynamic 动态加载
    # cascade 用于级联删除，当删除user时，该user下面的所有posts都会被级联删除
    posts = db.relationship('Post', backref='author', lazy='dynamic', cascade='all, delete-orphan')

    # follwereds 该用户关注了那些用户      followers 粉丝列表
    followereds = db.relationship('User', secondary=followers,
                    primaryjoin=(followers.c.follower_id == id),
                    secondaryjoin=(followers.c.followed_id == id),
                    backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

    # 构建用户与评论的关系 级联删除操作
    comments = db.relationship('Comment', backref='author', lazy='dynamic', cascade='all, delete-orphan')

    # 增加token信息列 字段 5- 1.1 pyjwt
    # token = db.Column(db.String(32), index=True, unique=True)
    # token_expiration = db.Column(db.DateTime)

    # 使用Gravatar服务根据用户的 Email地址在线生成头像
    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        # ''.format() 插值表达式
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, size)

    # pyjwt 相关函数
    def get_jwt(self, expires_in=3600):
        now = datetime.utcnow()

        # 构建字典
        payload = {
            'user_id': self.id,
            'name': self.name if self.name else self.username,
            'user_avatar': base64.b64encode(self.avatar(24).encode('utf-8')).decode('utf-8'),
            'exp': now + timedelta(seconds=expires_in),
            'iat': now
        }
        return jwt.encode(
            payload,
            current_app.config['SECRET_KEY'],
            algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_jwt(token):
        try:
            payload = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256'])
        except (jwt.exceptions.ExpiredSignatureError, jwt.exceptions.InvalidSignatureError,
                jwt.exceptions.DecodeError) as e:
            # Token过期，或被人修改，那么签名验证也会失败
            return None

        return User.query.get(payload.get('user_id'))

    # 与 tonken 有关的函数  User 数据模型添加 token 3.1!!!
    def get_token(self, expires_in=3600):
        now = datetime.utcnow()
        if self.token and self.token_expiration > now + timedelta(seconds=60):
            return self.token
        self.token = base64.b64encode(os.urandom(24)).decode('utf-8')
        self.token_expiration = now + timedelta(seconds=expires_in)
        db.session.add(self)
        return self.token

    def revoke_token(self):
        self.token_expiration = datetime.utcnow() - timedelta(seconds=1)

    # 验证 tonken 函数
    @staticmethod
    def check_token(token):
        user = User.query.filter_by(token=token).first()
        if user is None or user.token_expiration < datetime.utcnow():
            return None
        return user

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self,password):
        self.password_hash = generate_password_hash(password)

    def check_password(self,password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self, include_email=False):
        data = {
            'id': self.id,
            'username': self.username,
            'name': self.name,
            'location': self.location,
            'about_me': self.about_me,
            'member_since': self.member_since.isoformat() + 'Z',
            'last_seen': self.last_seen.isoformat() + 'Z',
            '_links': {
                'self': url_for('api.get_user', id=self.id),
                'avatar': self.avatar(128)
            }
        }
        if include_email:
            data['email'] = self.email

        return data

    def from_dict(self, data, new_user=False):
        for filed in ['username', 'email', 'name', 'location', 'about_me']:
            if filed in data:
                setattr(self, filed, data[filed])

        if new_user and 'password' in data:
            self.set_password(data['password'])

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)


    # 与粉丝管理相关的函数
    # 利用布尔值 判断当前登录用户是否关注 这个 user (博主)
    def is_following(self, user):
        return self.followereds.filter(
            followers.c.followed_id == user.id).count() > 0

    # 当前登录用户开始关注 这个 user (博主)
    def follow(self, user):
        if not self.is_following(user):
            self.followereds.append(user)

    # 当前登录用户取消关注 这个 user (博主)
    def unfollow(self, user):
        if self.is_following(user):
            self.followereds.remove(user)

    # 获取当前用户所关注的所有博客列表
    @property
    def followed_posts(self):
        follwed = Post.query.join(followers, (followers.c.followed_id == Post.author_id)).filter(
            followers.c.follower_id == self.id)
        # 查询结果按照 降序排列
        return follwed.order_by(Post.timestamp.desc())

# 增加 Post 数据模型
class Post(PaginatedAPIMixin, db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    summary = db.Column(db.Text)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    views = db.Column(db.Integer, default=0)

    # 外键, 直接操纵数据库   当user下面有posts时不允许删除user，下面仅仅是 ORM-level “delete” cascade
    # db.ForeignKey('users.id', ondelete='CASCADE') 会同时在数据库中指定 FOREIGN KEY level “ON DELETE” cascade
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # 构建帖子与评论的关系 级联删除操作
    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self,):
        return '<Post {}>'.format(self.title)


    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):

        # 如果前端不填写摘要，是空str，而不是None
        if not target.summary:
            # 截取 body 字段的前200个字符给 summary
            target.summary = value[:200] + '  ... ...'


    def to_dict(self):
        data = {
            'id': self.id,
            'title': self.title,
            'summary': self.summary,
            'body': self.body,
            'timestamp': self.timestamp,
            'views': self.views,
            'author': self.author.to_dict(),
            '_links': {
                'self': url_for('api.get_post', id=self.id),
                'author_url': url_for('api.get_user', id=self.author_id)
            }
        }

        return data


    def from_dict(self, data):
        for field in ['title', 'summary', 'body']:
            if field in data:
                setattr(self, field, data[field])

# body 字段有变化时，执行 on_changed_body() 方法
db.event.listen(Post.body, 'set', Post.on_changed_body)

# 增加 Comment 评论数据模型
class Comment(PaginatedAPIMixin, db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    # 文章作者会收到评论提醒 ,利用布尔类型记录
    mark_read = db.Column(db.Boolean, default=False)
    disabled = db.Column(db.Boolean, default=False)
    # 评论与对它点赞的人是多对多关系
    likers = db.relationship('User', secondary=comments_likes, backref=db.backref('liked_comments', lazy='dynamic'))
    # 外键，评论作者的 id
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # 外键，post文章作者的 id
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    # 自引用的多级评论实现  CASCADE (cascade) 级联
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id', ondelete='CASCADE'))

    parent = db.relationship('Comment', backref=db.backref('children', cascade='all, delete-orphan'), remote_side=[id])

    def __repr__(self):
        return '<Comment {}>'.format(self.id)

    # 获取一级评论的所有用户
    def get_descendants(self):
        data = set()

        def descendants(comment):
            if comment.children:
                data.update(comment.children)
                for child in comment.children:
                    descendants(child)
        descendants(self)

        return data

    def to_dict(self):
        data = {
            'id': self.id,
            'body':self.body,
            'timestamp':self.timestamp,
            'mark_read': self.mark_read,
            'disabled': self.disabled,
            'likers_id': [user.id for user in self.likers],
            'author': {
                'id': self.author.id,
                'username': self.author.username,
                'name': self.author.name,
                'avatar': self.author.avatar(128)
            },
            'post': {
                'id': self.post.id,
                'title': self.post.title,
                'author_id': self.post.author.id
            },
            'parent_id': self.parent.id if self.parent else None,
            '_links': {
                'self': url_for('api.get_comment', id=self.id),
                'author_url': url_for('api.get_user', id=self.author_id),
                'post_url': url_for('api.get_post', id=self.post_id),
                'parent_url': url_for('api.get_comment', id=self.parent.id) if self.parent else None,
                'children_url': [url_for('api.get_comment', id=child.id) for child in self.children] if self.children else None
            }
        }

        return data

    def from_dict(self, data):
        for field in ['body', 'timestamp', 'mark_read', 'disabled', 'author_id', 'post_id', 'parent_id']:
            if field in data:
                setattr(self, field, data[field])

