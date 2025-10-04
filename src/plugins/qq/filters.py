"""
白名单数据过滤器模块
提供各种数据过滤和验证功能
"""

import re
from nonebot import logger


def is_valid_user_data(item):
    """
    验证用户数据是否有效
    
    Args:
        item (dict): 用户数据项
        
    Returns:
        bool: 数据是否有效
    """
    if not item or not isinstance(item, dict):
        return False
        
    fields = item.get("fields", {})
    qq = fields.get("QQ号码", [{}])[0].get("text", "")
    game_id = fields.get("游戏ID", [{}])[0].get("text", "")
    
    # 只有当QQ号和游戏ID都不为空时，才认为是有效数据
    return qq.strip() and game_id.strip()


def extract_user_info(item):
    """
    从用户数据项中提取用户信息
    
    Args:
        item (dict): 用户数据项
        
    Returns:
        dict: 包含qq、game_id和score的字典，如果提取失败则返回None
    """
    if not item or not isinstance(item, dict):
        return None
        
    fields = item.get("fields", {})
    qq = fields.get("QQ号码", [{}])[0].get("text", "")
    game_id = fields.get("游戏ID", [{}])[0].get("text", "")
    score = (
        fields.get("总分", {}).get("value", [0])[0]
        if isinstance(fields.get("总分"), dict)
        else "未知"
    )
    
    return {
        "qq": qq,
        "game_id": game_id,
        "score": score
    }


def filter_valid_users(items):
    """
    过滤出有效的用户数据（基础验证）
    
    Args:
        items (list): 用户数据列表
        
    Returns:
        list: 有效用户数据列表
    """
    valid_items = []
    invalid_items_count = 0
    
    for idx, item in enumerate(items):
        logger.debug(f"处理第 {idx+1} 条用户数据: {item}")
        if is_valid_user_data(item):
            valid_items.append(item)
            logger.debug(f"第 {idx+1} 条数据有效，已添加到有效数据列表")
        else:
            invalid_items_count += 1
            logger.debug(f"第 {idx+1} 条数据无效，QQ或游戏ID为空，已跳过")
    
    logger.info(f"过滤后得到 {len(valid_items)} 个有效用户提交记录，{invalid_items_count} 个无效记录被过滤")
    logger.debug(f"有效用户数据详情: {valid_items}")
    return valid_items


def filter_duplicate_game_ids(items):
    """
    游戏ID相同时过滤仅保留最新的记录
    
    Args:
        items (list): 用户数据列表
        
    Returns:
        list: 去重后的用户数据列表
    """
    game_id_map = {}  # {game_id: (timestamp, item)}
    
    for item in items:
        fields = item.get("fields", {})
        game_id = fields.get("游戏ID", [{}])[0].get("text", "")
        timestamp = item.get("created_time", 0)  # 使用记录创建时间
        
        if not game_id:
            continue
            
        # 如果游戏ID已存在，且当前记录更新，则替换
        if game_id in game_id_map:
            if timestamp > game_id_map[game_id][0]:
                game_id_map[game_id] = (timestamp, item)
                logger.debug(f"游戏ID {game_id} 发现更新记录，已替换")
        else:
            game_id_map[game_id] = (timestamp, item)
            logger.debug(f"游戏ID {game_id} 首次记录")
    
    # 提取去重后的记录
    filtered_items = [item for _, (_, item) in game_id_map.items()]
    logger.info(f"游戏ID去重后剩余 {len(filtered_items)} 条记录，过滤掉 {len(items) - len(filtered_items)} 条重复记录")
    return filtered_items


def filter_duplicate_qq_numbers(items):
    """
    QQ号相同时过滤仅保留最新的记录
    
    Args:
        items (list): 用户数据列表
        
    Returns:
        list: 去重后的用户数据列表
    """
    qq_map = {}  # {qq: (timestamp, item)}
    
    for item in items:
        fields = item.get("fields", {})
        qq = fields.get("QQ号码", [{}])[0].get("text", "")
        timestamp = item.get("created_time", 0)  # 使用记录创建时间
        
        if not qq:
            continue
            
        # 如果QQ号已存在，且当前记录更新，则替换
        if qq in qq_map:
            if timestamp > qq_map[qq][0]:
                qq_map[qq] = (timestamp, item)
                logger.debug(f"QQ号 {qq} 发现更新记录，已替换")
        else:
            qq_map[qq] = (timestamp, item)
            logger.debug(f"QQ号 {qq} 首次记录")
    
    # 提取去重后的记录
    filtered_items = [item for _, (_, item) in qq_map.items()]
    logger.info(f"QQ号去重后剩余 {len(filtered_items)} 条记录，过滤掉 {len(items) - len(filtered_items)} 条重复记录")
    return filtered_items


def filter_invalid_game_ids(items):
    """
    过滤不符合正则表达式 ^[0-9a-zA-Z_]{3,16}$ 的游戏ID
    
    Args:
        items (list): 用户数据列表
        
    Returns:
        list: 格式验证通过的用户数据列表
    """
    valid_items = []
    invalid_items_count = 0
    pattern = re.compile(r"^[0-9a-zA-Z_]{3,16}$")
    
    for idx, item in enumerate(items):
        fields = item.get("fields", {})
        game_id = fields.get("游戏ID", [{}])[0].get("text", "")
        
        if pattern.match(game_id):
            valid_items.append(item)
            logger.debug(f"第 {idx+1} 条数据的游戏ID {game_id} 符合规范")
        else:
            invalid_items_count += 1
            logger.debug(f"第 {idx+1} 条数据的游戏ID {game_id} 不符合规范，已过滤")
    
    logger.info(f"游戏ID格式验证后剩余 {len(valid_items)} 条记录，过滤掉 {invalid_items_count} 条格式不正确的记录")
    return valid_items


def apply_filters(items):
    """
    应用所有过滤器到用户数据
    
    Args:
        items (list): 原始用户数据列表
        
    Returns:
        list: 经过所有过滤器处理后的用户数据列表
    """
    logger.info(f"开始对 {len(items)} 条用户数据应用过滤器")
    
    # 1. 基础有效性过滤
    valid_items = filter_valid_users(items)
    if not valid_items:
        return []
    
    # 2. 游戏ID格式过滤
    valid_items = filter_invalid_game_ids(valid_items)
    if not valid_items:
        return []
    
    # 3. 游戏ID重复过滤（保留最新）
    valid_items = filter_duplicate_game_ids(valid_items)
    if not valid_items:
        return []
    
    # 4. QQ号重复过滤（保留最新）
    valid_items = filter_duplicate_qq_numbers(valid_items)
    
    logger.info(f"所有过滤器应用完成，最终剩余 {len(valid_items)} 条有效记录")
    return valid_items