import nonebot
import requests
import time
import json
import os



config = nonebot.get_driver().config
APP_ID = config.feishu_app_id  # 替换为你的App ID
APP_SECRET = config.feishu_app_secret  # 替换为你的App Secret
class FeishuTokenManager:
    """
    飞书开放平台Token管理器

    用于获取和管理飞书自建应用的tenant_access_token，
    支持自动刷新和本地缓存功能。

    使用方法:
    1. 创建实例: manager = FeishuTokenManager("your_app_id", "your_app_secret")
    2. 获取token: token = manager.get_access_token()
    3. 在请求中使用: headers = {"Authorization": f"Bearer {token}"}
    """

    def __init__(self):
        """
        初始化Token管理器

        Args:
            app_id (str): 飞书应用的App ID
            app_secret (str): 飞书应用的App Secret
        """
        self.app_id = APP_ID
        self.app_secret = APP_SECRET
        self.access_token = None
        self.expires_at = 0
        self.token_file = "token.json"
        self.load_token_from_file()

    def get_access_token(self):
        """
        获取有效的tenant_access_token

        自动检查现有token是否有效，如果无效或即将过期则请求新token。
        Token默认提前1分钟刷新以确保连续性。

        Returns:
            str: 有效的tenant_access_token

        Raises:
            Exception: 当获取token失败时抛出异常
        """
        # 检查现有token是否有效
        if self.access_token and time.time() < self.expires_at - 60:  # 提前1分钟刷新
            return self.access_token

        # 请求新的access_token
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {"app_id": self.app_id, "app_secret": self.app_secret}

        response = requests.post(url, headers=headers, data=json.dumps(data))
        result = response.json()

        if result.get("code") == 0:
            self.access_token = result.get("tenant_access_token")
            expires_in = result.get("expire", 7200)  # 默认2小时
            self.expires_at = time.time() + expires_in

            # 保存到文件
            self.save_token_to_file()

            return self.access_token
        else:
            raise Exception(f"获取access_token失败: {result.get('msg')}")

    def save_token_to_file(self):
        """
        将token信息保存到本地文件

        保存access_token、过期时间和更新时间到JSON文件中，
        以便在程序重启后可以复用未过期的token。
        """
        token_data = {
            "access_token": self.access_token,
            "expires_at": self.expires_at,
            "updated_at": time.time(),
        }
        with open(self.token_file, "w", encoding="utf-8") as f:
            json.dump(token_data, f)

    def load_token_from_file(self):
        """
        从本地文件加载token信息

        在初始化时尝试从文件中加载之前保存的token，
        如果token仍然有效则直接使用，避免重复请求。
        """
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, "r", encoding="utf-8") as f:
                    token_data = json.load(f)

                # 检查token是否仍然有效
                if token_data.get("expires_at", 0) > time.time() + 60:
                    self.access_token = token_data.get("access_token")
                    self.expires_at = token_data.get("expires_at")
            except Exception as e:
                print(f"加载token文件失败: {e}")


