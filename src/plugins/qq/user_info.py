import nonebot
import requests
from nonebot import logger, on_command
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.adapters import Message
from nonebot.params import CommandArg

get_user_info = on_command("get_user", aliases={"获取飞书记录"}, priority=5)

@get_user_info.handle()
async def handle_user_info_command(event: MessageEvent,args: Message = CommandArg()):
    """
    处理获取QQ用户信息的命令
    """
    
    if location := args.extract_plain_text():
        user_info = await fetch_user_info(location)
    
        if user_info:
            reply = f"用户信息:\n"
            reply += f"昵称: {user_info['Name']}\n"
            reply += f"QQ等级: {user_info['QQLevel']}\n"
            reply += f"历史活跃天数: {user_info['Day']}\n"
            # FaceUrl 可以根据需要添加
            await get_user_info.finish(reply)
        else:
            await get_user_info.finish("未能获取用户信息")
    else:
        await get_user_info.finish("请提供QQ号码")
        return
    
    # 获取用户信息
    # user_info = fetch_user_info(qq_number)
    
    # if user_info:
    #     reply = f"用户信息:\n"
    #     reply += f"昵称: {user_info['Name']}\n"
    #     reply += f"QQ等级: {user_info['QQLevel']}\n"
    #     reply += f"活跃天数: {user_info['Day']}\n"
    #     # FaceUrl 可以根据需要添加
    #     await get_user_info.finish(reply)
    # else:
    #     await get_user_info.finish("未能获取用户信息")


async def fetch_user_info(qq_number):
    """
    获取QQ用户信息并提取指定字段
    
    Args:
        qq_number (str): QQ号码
        
    Returns:
        dict: 包含指定字段的用户信息
    """
    # 构建请求URL
    try:
        key = nonebot.get_driver().config.shwgij_key  # 从配置中获取API密钥
        url = f"https://api.shwgij.com/api/qq/qqinfo?key={key}&qq={qq_number}"
        
        response = requests.get(url)
        logger.debug(f"Response Status Code: {response.status_code}")
        logger.debug(f"Response Content: {response.text}")
        data = response.json()
        
        # 检查请求是否成功
        if response.status_code == 200:
            # 提取指定字段
            user_data = data.get("data", {}).get("mRes", {})
            extracted_data = {
                "Name": user_data.get("sNickName"),
                "FaceUrl": user_data.get("sFaceUrl"),
                "QQLevel": user_data.get("iQQLevel"),
                "Day": user_data.get("iTotalActiveDay")
            }
            logger.debug(f"Extracted User Data: {extracted_data}")
            return extracted_data
        else:
            return None
            
    except Exception as e:
        logger.error(f"获取用户信息时出错: {e}")
        return None


# 保留示例用法但修改函数名以避免冲突
if __name__ == "__main__":
    def test_get_user_info(qq_number):
        """
        测试用函数
        """
        return fetch_user_info(qq_number)
    
    qq_number = "3456842349"  # 替换为你想查询的QQ号码
    user_info = test_get_user_info(qq_number)
    if user_info:
        print("用户信息:", user_info)
    else:
        print("未能获取用户信息")