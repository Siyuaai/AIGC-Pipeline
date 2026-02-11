import json
import random

class WorkflowModifier:
    """
    专门负责修改工作流数据的类。
    """
    def __init__(self, template_path):
        self.template_path = template_path
        self.workflow_data = self._load_template()

    def _load_template(self):
        """加载 JSON 模板"""
        try:
            with open(self.template_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ 致命错误：找不到模板文件 {self.template_path}")

    def update_prompt(self, node_id, new_text):
        """修改指定节点的提示词"""
        # 注意：这里需要你确认 JSON 里的 ID 是否匹配
        if node_id in self.workflow_data:
            self.workflow_data[node_id]["inputs"]["text"] = new_text
        else:
            print(f"⚠️ 警告：节点 ID {node_id} 不存在，跳过修改。")

    def randomize_seed(self, node_id):
        """注入随机种子"""
        new_seed = random.randint(1, 10**14)
        if node_id in self.workflow_data:
            self.workflow_data[node_id]["inputs"]["seed"] = new_seed
        return new_seed

    def get_workflow(self):
        """返回修改后的数据"""
        return self.workflow_data