from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from config import Config
# CORS跨域访问包
from flask_cors import CORS




# Flask-SQLAlchemy plugin
db = SQLAlchemy()
# # Flask-Migrate plugin
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

# 跨域请求,开启CORS
    CORS(app)

    # Init Flask-SQLAlchemy
    db.init_app(app)
    # Init Flask-Migrate
    migrate.init_app(app, db)

#导入数据库模型
    from app import models

    # 注册 blueprint
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
# 返回对象集
    return app