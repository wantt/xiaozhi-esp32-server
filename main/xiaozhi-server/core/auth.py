from config.logger import setup_logging
import json
import requests

TAG = __name__
logger = setup_logging()


class AuthenticationError(Exception):
    """认证异常"""
    pass


class AuthMiddleware:
    def __init__(self, config):
        self.config = config
        self.auth_config = config["server"].get("auth", {})
        # 构建token查找表
        self.tokens = {
            item["token"]: item["name"]
            for item in self.auth_config.get("tokens", [])
        }
        # 设备白名单
        self.allowed_devices = set(
            self.auth_config.get("allowed_devices", [])
        )

    def auth_device(self, headers:dict={}, chat_count:int=0):
        device_id = headers.get("device-id", "")
        api_url = self.auth_config.get('authurl','http://47.243.172.147:24003/auth_once')
        if device_id and api_url:
            request_json = {
                "device_id": device_id,
                "chat_count": chat_count,
            }
            headers = {
                "Content-Type": "application/json"
            }
            response = requests.request("GET", api_url, json=request_json, headers=headers,timeout=1)
            if response.status_code == 200:
                data = json.loads(response.content)
                code = data['code']
                if code == '402':
                    return False
            else:
                logger.bind(tag=TAG).error(response.content)
            return True
        return False

    async def authenticate(self, headers):
        """验证连接请求"""
        # 检查是否启用认证
        if not self.auth_config.get("enabled", False):
            return True

        # 检查设备是否在白名单中
        device_id = headers.get("device-id", "")

        if self.allowed_devices and device_id in self.allowed_devices:
            return True

        # 验证Authorization header
        auth_header = headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.bind(tag=TAG).error("Missing or invalid Authorization header")
            raise AuthenticationError("Missing or invalid Authorization header")

        token = auth_header.split(" ")[1]
        if token not in self.tokens:
            logger.bind(tag=TAG).error(f"Invalid token: {token}")
            raise AuthenticationError("Invalid token")

        logger.bind(tag=TAG).info(f"Authentication successful - Device: {device_id}, Token: {self.tokens[token]}")
        return True

    def get_token_name(self, token):
        """获取token对应的设备名称"""
        return self.tokens.get(token)
