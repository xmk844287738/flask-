import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))    #当前文件的绝对路径
load_dotenv(os.path.join(basedir, '.env'))

# 默认使用 SQLite 数据库
class Config(object):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'