import base64
from _md5 import md5
from datetime import datetime, timedelta
import os
import jwt
from flask import url_for, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app import db



# 用户集合转换成 JSON 通用类
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
                'self': url_for(endpoint, page=page, per_page=per_page,     #当前页数据
                                **kwargs),
                'next': url_for(endpoint, page=page + 1, per_page=per_page, #下一页数据
                                **kwargs) if resources.has_next else None,
                'prev': url_for(endpoint, page=page - 1, per_page=per_page, #上一页数据
                                **kwargs) if resources.has_prev else None
            }
        }
        return data



# User 用户模型
class User(PaginatedAPIMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)    #用户主键ID
    username = db.Column(db.String(64), index=True, unique=True)    #用户名
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))  # 不保存原始密码,加密存储
    # 为用户模型增加 token字段
    # token = db.Column(db.String(32), index=True, unique=True)
    # token_expiration = db.Column(db.DateTime)   # 增加 token发布的时间字段
    name = db.Column(db.String(64))     #为User用户模型添加新的字段
    location = db.Column(db.String(64))     #位置信息
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)    #何时注册
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)   #最后一次登录的时间

    # 反向引用，直接查询出当前用户的所有博客文章; 同时，Post实例中会有 author 属性
    # cascade 用于级联删除，当删除user时，该user下面的所有posts都会被级联删除
    posts = db.relationship('Post', backref='author', lazy='dynamic',
                            cascade='all, delete-orphan')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    # # 与 token 字段有关的方法函数 [start]
    # def get_token(self, expires_in=3600):
    #     now = datetime.utcnow()
    #     if self.token and self.token_expiration > now + timedelta(seconds=60):
    #         return self.token
    #     self.token = base64.b64encode(os.urandom(24)).decode('utf-8')
    #     self.token_expiration = now + timedelta(seconds=expires_in)
    #     db.session.add(self)
    #     return self.token
    #
    # def revoke_token(self):
    #     self.token_expiration = datetime.utcnow() - timedelta(seconds=1)
    #
    # @staticmethod
    # def check_token(token):     # 与 token 字段有关的方法函数 [end]
    #     user = User.query.filter_by(token=token).first()
    #     if user is None or user.token_expiration < datetime.utcnow():
    #         return None
    #     return user


    def get_jwt(self, expires_in=600):
        now = datetime.utcnow()
        payload = {
            'user_id': self.id,
            'name': self.name if self.name else self.username,
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
        except (jwt.exceptions.ExpiredSignatureError, jwt.exceptions.InvalidSignatureError) as e:
            # Token过期，或被人修改，那么签名验证也会失败
            return None
        return User.query.get(payload.get('user_id'))


# 设置hash密码的方法函数
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    # 检验hash密码的方法函数
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # 定义 to_dict 方法将用户对象转为JSON
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
        if include_email:       # 当用户请求自己的数据时包含 email 时,data JSON对象增加email值
            data['email'] = self.email
        return data

# 将前端发送过来 JSON 对象，转换成 User 对象
    def from_dict(self, data, new_user=False):
        for field in ['username', 'email', 'name', 'location', 'about_me']:
            if field in data:
                setattr(self, field, data[field])
        if new_user and 'password' in data:
            self.set_password(data['password'])

    # 为User数据模型增加一个方法,根据用户的Email地址在线生成头像
    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, size)



#增加 Post 数据模型
class Post(PaginatedAPIMixin, db.Model):
    __tablename__ = 'posts'
    #为Post 模型增加 7个字段(1个外键字段)
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    summary = db.Column(db.Text)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    views = db.Column(db.Integer, default=0)

    # 外键, 直接操纵数据库当user下面有posts时不允许删除user，下面仅仅是 ORM-level “delete” cascade
    # db.ForeignKey('users.id', ondelete='CASCADE') 会同时在数据库中指定 FOREIGN KEY level “ON DELETE” cascade
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))     #ForeignKey 外键

    def __repr__(self):
        return '<Post {}>'.format(self.title)









#1.创建迁移存储库
# flask db init
#2.生成迁移脚本
#flask db migrate -m "add users table"
#3.将迁移脚本应用到数据库中
#flask db upgrade

# 添加用户步骤
# 1.flask shell     进入数据添加模式
# 2.u=User(username="",email="")
# 3.u.set_password("")
# 4.db.session.add(u)
# 5.db.session.commit()
# 6.exit() 退出数据添加模式


# 为模型做完添加字段工作需要及时对数据库迁移工作!!!!!  字段数据的升级

# 为User模型添加 token相关字段做好数据库迁移脚本并应用
# 1.flask db migrate -m "user add tokens"
# 2.flask db upgrade