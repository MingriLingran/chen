import nonebot
from nonebot import logger, on_notice, on_command
from nonebot.adapters.onebot.v11 import Bot, GroupIncreaseNoticeEvent
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import MessageEvent, Message
from nonebot.params import CommandArg
from .user_info import fetch_user_info

# 获取配置
config = nonebot.get_driver().config
# 获取用户检测功能开关，默认为 False
user_check_enabled = getattr(config, "user_check_enabled", False)

# 创建群成员增加事件处理器，指定只处理GroupIncreaseNoticeEvent事件
group_increase = on_notice(priority=10)

# 创建命令处理器，用于控制用户检测功能开关
user_check_switch = on_command("用户检测", priority=5, permission=SUPERUSER)

@user_check_switch.handle()
async def handle_user_check_switch(event: MessageEvent, arg: Message = CommandArg()):
    global user_check_enabled
    args = arg.extract_plain_text().strip()
    
    if args.lower() in ["开启", "启用", "enable", "on"]:
        user_check_enabled = True
        await user_check_switch.finish("用户检测功能已开启")
    elif args.lower() in ["关闭", "禁用", "disable", "off"]:
        user_check_enabled = False
        await user_check_switch.finish("用户检测功能已关闭")
    elif args.lower() in ["状态", "status", "state"]:
        status_text = "开启" if user_check_enabled else "关闭"
        await user_check_switch.finish(f"用户检测功能当前状态：{status_text}")
    else:
        await user_check_switch.finish("用法：\n用户检测 开启/关闭/状态\n例如：用户检测 开启")

@group_increase.handle()
async def handle_group_increase(bot: Bot, event: GroupIncreaseNoticeEvent):
    # 检查功能是否开启
    if not user_check_enabled:
        return
        
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
                message=f"新成员 [CQ:at,qq={user_id}] QQ等级({qq_level})≤5，已自动禁言30天"
            )
    except Exception as e:
        # 异常处理（可选）
        logger.error(f"处理新成员 {user_id} 时出错: {str(e)}")
        await bot.send_group_msg(
            group_id=group_id,
            message=f"处理新成员时发生错误：{str(e)}"
        )