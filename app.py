import streamlit as st
import os
import time
import pandas as pd
from src.data_processor import WorkflowModifier
from src.comfy_client import ComfyAgent
from src.file_manager import AssetManager

# === 配置区 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "config", "workflow_api.json")
PROJECT_OUTPUT_DIR = os.path.join(BASE_DIR, "output")
# ⚠️ 再次确认你的 ComfyUI 输出路径
COMFY_OUTPUT_DIR = r"D:\ComfyUI_Main\ComfyUI-aki-v3\ComfyUI-aki-v3\ComfyUI\output"

NODE_ID_PROMPT = "6"  # 根据你的实际 ID 修改
NODE_ID_SEED = "3"
# === 🎨 风格预设库 ===
STYLE_PRESETS = {
    "✨ 通用高画质 (General Best)": "masterpiece, best quality, high resolution, 8k, detailed",
    "🤖 赛博朋克 (Cyberpunk)": "cyberpunk, neon lights, rain, futuristic city, sci-fi, high contrast, masterpiece",
    "🌸 日系动漫 (Anime)": "anime style, studio ghibli, cel shaded, vibrant colors, cute, masterpiece",
    "🖌️ 墨水油画 (Ink & Oil)": "oil painting, thick strokes, ink wash, artistic, abstract, masterpiece"
}

# === 页面设置 ===
st.set_page_config(
    page_title="Siyua AIGC Workstation",
    page_icon="🎨",
    layout="wide"
)

# === 侧边栏：控制台 ===
with st.sidebar:
    st.title("🎛️ 指挥控制台")
    st.markdown("---")
    
    # 1. 基础描述
    user_prompt = st.text_area("画面描述 (Content)", value="1girl, looking at viewer", height=100)
    
    # 2. 风格选择 (新增功能！)
    selected_style_name = st.selectbox("选择画风 (Style)", list(STYLE_PRESETS.keys()))
    
    # 3. 随机种子
    seed_input = st.number_input("随机种子 (Seed)", value=1001, min_value=1)
    
    # 4. 自动拼接逻辑
    # 获取选中风格对应的 prompt
    style_prompt = STYLE_PRESETS[selected_style_name]
    # 拼合最终 prompt
    final_prompt = f"{user_prompt}, {style_prompt}"
    
    # 在界面上显示一下最终发给 AI 的词 (方便调试)
    st.caption(f"ℹ️ 最终发送的提示词: {final_prompt[:50]}...")
    
    st.markdown("---")
    
    # 发射按钮逻辑微调
    if st.button("🚀 发射指令 (Generate)", type="primary"):
        # 1. 初始化代理
        agent = ComfyAgent()
        if not agent.is_server_ready():
            st.error("❌ 无法连接 ComfyUI，请检查是否启动！")
        else:
            try:
                # 2. 准备工作流
                modifier = WorkflowModifier(TEMPLATE_PATH)
                modifier.update_prompt(NODE_ID_PROMPT, final_prompt)
                modifier.workflow_data[NODE_ID_SEED]["inputs"]["seed"] = seed_input
                
                # 3. 发送
                workflow = modifier.get_workflow()
                success, msg = agent.send_job(workflow)
                
                if success:
                    st.success(f"✅ 指令已送达！ID: {msg}")
                    with st.spinner("正在生产中，请稍候..."):
                        # 简单的等待逻辑
                        time.sleep(5) 
                        # 触发归档搬运
                        archiver = AssetManager(COMFY_OUTPUT_DIR, PROJECT_OUTPUT_DIR)
                        today_str = time.strftime("%Y%m%d")
                        archiver.sync_latest_images(today_str)
                else:
                    st.error(f"❌ 发送失败: {msg}")
                    
            except Exception as e:
                st.error(f"发生错误: {e}")

# === 主画面：资产画廊 ===
st.title("🖼️ AIGC 资产监控室")
st.caption(f"当前监控目录: {PROJECT_OUTPUT_DIR}")

# 刷新按钮
if st.button("🔄 刷新画廊"):
    st.rerun()

# 展示图片逻辑
if os.path.exists(PROJECT_OUTPUT_DIR):
    # 获取所有图片文件
    images = [f for f in os.listdir(PROJECT_OUTPUT_DIR) if f.endswith(('.png', '.jpg', '.webp'))]
    
    if images:
        # 按修改时间倒序排列（最新的在前面）
        images.sort(key=lambda x: os.path.getmtime(os.path.join(PROJECT_OUTPUT_DIR, x)), reverse=True)
        
        # 建立网格布局
        cols = st.columns(4) # 每行显示4张
        for idx, img_name in enumerate(images):
            img_path = os.path.join(PROJECT_OUTPUT_DIR, img_name)
            with cols[idx % 4]:
                st.image(img_path, caption=img_name, use_container_width=True)
    else:
        st.info("暂无资产，请在左侧侧边栏发送指令。")
else:
    st.warning("输出目录不存在，请先运行一次生成任务。")