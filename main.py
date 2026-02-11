import os
import time
import pandas as pd
from src.data_processor import WorkflowModifier
from src.comfy_client import ComfyAgent
from src.file_manager import AssetManager  # 引入新写的搬运工

# ==========================================
# 🔧 工程配置区 (Configuration)
# ==========================================

# 1. 获取当前项目路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "config", "workflow_api.json")
DATA_PATH = os.path.join(BASE_DIR, "jobs.csv")
PROJECT_OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# 2. ComfyUI 的输出路径 (⚠️⚠️⚠️ 这里一定要改对 ⚠️⚠️⚠️)
# 也就是你平时用 ComfyUI 生成图片后，图片存放的那个文件夹
# 如果你是便携版，通常在 ComfyUI/output
COMFY_OUTPUT_DIR = r"D:\ComfyUI_Main\ComfyUI-aki-v3\ComfyUI-aki-v3\ComfyUI\output" 
# ↑↑↑ 如果你的盘符是 M盘或 E盘，请手动修改上面的路径 ↑↑↑

# 3. JSON 节点 ID (根据你的 workflow_api.json)
NODE_ID_PROMPT = "6"
NODE_ID_SEED = "3"

def main():
    print("🤖 AIGC Pipeline v1.2 (Full Cycle) 初始化中...")

    # === 第一步：基础设施自检 ===
    agent = ComfyAgent()
    if not agent.is_server_ready():
        print("❌ 错误：无法连接到 ComfyUI。请先启动 ComfyUI 控制台！")
        return

    if not os.path.exists(DATA_PATH):
        print(f"❌ 错误：找不到工单文件 {DATA_PATH}")
        return

    # === 第二步：读取工单 ===
    print(f"📂 正在读取工单: {DATA_PATH}")
    try:
        df = pd.read_csv(DATA_PATH)
        # 过滤掉 NaN 的行 (防呆设计)
        df = df.dropna(subset=['prompt'])
    except Exception as e:
        print(f"❌读取 CSV 失败: {e}")
        return

    # 筛选待处理任务
    pending_jobs = df[df['status'] == 'pending']
    print(f"📋 待处理任务数：{len(pending_jobs)}")

    if len(pending_jobs) == 0:
        print("✅ 所有任务已完成，无需运行。")
        return

    # === 第三步：加载模具 ===
    try:
        modifier = WorkflowModifier(TEMPLATE_PATH)
    except Exception as e:
        print(f"❌ {e}")
        return

    # === 第四步：循环生产 (Production Loop) ===
    for index, row in pending_jobs.iterrows():
        prompt_text = row['prompt']
        seed_val = int(row['seed'])
        job_id_csv = row['id']
        
        print(f"\n--- 正在处理任务 ID: {job_id_csv} ---")
        
        # 1. 修改参数
        modifier.update_prompt(NODE_ID_PROMPT, prompt_text)
        # 强制修改 Seed
        modifier.workflow_data[NODE_ID_SEED]["inputs"]["seed"] = seed_val
        
        print(f"Ref: 提示词='{prompt_text[:20]}...', 种子={seed_val}")

        # 2. 发送指令
        workflow = modifier.get_workflow()
        success, msg = agent.send_job(workflow)

        if success:
            print(f"✅ 指令下发成功! Job ID: {msg}")
            # 更新内存状态
            df.at[index, 'status'] = 'done'
        else:
            print(f"❌ 下发失败: {msg}")

    # === 第五步：等待生成 (Wait) ===
    # 这一步是为了给 ComfyUI 留出渲染时间
    # 假设每张图 3 秒，3张图就是 9 秒，我们给 12 秒缓冲
    wait_time = len(pending_jobs) * 4 
    print(f"\n⏳ 所有指令已发送，等待 GPU 渲染中... ({wait_time}秒)")
    time.sleep(wait_time)

    # === 第六步：资产归档 (Archiving) ===
    # 实例化搬运工
    archiver = AssetManager(COMFY_OUTPUT_DIR, PROJECT_OUTPUT_DIR)
    
    # 获取今天日期
    today_str = time.strftime("%Y%m%d")
    
    # 执行搬运
    archiver.sync_latest_images(today_str)
    
    print("\n🎉 全流程结束！请检查 output 文件夹。")

if __name__ == "__main__":
    main()