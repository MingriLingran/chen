from nonebot import logger, on_notice
from nonebot.adapters.onebot.v11 import Bot, GroupIncreaseNoticeEvent
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.permission import SUPERUSER
from .user_info import fetch_user_info

# 创建群成员增加事件处理器，指定只处理GroupIncreaseNoticeEvent事件
group_increase = on_notice(priority=10)

@group_increase.handle()
async def handle_group_increase(bot: Bot, event: GroupIncreaseNoticeEvent):
    # 获取用户QQ号
    user_id = event.user_id
    group_id = event.group_id
    
    try:
        # 调用获取用户信息接口 (实际使用时需替换为真实API)
        user_info = await fetch_user_info(user_id)  # 使用await调用异步函数
        logger.debug(f"Fetched User Info: {user_info}")
        
        # 检查user_info是否为None
        if user_info is None:
            await bot.send_group_msg(
                group_id=group_id,
                message=f"无法获取新成员 [CQ:at,qq={user_id}] 的信息"
            )
            return
            
        # 提取QQ等级并转换为整数
        qq_level = int(user_info.get('QQLevel', '0'))
        logger.debug(f"User {user_id} QQ Level: {qq_level}")
        
        # 判断等级是否小于等于5
        if qq_level <= 5:
            # 执行禁言30天（2592000秒）
            await bot.set_group_ban(
                group_id=group_id,
                user_id=user_id,
                duration=2592000  # 30天秒数
            )
            await bot.send_group_msg(
                group_id=group_id,
                message=f"新成员 [CQ:at,qq={user_id}] QQ等级({qq_level})≤20，已自动禁言30天"
            )
    except Exception as e:
        # 异常处理（可选）
        logger.error(f"处理新成员 {user_id} 时出错: {str(e)}")
        await bot.send_group_msg(
            group_id=group_id,
            message=f"处理新成员时发生错误：{str(e)}"
        )