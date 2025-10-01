from nonebot import logger, on_command, require

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler
from nonebot.adapters.onebot.v11 import MessageEvent
import nonebot
import requests
import json
from .密钥管理 import FeishuTokenManager

config = nonebot.get_driver().config


class 查询昨天的用户:
    def __init__(self):
        # 修改: 延迟初始化token，避免在插件加载时就执行网络请求
        self.access_token = None
        self.headers = None
        self.base_id = config.feishu_base_id
        self.table_id = config.feishu_table_id

    async def ensure_token(self):
        """确保token已初始化"""
        if self.access_token is None or self.headers is None:
            try:
                # 获取access_token
                token_manager = FeishuTokenManager()
                self.access_token = token_manager.get_access_token()
                logger.debug(f"Access Token: {self.access_token}")
                self.headers = {"Authorization": f"Bearer {self.access_token}"}
            except Exception as e:
                logger.error(f"获取token失败: {e}")
                raise

    async def 获取昨日提交用户(self):
        # 修改: 在实际需要时再初始化token
        await self.ensure_token()
        data = json.dumps({
        "filter": {
            "conjunction": "and",
            "conditions": [
            {
                "field_name": "总分",
                "operator": "isGreater",
                "value": [
                75
                ]
            },
            {
                "field_name": "提交时间",
                "operator": "is",
                "value": [
                "TheLastMonth"
                ]
            }
            ]
        },
        "page_size": 50,
        "automatic_fields": 'false',
        "field_names": [
            "你的QQ号码",
            "总分",
            "你要申请白名单的游戏ID",
            "提交时间"
        ]
        })
        try:
            response = requests.post(
                f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.base_id}/tables/{self.table_id}/records/search",
                headers=self.headers,
                data=data,
            )
            logger.debug(f"Response: {response.json()}")
            return response.json()
        except Exception as e:
            logger.debug(f"获取用户信息失败: {e}")
            return None


weather = on_command("qc", aliases={"获取飞书记录"}, priority=5)


@weather.handle()
# @scheduler.scheduled_job("interval", seconds=30, id="xxx")
async def _():
    try:
        query = 查询昨天的用户()
        result = await query.获取昨日提交用户()
        if result and result.get("code") == 0:
            items = result.get("data", {}).get("items", [])
            if not items:
                await weather.send("📭 没有查询到任何提交记录。")
            else:
                response_text = "📋 昨日提交白名单申请的用户如下：\n\n"
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
                await weather.send(response_text)
        else:
            await weather.send("❌ 获取用户信息失败或无数据返回。")
    except Exception as e:
        logger.error(f"处理 /qc 命令时发生异常：{e}")
