
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from config import Config

# 调用 flask_sqlalchemy 插件
db = SQLAlchemy()
# flask_Migrate 插件
migrate = Migrate()


def create_app(config_class = Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.url_map.strict_slashes = False

    # 开启 CORS 跨域访问
    CORS(app)

    # 初始化 flask_sqlalchemy
    db.init_app(app)
    # 初始化 flask_Migrate
    migrate.init_app(app, db)


    # 注册 blueprint
    from app.api import bp as api_bi
    app.register_blueprint(api_bi, url_prefix='/api')

    return app


from app import models