from nonebot import logger, on_command, require
from nonebot_plugin_apscheduler import scheduler
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.permission import SUPERUSER
import nonebot
import requests
import json
from .密钥管理 import FeishuTokenManager

require("nonebot_plugin_apscheduler")
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
        """
        获取所有符合条件的用户记录（支持分页查询，最多可获取5000条记录）
        """
        # 修改: 在实际需要时再初始化token
        await self.ensure_token()
        
        all_items = []
        page_token = None
        max_pages = 100  # 限制最大页数，防止无限循环
        current_page = 0
        
        while current_page < max_pages:
            current_page += 1
            logger.debug(f"正在获取第 {current_page} 页数据")
            
            # 构建请求数据
            request_data = {
                "filter": {
                    "conjunction": "and",
                    "conditions": [
                        {"field_name": "总分", "operator": "isGreater", "value": [75]},
                        {
                            "field_name": "提交时间",
                            "operator": "is",
                            "value": ["Yesterday"],
                        },
                    ],
                },
                "page_size": 500,  # 根据API文档，最大支持500条记录
                "automatic_fields": "false",
                "field_names": [
                    "QQ号码",
                    "总分",
                    "游戏ID",
                    "提交时间",
                ],
            }
            
            # 构建请求URL和参数
            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.base_id}/tables/{self.table_id}/records/search"
            params = {}
            
            # 如果有page_token，添加到查询参数中
            if page_token:
                params["page_token"] = page_token
                
            data = json.dumps(request_data)
            logger.debug(f"请求参数: {request_data}")
            logger.debug(f"查询参数: {params}")
            
            try:
                response = requests.post(
                    url,
                    headers=self.headers,
                    data=data,
                    params=params  # 将page_token作为查询参数传递
                )
                result = response.json()
                logger.debug(f"第 {current_page} 页响应: {result}")
                
                if result and result.get("code") == 0:
                    items = result.get("data", {}).get("items", [])
                    all_items.extend(items)
                    logger.debug(f"第 {current_page} 页获取到 {len(items)} 条记录，当前总记录数: {len(all_items)}")
                    
                    # 检查是否还有更多数据
                    has_more = result.get("data", {}).get("has_more", False)
                    page_token = result.get("data", {}).get("page_token")
                    logger.debug(f"has_more: {has_more}, page_token: {page_token}")
                    
                    # 如果没有更多数据或page_token为空，则结束循环
                    if not has_more or not page_token:
                        logger.debug("没有更多页面，结束分页查询")
                        break
                else:
                    logger.error(f"获取第 {current_page} 页数据失败: {result}")
                    break
                    
            except Exception as e:
                logger.error(f"获取第 {current_page} 页数据时发生异常: {e}", exc_info=True)
                break
                
        logger.info(f"总共获取到 {len(all_items)} 条用户记录")
        return {
            "code": 0,
            "data": {
                "items": all_items
            }
        }

    async def 根据QQ号查询用户(self, qq_number: str):
        """
        根据QQ号查询特定用户记录
        """
        await self.ensure_token()
        data = json.dumps(
            {
                "filter": {
                    "conjunction": "and",
                    "conditions": [
                        {"field_name": "QQ号码", "operator": "is", "value": [qq_number]},
                    ],
                },
                "page_size": 10,  # 一般一个QQ号只会有一条记录，设置10条以防万一
                "automatic_fields": "false",
                "field_names": [
                    "QQ号码",
                    "总分",
                    "游戏ID",
                    "提交时间",
                ],
            }
        )
        try:
            response = requests.post(
                f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.base_id}/tables/{self.table_id}/records/search",
                headers=self.headers,
                data=data,
            )
            logger.debug(f"根据QQ号查询用户响应: {response.json()}")
            return response.json()
        except Exception as e:
            logger.debug(f"根据QQ号查询用户失败: {e}", exc_info=True)
            return None


weather = on_command("qc", aliases={"获取飞书记录"}, priority=5,permission=SUPERUSER)


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
                    qq = fields.get("QQ号码", [{}])[0].get("text", "未知")
                    game_id = fields.get("游戏ID", [{}])[0].get(
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
        logger.error(f"处理 /qc 命令时发生异常：{e}", exc_info=True)