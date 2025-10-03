from nonebot import require

# 加载群组白名单装饰器
from . import group_whitelist

# 确保其他插件模块被加载
from . import user_info
from . import 用户检测
from . import 自动删除白名单
from . import 自动添加白名单

__all__ = [
    "group_whitelist",
    "user_info",
    "用户检测",
    "自动删除白名单",
    "自动添加白名单",
]