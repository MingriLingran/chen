import nonebot
from nonebot import logger, require, on_command
from nonebot_plugin_apscheduler import scheduler
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import Bot
from ..feishu.查询用户 import 查询昨天的用户
from ..mcsm.command import 面板管理

require("nonebot_plugin_apscheduler")

config = nonebot.get_driver().config
group_id = getattr(config, "qq_group_id", None)  # 获取配置中的QQ群号

# 定义手动触发命令
add_whitelist = on_command("add_whitelist", aliases={"添加白名单", "添加全部白名单"}, priority=20,permission=SUPERUSER)

#@scheduler.scheduled_job("interval", seconds=30, id="auto_add_whitelist")
async def auto_add_whitelist():
    """
    自动定时执行添加白名单任务
    """
    logger.info("开始执行自动添加白名单定时任务")
    # 获取bot实例
    bots = nonebot.get_bots()
    if bots and group_id:
        # 获取第一个bot实例
        bot = list(bots.values())[0]
        await process_whitelist_addition(bot)
    else:
        if not bots:
            logger.error("未找到可用的bot实例")
        if not group_id:
            logger.error("未配置QQ群号，请在配置文件中添加 qq_group_id")

@add_whitelist.handle()
async def handle_add_whitelist_command(bot: Bot):
    """
    手动触发添加白名单命令
    """
    logger.info("收到手动添加白名单命令请求")
    if not group_id:
        await bot.send_msg(message_type="group", group_id=group_id, message="❌ 未配置QQ群号，请联系管理员")
        logger.error("未配置QQ群号，请在配置文件中添加 qq_group_id")
        return
    await process_whitelist_addition(bot)

async def process_whitelist_addition(bot):
    """
    处理白名单添加的核心逻辑
    """
    try:
        query = 查询昨天的用户()
        result = await query.获取昨日提交用户()
        logger.info(f"获取用户信息结果: {result}")
        if result and result.get("code") == 0:
            items = result.get("data", {}).get("items", [])
            logger.info(f"获取到 {len(items)} 个用户提交记录")
            if not items:
                logger.info("没有查询到任何提交记录")
                try:
                    if group_id:
                        await bot.send_group_msg(group_id=int(group_id), message="📭 昨日没有查询到任何提交记录。")
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"发送消息失败: {error_msg}")
                    # 检查是否是因为机器人不在群内
                    if "不是本群成员" in error_msg or "not in group" in error_msg.lower():
                        logger.error(f"机器人不在目标群组 {group_id} 内，请将机器人QQ号添加到群组中")
            else:
                response_text = "📋 昨日提交白名单申请的用户如下：\n\n"
                user_details = []
                for idx, item in enumerate(items, start=1):
                    fields = item.get("fields", {})
                    qq = fields.get("你的QQ号码", [{}])[0].get("text", "未知")
                    game_id = fields.get("你要申请白名单的游戏ID", [{}])[0].get(
                        "text", "未知"
                    )
                    score = (
                        fields.get("总分", {}).get("value", [0])[0]
                        if isinstance(fields.get("总分"), dict)
                        else "未知"
                    )
                    response_text += (
                        f"{idx}. QQ：{qq} | 游戏ID：{game_id} | 总分：{score}\n"
                    )
                    user_details.append({
                        "index": idx,
                        "qq": qq,
                        "game_id": game_id,
                        "score": score
                    })
                logger.info(f"用户详情: {user_details}")
                try:
                    if group_id:
                        await bot.send_group_msg(group_id=int(group_id), message=response_text)
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"发送用户列表消息失败: {error_msg}")
                    # 检查是否是因为机器人不在群内
                    if "不是本群成员" in error_msg or "not in group" in error_msg.lower():
                        logger.error(f"机器人不在目标群组 {group_id} 内，请将机器人QQ号添加到群组中")
                
                # 循环添加用户白名单
                logger.info("开始循环添加用户白名单")
                success_count = 0
                fail_count = 0
                success_users = []
                fail_users = []
                
                for item in items:
                    fields = item.get("fields", {})
                    qq = fields.get("你的QQ号码", [{}])[0].get("text", "")
                    game_id = fields.get("你要申请白名单的游戏ID", [{}])[0].get("text", "")
                    logger.info(f"正在处理用户 QQ:{qq}, GameID:{game_id}")
                    
                    if game_id:
                        try:
                            manager = 面板管理(f"whitelist add {game_id}")
                            result = manager.发送并获取日志()
                            logger.info(f"添加白名单成功，游戏ID: {game_id}, 返回结果: {result}")
                            success_count += 1
                            success_users.append({"qq": qq, "game_id": game_id})
                        except Exception as e:
                            logger.error(f"添加白名单失败，QQ: {qq}, 游戏ID: {game_id}, 错误: {str(e)}")
                            fail_count += 1
                            fail_users.append({"qq": qq, "game_id": game_id, "error": str(e)})
                    else:
                        logger.warning(f"用户 QQ:{qq} 的游戏ID为空，跳过添加白名单")
                        fail_count += 1
                        fail_users.append({"qq": qq, "game_id": "空", "error": "游戏ID为空"})
                
                # 发送添加结果
                result_message = f"✅ 白名单添加完成！成功: {success_count}个，失败: {fail_count}个"
                logger.info(f"白名单添加完成统计 - 成功: {success_count}, 失败: {fail_count}")
                logger.info(f"成功用户列表: {success_users}")
                logger.info(f"失败用户列表: {fail_users}")
                try:
                    if group_id:
                        await bot.send_group_msg(group_id=int(group_id), message=result_message)
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"发送结果消息失败: {error_msg}")
                    # 检查是否是因为机器人不在群内
                    if "不是本群成员" in error_msg or "not in group" in error_msg.lower():
                        logger.error(f"机器人不在目标群组 {group_id} 内，请将机器人QQ号添加到群组中")
        else:
            logger.warning(f"获取用户信息失败或无数据返回，结果: {result}")
            try:
                if group_id:
                    await bot.send_group_msg(group_id=int(group_id), message="❌ 获取用户信息失败或无数据返回。")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"发送失败消息失败: {error_msg}")
                # 检查是否是因为机器人不在群内
                if "不是本群成员" in error_msg or "not in group" in error_msg.lower():
                    logger.error(f"机器人不在目标群组 {group_id} 内，请将机器人QQ号添加到群组中")
    except Exception as e:
        # 异常处理（可选）
        logger.error(f"处理新成员时出错: {str(e)}", exc_info=True)
        try:
            if group_id:
                await bot.send_group_msg(
                    group_id=int(group_id),
                    message=f"处理新成员时发生错误：请尽快返回控制台查看"
                )
        except Exception as send_error:
            error_msg = str(send_error)
            logger.error(f"发送错误消息失败: {error_msg}")
            # 检查是否是因为机器人不在群内
            if "不是本群成员" in error_msg or "not in group" in error_msg.lower():
                logger.error(f"机器人不在目标群组 {group_id} 内，请将机器人QQ号添加到群组中")