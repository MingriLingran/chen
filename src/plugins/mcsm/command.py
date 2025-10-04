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
        
    def 获取实例列表(self):
        # TODO: 实现实例列表获取功能
        pass
        
    def 发送命令(self, command, uuid=None, daemonid=None):
        uuid = uuid or self.uuid
        daemonid = daemonid or self.daemonid
        
        if not uuid or not daemonid or not command:
            raise ValueError("缺少必要的参数: uuid, daemonid 或 command")
            
        url = f"{self.api_url}/api/protected_instance/command?apikey={self.api_key}&uuid={uuid}&daemonId={daemonid}&command={command}"
        response = requests.post(url, headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"命令发送失败: HTTP {response.status_code}")
        
        command_data = response.json()
        command_time = command_data["time"]  # 命令发送时间戳

        time.sleep(1.5)
        self.start_time = command_time - 1000  # 提前1秒
        self.end_time = command_time + 5000    # 延后5秒
        return command_data
        
    def 查询日志(self, uuid=None, daemonid=None):
        uuid = uuid or self.uuid
        daemonid = daemonid or self.daemonid
        
        logs_url = f"{self.api_url}/api/protected_instance/outputlog?apikey={self.api_key}&uuid={uuid}&daemonId={daemonid}&size=1kb"
        response = requests.get(logs_url, headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"日志查询失败: HTTP {response.status_code}")
        
        logs_data = response.json()
        log_content = logs_data["data"]
        log_time = logs_data["time"]
        
        # 5. 提取匹配时间范围内的日志
        matched_logs = []
        current_timestamp = None
        
        for line in log_content.split('\n'):
            # 尝试提取时间戳
            time_match = re.search(r'\[(\d{2}:\d{2}:\d{2})\]', line)
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
            
            # 检查是否在时间范围内
            if current_timestamp and self.start_time <= current_timestamp <= self.end_time:
                matched_logs.append(line)
        
        return '\n'.join(matched_logs)
        
    def 发送并获取日志(self, command=None, uuid=None, daemonid=None):
        command = command or self.command
        if not command:
            raise ValueError("命令不能为空")
            
        self.发送命令(command, uuid, daemonid)
        return self.查询日志(uuid, daemonid)


command = on_command("mcsm", aliases={"MCSM"}, priority=5,permission=SUPERUSER)

@command.handle()
async def _(args: Message = CommandArg()):
    uuid = getattr(config, "mcsm_uuid", None)
    daemonid = getattr(config, "mcsm_daemonid", None)
    
    if not uuid or not daemonid:
        await command.finish("未配置 MCSM 信息，请检查配置文件")
        
    args_text = args.extract_plain_text().strip()
    if args_text:
        try:
            manager = 面板管理(args_text)
            result = manager.发送并获取日志()
            await command.finish(result)
        except Exception as e:
            logger.debug(f"执行命令时出错: {str(e)}")

@command.got("command", "请输入要发送的命令")
async def _(matcher: Matcher, command_text: str = ArgPlainText("command")):
    uuid = getattr(config, "mcsm_uuid", None)
    daemonid = getattr(config, "mcsm_daemonid", None)
    
    if not uuid or not daemonid:
        await matcher.finish("未配置 MCSM 信息，请检查配置文件")
        
    try:
        manager = 面板管理(command_text)
        result = manager.发送并获取日志()
        await matcher.finish(result)
    except Exception as e:
        logger.error(f"执行命令时出错: {str(e)}")