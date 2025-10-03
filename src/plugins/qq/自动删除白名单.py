import nonebot
from nonebot import logger, on_notice
from nonebot.adapters.onebot.v11 import Bot, GroupDecreaseNoticeEvent
from ..feishu.查询用户 import 查询昨天的用户
from ..mcsm.command import 面板管理

config = nonebot.get_driver().config
group_id = getattr(config, "qq_group_id", None)  # 获取配置中的QQ群号

# 创建退群事件监听器
group_decrease = on_notice(priority=10)

@group_decrease.handle()
async def handle_group_decrease(bot: Bot, event: GroupDecreaseNoticeEvent):
    """
    处理群成员减少事件（退群/被踢）
    """
    # 获取退群用户QQ号和群号
    user_id = event.user_id
    group_id_event = event.group_id
    
    logger.info(f"检测到用户退群事件: 用户QQ={user_id}, 群号={group_id_event}")
    
    # 只处理配置中指定的群
    if group_id and str(group_id_event) == str(group_id):
        logger.info(f"开始处理退群用户 {user_id} 的白名单删除操作")
        await process_whitelist_removal(bot, user_id)
    else:
        logger.debug(f"退群事件不在目标群内，目标群号: {group_id}, 事件群号: {group_id_event}")

async def process_whitelist_removal(bot: Bot, user_id: int):
    """
    处理白名单删除的核心逻辑
    """
    try:
        logger.info(f"开始查询退群用户 {user_id} 的白名单信息")
        query = 查询昨天的用户()
        # 使用新的根据QQ号精确查询的方法
        result = await query.根据QQ号查询用户(str(user_id))
        
        logger.debug(f"获取用户信息结果: {result}")
        
        if result and result.get("code") == 0:
            items = result.get("data", {}).get("items", [])
            logger.info(f"从飞书表格查询到 {len(items)} 条用户记录")
            
            if items:
                # 获取第一个匹配的用户记录（正常情况下一个QQ号只会有一条记录）
                target_item = items[0]
                fields = target_item.get("fields", {})
                game_id = fields.get("游戏ID", [{}])[0].get("text", "")
                
                if game_id:
                    logger.info(f"准备删除用户 {user_id} 的白名单，游戏ID: {game_id}")
                    
                    try:
                        # 删除白名单
                        manager = 面板管理(f"multilogin whitelist remove {game_id}")
                        result = manager.发送并获取日志()
                        
                        logger.info(f"成功删除用户 {user_id} 的白名单，游戏ID: {game_id}")
                        logger.debug(f"删除操作返回结果: {result}")
                        
                        # 发送通知消息到群
                        if group_id:
                            await bot.send_group_msg(
                                group_id=int(group_id),
                                message=f"✅ 检测到用户 {user_id} 退群，已自动删除其白名单 (游戏ID: {game_id})"
                            )
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"删除白名单失败: {error_msg}", exc_info=True)
                        
                        # 发送错误消息到群
                        if group_id:
                            await bot.send_group_msg(
                                group_id=int(group_id),
                                message=f"❌ 删除退群用户 {user_id} 的白名单时出错: {error_msg}"
                            )
                else:
                    logger.warning(f"用户 {user_id} 的游戏ID为空，无法删除白名单")
                    if group_id:
                        await bot.send_group_msg(
                            group_id=int(group_id),
                            message=f"⚠️ 检测到用户 {user_id} 退群，但未找到其游戏ID，无法删除白名单"
                        )
            else:
                logger.info(f"退群用户 {user_id} 未在白名单申请记录中找到")
                if group_id:
                    await bot.send_group_msg(
                        group_id=int(group_id),
                        message=f"ℹ️ 检测到用户 {user_id} 退群，该用户未在白名单申请记录中"
                    )
        else:
            logger.warning(f"获取飞书表格数据失败或无数据返回，结果: {result}")
            if group_id:
                await bot.send_group_msg(
                    group_id=int(group_id),
                    message=f"❌ 获取白名单数据失败，无法处理退群用户 {user_id} 的白名单删除"
                )
    except Exception as e:
        logger.error(f"处理退群用户 {user_id} 的白名单删除时出错: {str(e)}", exc_info=True)
        if group_id:
            await bot.send_group_msg(
                group_id=int(group_id),
                message=f"❌ 处理退群用户 {user_id} 的白名单删除时发生错误，请查看日志"
            )