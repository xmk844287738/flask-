
from flask import Blueprint

bp = Blueprint('api', __name__)

# 防止循环导入
from app.api import ping, users, tokens, posts, comments