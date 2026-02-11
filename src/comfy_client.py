import requests
import time

class ComfyAgent:
    """
    负责与 ComfyUI 后端 API 进行 HTTP 通信的代理。
    """
    def __init__(self, base_url="http://127.0.0.1:8188"):
        self.base_url = base_url
        self.prompt_url = f"{base_url}/prompt"

    def is_server_ready(self):
        """检查服务器是否存活"""
        try:
            # 尝试访问服务器根目录
            response = requests.get(self.base_url)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def send_job(self, workflow_data):
        """发送生成任务"""
        payload = {"prompt": workflow_data}
        try:
            response = requests.post(self.prompt_url, json=payload)
            if response.status_code == 200:
                job_id = response.json().get('prompt_id')
                return True, job_id
            else:
                return False, response.text
        except requests.RequestException as e:
            return False, str(e)