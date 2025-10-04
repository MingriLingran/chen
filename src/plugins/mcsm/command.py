import time
import re
import requests
import nonebot
from nonebot import logger, on_command
from datetime import datetime, timedelta
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg, ArgPlainText
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER

config = nonebot.get_driver().config


class 面板管理:
    def __init__(self, command=None, uuid=None, daemonid=None):
        self.api_key = config.mcsm_api_key
        self.api_url = config.mcsm_api_url
        self.uuid = uuid or config.mcsm_uuid
        self.daemonid = daemonid or config.mcsm_daemonid
        self.command = command
        self.headers = {
            "Content-Type": "application/json; charset=utf-8",
            "X-Requested-With": "XMLHttpRequest"
        }
        logger.debug(f"面板管理实例已创建，API URL: {self.api_url}, UUID: {self.uuid}, DaemonID: {self.daemonid}")
        
    def 获取实例列表(self):
        # TODO: 实现实例列表获取功能
        pass
        
    def 发送命令(self, command, uuid=None, daemonid=None):
        uuid = uuid or self.uuid
        daemonid = daemonid or self.daemonid
        
        logger.debug(f"准备发送命令，UUID: {uuid}, DaemonID: {daemonid}, 命令: {command}")
        
        if not uuid or not daemonid or not command:
            logger.error("缺少必要的参数: uuid, daemonid 或 command")
            raise ValueError("缺少必要的参数: uuid, daemonid 或 command")
            
        url = f"{self.api_url}/api/protected_instance/command?apikey={self.api_key}&uuid={uuid}&daemonId={daemonid}&command={command}"
        logger.info(f"正在发送命令到URL: {url}")
        
        try:
            response = requests.post(url, headers=self.headers)
            logger.debug(f"命令发送响应状态码: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"命令发送失败: HTTP {response.status_code}, 响应内容: {response.text}")
                raise Exception(f"命令发送失败: HTTP {response.status_code}")
            
            command_data = response.json()
            logger.debug(f"命令发送成功，响应数据: {command_data}")
            command_time = command_data["time"]  # 命令发送时间戳
            
            logger.info(f"命令发送成功，时间戳: {command_time}")
            
            time.sleep(1.5)
            self.start_time = command_time - 1000  # 提前1秒
            self.end_time = command_time + 5000    # 延后5秒
            
            logger.debug(f"设置日志时间范围: 开始时间 {self.start_time}, 结束时间 {self.end_time}")
            return command_data
        except requests.RequestException as e:
            logger.error(f"发送命令时网络请求异常: {str(e)}", exc_info=True)
            raise Exception(f"网络请求异常: {str(e)}")
        except Exception as e:
            logger.error(f"发送命令时发生未知错误: {str(e)}", exc_info=True)
            raise
        
    def 查询日志(self, uuid=None, daemonid=None):
        uuid = uuid or self.uuid
        daemonid = daemonid or self.daemonid
        
        logger.debug(f"准备查询日志，UUID: {uuid}, DaemonID: {daemonid}")
        
        logs_url = f"{self.api_url}/api/protected_instance/outputlog?apikey={self.api_key}&uuid={uuid}&daemonId={daemonid}&size=1kb"
        logger.info(f"正在获取日志，URL: {logs_url}")
        
        try:
            response = requests.get(logs_url, headers=self.headers)
            logger.debug(f"日志查询响应状态码: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"日志查询失败: HTTP {response.status_code}, 响应内容: {response.text}")
                raise Exception(f"日志查询失败: HTTP {response.status_code}")
            
            logs_data = response.json()
            log_content = logs_data["data"]
            log_time = logs_data["time"]
            
            logger.debug(f"日志查询成功，日志时间: {log_time}, 日志长度: {len(log_content)}")
            logger.debug(f"日志内容: {log_content}")
            
            # 5. 提取匹配时间范围内的日志
            matched_logs = []
            current_timestamp = None
            
            logger.debug(f"开始提取时间范围内的日志，范围: {self.start_time} - {self.end_time}")
            
            for line_num, line in enumerate(log_content.split('\n')):
                # 尝试提取时间戳
                time_match = re.search(r'(\d{2}:\d{2}:\d{2})', line)
                if time_match:
                    time_str = time_match.group(1)
                    # 将日志时间转换为绝对时间戳
                    log_datetime = datetime.fromtimestamp(log_time / 1000)
                    line_time = datetime.strptime(time_str, "%H:%M:%S")
                    line_time = line_time.replace(
                        year=log_datetime.year,
                        month=log_datetime.month,
                        day=log_datetime.day
                    )
                    current_timestamp = int(line_time.timestamp() * 1000)
                    logger.debug(f"解析日志行 #{line_num} 时间戳: {current_timestamp}")
                else:
                    logger.debug(f"日志行 #{line_num} 未找到时间戳: {line[:50]}...")
                
                # 检查是否在时间范围内
                if current_timestamp and self.start_time <= current_timestamp <= self.end_time:
                    matched_logs.append(line)
                    logger.debug(f"匹配日志行 #{line_num}: {line[:50]}...")
                else:
                    logger.debug(f"日志行 #{line_num} 不在时间范围内: {line[:50]}...")
            
            logger.info(f"日志提取完成，共匹配到 {len(matched_logs)} 行日志")
            return '\n'.join(matched_logs)
        except requests.RequestException as e:
            logger.error(f"查询日志时网络请求异常: {str(e)}", exc_info=True)
            raise Exception(f"网络请求异常: {str(e)}")
        except Exception as e:
            logger.error(f"查询日志时发生未知错误: {str(e)}", exc_info=True)
            raise
        
    def 发送并获取日志(self, command=None, uuid=None, daemonid=None):
        command = command or self.command
        logger.debug(f"开始执行发送并获取日志操作，命令: {command}")
        
        if not command:
            logger.error("命令不能为空")
            raise ValueError("命令不能为空")
            
        self.发送命令(command, uuid, daemonid)
        return self.查询日志(uuid, daemonid)


command = on_command("mcsm", aliases={"MCSM"}, priority=5,permission=SUPERUSER)

@command.handle()
async def _(args: Message = CommandArg()):
    logger.info("收到MCSM命令请求")
    uuid = getattr(config, "mcsm_uuid", None)
    daemonid = getattr(config, "mcsm_daemonid", None)
    
    logger.debug(f"配置信息 - UUID: {uuid}, DaemonID: {daemonid}")
    
    if not uuid or not daemonid:
        logger.error("未配置MCSM信息，请检查配置文件")
        await command.finish("未配置 MCSM 信息，请检查配置文件")
        
    args_text = args.extract_plain_text().strip()
    logger.info(f"接收到命令参数: {args_text}")
    
    if args_text:
        try:
            logger.debug(f"创建面板管理实例，命令: {args_text}")
            manager = 面板管理(args_text)
            logger.debug("开始发送命令并获取日志")
            result = manager.发送并获取日志()
            logger.info(f"命令执行成功，返回结果长度: {len(result)}")
            await command.finish(result)
        except Exception as e:
            logger.error(f"执行命令时出错: {str(e)}", exc_info=True)

@command.got("command", "请输入要发送的命令")
async def _(matcher: Matcher, command_text: str = ArgPlainText("command")):
    logger.info(f"通过交互方式获取命令: {command_text}")
    uuid = getattr(config, "mcsm_uuid", None)
    daemonid = getattr(config, "mcsm_daemonid", None)
    
    logger.debug(f"配置信息 - UUID: {uuid}, DaemonID: {daemonid}")
    
    if not uuid or not daemonid:
        logger.error("未配置MCSM信息，请检查配置文件")
        await matcher.finish("未配置 MCSM 信息，请检查配置文件")
        
    try:
        logger.debug(f"创建面板管理实例，命令: {command_text}")
        manager = 面板管理(command_text)
        logger.debug("开始发送命令并获取日志")
        result = manager.发送并获取日志()
        logger.info(f"命令执行成功，返回结果长度: {len(result)}")
        await matcher.finish(result)
    except Exception as e:
        logger.error(f"执行命令时出错: {str(e)}", exc_info=True)