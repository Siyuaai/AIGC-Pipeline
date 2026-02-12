import streamlit as st
import os
import time
import pandas as pd  # 👈 引入 Pandas 处理表格
from src.data_processor import WorkflowModifier
from src.comfy_client import ComfyAgent
from src.file_manager import AssetManager

# === ⚙️ 配置区 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "config", "workflow_api.json") # 文生图模板
PROJECT_OUTPUT_DIR = os.path.join(BASE_DIR, "output")
COMFY_OUTPUT_DIR = r"D:\ComfyUI_Main\ComfyUI-aki-v3\ComfyUI-aki-v3\ComfyUI\output"

# 节点 ID (保持不变)
NODE_ID_PROMPT = "6"
NODE_ID_SEED = "3"

# 风格预设
STYLE_PRESETS = {
    "✨ 通用高画质": "masterpiece, best quality, high resolution, 8k, detailed",
    "🤖 赛博朋克": "cyberpunk, neon lights, rain, futuristic city, sci-fi, high contrast",
    "🌸 日系动漫": "anime style, studio ghibli, cel shaded, vibrant colors, cute",
    "🖌️ 墨水油画": "oil painting, thick strokes, ink wash, artistic, abstract"
}

st.set_page_config(page_title="Siyua AIGC Factory", layout="wide", page_icon="🏭")

st.title("🏭 AIGC 智能生产管线")

# === 🎛️ 分页系统 ===
tab1, tab2 = st.tabs(["🎮 单人控制台 (Manual)", "🚀 批量流水线 (Batch)"])

# ------------------------------------------------------------------
# Tab 1: 经典手动模式 (这是你之前成功的代码，逻辑完全一致)
# ------------------------------------------------------------------
with tab1:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("单兵作战")
        user_prompt = st.text_area("画面描述", value="1girl, looking at viewer", height=100)
        selected_style = st.selectbox("画风选择", list(STYLE_PRESETS.keys()))
        seed_input = st.number_input("种子", value=1001, min_value=1)
        
        if st.button("✨ 立即生成", key="btn_manual"):
            agent = ComfyAgent()
            if agent.is_server_ready():
                try:
                    modifier = WorkflowModifier(TEMPLATE_PATH)
                    final_prompt = f"{user_prompt}, {STYLE_PRESETS[selected_style]}"
                    modifier.update_prompt(NODE_ID_PROMPT, final_prompt)
                    
                    if NODE_ID_SEED in modifier.workflow_data:
                        modifier.workflow_data[NODE_ID_SEED]["inputs"]["seed"] = seed_input
                    
                    success, msg = agent.send_job(modifier.get_workflow())
                    
                    if success:
                        st.success(f"✅ 指令发送成功: {msg}")
                        # 模拟进度条
                        bar = st.progress(0)
                        for i in range(100):
                            time.sleep(0.05) 
                            bar.progress(i+1)
                        
                        # 搬运
                        count = AssetManager(COMFY_OUTPUT_DIR, PROJECT_OUTPUT_DIR).sync_latest_images(time.strftime("%Y%m%d"))
                        if count > 0:
                            st.balloons()
                            st.rerun()
                        else:
                            st.warning("⚠️ 未检测到新文件，请稍后刷新画廊")
                except Exception as e:
                    st.error(f"❌ 错误: {e}")
            else:
                st.error("❌ 无法连接 ComfyUI")

# ------------------------------------------------------------------
# Tab 2: 批量生产模式 (新增功能)
# ------------------------------------------------------------------
with tab2:
    st.subheader("📊 CSV 批量作业")
    st.info("💡 请上传包含表头 [prompt, style, seed] 的 CSV 文件")
    
    # 1. 上传 CSV
    uploaded_file = st.file_uploader("📂 上传工单文件", type=["csv"])
    
    if uploaded_file:
        # 读取并展示表格
        df = pd.read_csv(uploaded_file)
        st.dataframe(df, use_container_width=True)
        st.caption(f"共检测到 {len(df)} 个任务")
        
        # 启动按钮
        if st.button("🚀 启动自动化生产线", type="primary"):
            agent = ComfyAgent()
            if not agent.is_server_ready():
                st.error("❌ ComfyUI 未启动！")
            else:
                # 初始化进度
                progress_bar = st.progress(0, text="准备开始...")
                status_box = st.empty() # 占位符，用于动态显示状态
                total_jobs = len(df)
                success_count = 0
                
                # === 核心循环：遍历每一行数据 ===
                for index, row in df.iterrows():
                    # 1. 解析数据
                    current_prompt = str(row['prompt'])
                    # 如果 CSV 里的 style 不在预设里，就用默认的
                    style_key = row.get('style', "✨ 通用高画质")
                    style_prompt = STYLE_PRESETS.get(style_key, "")
                    current_seed = int(row.get('seed', 1001))
                    
                    status_box.info(f"🔄 [任务 {index+1}/{total_jobs}] 正在生成: {current_prompt}...")
                    
                    try:
                        # 2. 修改工作流
                        modifier = WorkflowModifier(TEMPLATE_PATH)
                        final_prompt = f"{current_prompt}, {style_prompt}"
                        
                        modifier.update_prompt(NODE_ID_PROMPT, final_prompt)
                        if NODE_ID_SEED in modifier.workflow_data:
                            modifier.workflow_data[NODE_ID_SEED]["inputs"]["seed"] = current_seed
                        
                        # 3. 发送指令
                        success, msg = agent.send_job(modifier.get_workflow())
                        
                        if success:
                            success_count += 1
                            # ⏳ 关键：给显卡一点喘息时间，避免队列堵死
                            # 每张图等待 5 秒 (根据你的显卡速度调整)
                            time.sleep(5) 
                        else:
                            st.error(f"❌ 任务 {index+1} 失败: {msg}")
                            
                    except Exception as e:
                        st.error(f"❌ 数据异常: {e}")
                    
                    # 更新进度条
                    progress_bar.progress((index + 1) / total_jobs, text=f"进度: {index+1}/{total_jobs}")
                
                status_box.success(f"✅ 生产结束！成功发送 {success_count} 个任务。正在归档图片...")
                
                # 4. 最后统一搬运一次
                time.sleep(2)
                moved = AssetManager(COMFY_OUTPUT_DIR, PROJECT_OUTPUT_DIR).sync_latest_images(time.strftime("%Y%m%d"))
                st.success(f"📦 归档完成！共捕获 {moved} 张新图片。")
                time.sleep(2)
                st.rerun()

# ------------------------------------------------------------------
# 公共画廊区
# ------------------------------------------------------------------
st.markdown("---")
st.subheader("🖼️ 资产监控 (Gallery)")

# 刷新按钮
if st.button("🔄 刷新画廊"):
    st.rerun()

if os.path.exists(PROJECT_OUTPUT_DIR):
    images = [f for f in os.listdir(PROJECT_OUTPUT_DIR) if f.endswith(('.png', '.jpg'))]
    if images:
        # 按时间倒序
        images.sort(key=lambda x: os.path.getmtime(os.path.join(PROJECT_OUTPUT_DIR, x)), reverse=True)
        
        # 显示最近的 8 张
        cols = st.columns(4)
        for idx, img in enumerate(images[:8]): 
            with cols[idx % 4]:
                st.image(os.path.join(PROJECT_OUTPUT_DIR, img), caption=img, use_container_width=True)
    else:
        st.info("暂无图片")