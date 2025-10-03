import nonebot
from nonebot.exception import IgnoredException
from nonebot.message import event_preprocessor
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot import logger

# 获取配置中的白名单群组ID列表
config = nonebot.get_driver().config
# 支持单个群组ID或者群组ID列表
whitelist_group_ids = getattr(config, "whitelist_group_ids", [])

# 如果是单个ID则转为列表
if whitelist_group_ids and not isinstance(whitelist_group_ids, list):
    whitelist_group_ids = [whitelist_group_ids]


def get_group_id_from_event(event):
    """
    从事件中提取群组ID
    """
    if hasattr(event, 'group_id'):
        return event.group_id
    return None


@event_preprocessor
async def group_whitelist_filter(event):
    """
    群组白名单过滤器
    只允许特定群组的消息通过，其他群组消息将被忽略
    """
    # 检查事件是否包含群组信息
    group_id = get_group_id_from_event(event)
    if group_id is None:
        # 如果事件不包含群组信息，则允许通过
        return
    
    # 如果没有配置白名单，则允许所有群组消息通过
    if not whitelist_group_ids:
        logger.debug("未配置白名单群组，允许所有群组消息通过")
        return
    
    # 检查群组ID是否在白名单中
    if group_id in whitelist_group_ids:
        logger.debug(f"群组 {group_id} 在白名单中，允许消息通过")
        return
    else:
        logger.debug(f"群组 {group_id} 不在白名单中，忽略该消息")
        # 抛出IgnoredException异常，使事件处理流程中断
        raise IgnoredException("群组不在白名单中")