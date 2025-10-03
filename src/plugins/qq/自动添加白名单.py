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

# @scheduler.scheduled_job("cron", hour=10, minute=0, id="auto_add_whitelist")
async def auto_add_whitelist():
    """
    自动定时执行添加白名单任务
    """
    logger.info("开始执行自动添加白名单定时任务")
    logger.debug(f"当前配置信息: group_id={group_id}")
    # 获取bot实例
    bots = nonebot.get_bots()
    logger.debug(f"获取到的bots实例: {bots}")
    if bots and group_id:
        # 获取第一个bot实例
        bot = list(bots.values())[0]
        logger.debug(f"选择使用的bot实例: {bot}")
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
    logger.debug(f"当前配置信息: group_id={group_id}")
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
        logger.info("开始处理白名单添加逻辑")
        query = 查询昨天的用户()
        logger.debug("初始化查询昨天的用户实例完成")
        result = await query.获取昨日提交用户()
        logger.info(f"获取用户信息结果: {result}")
        logger.debug(f"获取用户信息结果详情: {type(result)}, {len(result) if isinstance(result, dict) else 'N/A'}")
        if result and result.get("code") == 0:
            items = result.get("data", {}).get("items", [])
            logger.info(f"获取到 {len(items)} 个用户提交记录")
            logger.debug(f"原始用户数据详情: {items}")
            if not items:
                logger.info("没有查询到任何提交记录")
                try:
                    if group_id:
                        await bot.send_group_msg(group_id=int(group_id), message="📭 昨日没有查询到任何提交记录。")
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"发送消息失败: {error_msg}", exc_info=True)
                    # 检查是否是因为机器人不在群内
                    if "不是本群成员" in error_msg or "not in group" in error_msg.lower():
                        logger.error(f"机器人不在目标群组 {group_id} 内，请将机器人QQ号添加到群组中")
            else:
                # 过滤有效数据
                valid_items = []
                invalid_items_count = 0
                for idx, item in enumerate(items):
                    logger.debug(f"处理第 {idx+1} 条用户数据: {item}")
                    fields = item.get("fields", {})
                    logger.debug(f"第 {idx+1} 条数据的字段详情: {fields}")
                    # 使用正确的字段名提取数据
                    qq = fields.get("QQ号码", [{}])[0].get("text", "")
                    game_id = fields.get("游戏ID", [{}])[0].get("text", "")
                    logger.debug(f"提取到的QQ: '{qq}', 游戏ID: '{game_id}'")
                    
                    # 只有当QQ号和游戏ID都不为空时，才认为是有效数据
                    if qq.strip() and game_id.strip():
                        valid_items.append(item)
                        logger.debug(f"第 {idx+1} 条数据有效，已添加到有效数据列表")
                    else:
                        invalid_items_count += 1
                        logger.debug(f"第 {idx+1} 条数据无效，QQ或游戏ID为空，已跳过")
                
                logger.info(f"过滤后得到 {len(valid_items)} 个有效用户提交记录，{invalid_items_count} 个无效记录被过滤")
                logger.debug(f"有效用户数据详情: {valid_items}")
                
                if not valid_items:
                    logger.info("没有查询到任何有效记录")
                    try:
                        if group_id:
                            await bot.send_group_msg(group_id=int(group_id), message="📭 昨日没有查询到任何有效记录。")
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"发送消息失败: {error_msg}", exc_info=True)
                        # 检查是否是因为机器人不在群内
                        if "不是本群成员" in error_msg or "not in group" in error_msg.lower():
                            logger.error(f"机器人不在目标群组 {group_id} 内，请将机器人QQ号添加到群组中")
                else:
                    response_text = "📋 昨日提交白名单申请的用户如下：\n\n"
                    user_details = []
                    for idx, item in enumerate(valid_items, start=1):
                        fields = item.get("fields", {})
                        # 使用正确的字段名提取数据
                        qq = fields.get("QQ号码", [{}])[0].get("text", "未知")
                        game_id = fields.get("游戏ID", [{}])[0].get("text", "未知")
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
                        logger.error(f"发送用户列表消息失败: {error_msg}", exc_info=True)
                        # 检查是否是因为机器人不在群内
                        if "不是本群成员" in error_msg or "not in group" in error_msg.lower():
                            logger.error(f"机器人不在目标群组 {group_id} 内，请将机器人QQ号添加到群组中")
                    
                    # 循环添加用户白名单
                    logger.info("开始循环添加用户白名单")
                    success_count = 0
                    fail_count = 0
                    success_users = []
                    fail_users = []
                    
                    for idx, item in enumerate(valid_items):
                        logger.debug(f"开始处理第 {idx+1} 个有效用户")
                        fields = item.get("fields", {})
                        # 使用正确的字段名提取数据
                        qq = fields.get("QQ号码", [{}])[0].get("text", "")
                        game_id = fields.get("游戏ID", [{}])[0].get("text", "")
                        logger.info(f"正在处理用户 QQ:{qq}, GameID:{game_id}")
                        
                        # 数据校验，跳过空数据
                        if not qq.strip() or not game_id.strip():
                            logger.warning(f"发现空数据，QQ: '{qq}', GameID: '{game_id}'，跳过该条记录")
                            continue
                        
                        # 检查用户是否在群内
                        if group_id and qq:
                            try:
                                logger.debug(f"准备检查用户 {qq} 是否在群 {group_id} 内")
                                group_member_info = await bot.get_group_member_info(
                                    group_id=int(group_id),
                                    user_id=int(qq),
                                    no_cache=True
                                )
                                logger.info(f"用户 {qq} 在群 {group_id} 内，信息: {group_member_info}")
                                logger.debug(f"用户 {qq} 的群成员信息详情: {group_member_info}")
                            except Exception as e:
                                logger.warning(f"用户 {qq} 不在群 {group_id} 内或获取信息失败: {str(e)}")
                                logger.debug("详细错误信息", exc_info=True)
                                # 用户不在群内，跳过添加白名单
                                fail_count += 1
                                fail_users.append({"qq": qq, "game_id": game_id, "error": "用户不在群内"})
                                continue
                        
                        if game_id:
                            try:
                                logger.debug(f"准备为游戏ID {game_id} 添加白名单")
                                manager = 面板管理(f"multilogin whitelist add {game_id}")
                                result = manager.发送并获取日志()
                                logger.info(f"添加白名单成功，游戏ID: {game_id}, 返回结果: {result}")
                                logger.debug(f"添加白名单详细结果: {result}")
                                success_count += 1
                                success_users.append({"qq": qq, "game_id": game_id})
                            except Exception as e:
                                logger.error(f"添加白名单失败，QQ: {qq}, 游戏ID: {game_id}, 错误: {str(e)}")
                                logger.debug("详细错误信息", exc_info=True)
                                fail_count += 1
                                fail_users.append({"qq": qq, "game_id": game_id, "error": str(e)})
                        else:
                            logger.warning(f"用户 QQ:{qq} 的游戏ID为空，跳过添加白名单")
                            fail_count += 1
                            fail_users.append({"qq": qq, "game_id": "空", "error": "游戏ID为空"})
                    
                    # 发送添加结果
                    result_message = f"✅ 白名单添加完成！成功: {success_count}个，失败: {fail_count}个"
                    logger.info(f"白名单添加完成统计 - 成功: {success_count}, 失败: {fail_count}")
                    logger.debug(f"成功用户列表: {success_users}")
                    logger.debug(f"失败用户列表: {fail_users}")
                    
                    # 只发送成功添加白名单的用户信息
                    if success_users:
                        success_message = "✅ 以下用户白名单添加成功：\n\n"
                        for idx, user in enumerate(success_users, start=1):
                            success_message += f"{idx}. QQ：{user['qq']} | 游戏ID：{user['game_id']}\n"
                        try:
                            if group_id:
                                await bot.send_group_msg(group_id=int(group_id), message=success_message)
                        except Exception as e:
                            error_msg = str(e)
                            logger.error(f"发送成功用户列表消息失败: {error_msg}", exc_info=True)
                            if "不是本群成员" in error_msg or "not in group" in error_msg.lower():
                                logger.error(f"机器人不在目标群组 {group_id} 内，请将机器人QQ号添加到群组中")
                    
                    try:
                        if group_id:
                            await bot.send_group_msg(group_id=int(group_id), message=result_message)
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"发送结果消息失败: {error_msg}", exc_info=True)
                        # 检查是否是因为机器人不在群内
                        if "不是本群成员" in error_msg or "not in group" in error_msg.lower():
                            logger.error(f"机器人不在目标群组 {group_id} 内，请将机器人QQ号添加到群组中")
        else:
            logger.warning(f"获取用户信息失败或无数据返回，结果: {result}")
            logger.debug(f"获取用户信息失败详情: code={result.get('code') if isinstance(result, dict) else 'N/A'}")
            try:
                if group_id:
                    await bot.send_group_msg(group_id=int(group_id), message="❌ 获取用户信息失败或无数据返回。")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"发送失败消息失败: {error_msg}", exc_info=True)
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
            logger.error(f"发送错误消息失败: {error_msg}", exc_info=True)
            # 检查是否是因为机器人不在群内
            if "不是本群成员" in error_msg or "not in group" in error_msg.lower():
                logger.error(f"机器人不在目标群组 {group_id} 内，请将机器人QQ号添加到群组中")