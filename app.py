import streamlit as st
import os
import time
import pandas as pd
import random
from datetime import datetime
from src.data_processor import WorkflowModifier
from src.comfy_client import ComfyAgent
from src.file_manager import AssetManager

# === ⚙️ 配置区 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "config", "workflow_api.json")
PROJECT_OUTPUT_DIR = os.path.join(BASE_DIR, "output")
HISTORY_FILE = os.path.join(BASE_DIR, "history.csv")
COMFY_OUTPUT_DIR = r"D:\ComfyUI_Main\ComfyUI-aki-v3\ComfyUI-aki-v3\ComfyUI\output"

# 节点 ID
NODE_ID_PROMPT = "6"
NODE_ID_SEED = "3"

# 风格预设
STYLE_PRESETS = {
    "✨ 通用高画质": "masterpiece, best quality, high resolution, 8k, detailed",
    "🤖 赛博朋克": "cyberpunk, neon lights, rain, futuristic city, sci-fi, high contrast",
    "🌸 日系动漫": "anime style, studio ghibli, cel shaded, vibrant colors, cute",
    "🖌️ 墨水油画": "oil painting, thick strokes, ink wash, artistic, abstract"
}

st.set_page_config(page_title="Siyua BI Dashboard & Factory", layout="wide", page_icon="📊")

# === 🧠 数据记录核心 ===
def log_job(prompt, style, seed, status, cost_time, filename="N/A"):
    new_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "prompt": prompt,
        "style": style,
        "seed": seed,
        "status": status,
        "cost_time_sec": round(cost_time, 2),
        "filename": filename
    }
    if not os.path.exists(HISTORY_FILE):
        df = pd.DataFrame([new_data])
        df.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    else:
        df = pd.DataFrame([new_data])
        df.to_csv(HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

# === 🎨 UI 主标题 ===
st.title("🏭 Siyua AIGC 智能数据工厂 (v1.5)")

# === 🗂️ 三大功能区 ===
tab1, tab2, tab3 = st.tabs(["🎮 单人控制台", "🚀 批量流水线", "📊 BI 数据看板"])

# --- Tab 1: 单人模式 ---
with tab1:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("指令输入")
        user_prompt = st.text_area("画面描述", value="1girl, looking at viewer", height=100)
        selected_style = st.selectbox("画风选择", list(STYLE_PRESETS.keys()))
        # 增加随机选项
        use_random = st.checkbox("🎲 随机种子", value=True)
        seed_input = st.number_input("固定种子", value=1001, disabled=use_random)
        
        if st.button("✨ 立即生成", type="primary"):
            start_time = time.time()
            agent = ComfyAgent()
            
            # 决定种子
            real_seed = random.randint(1, 10**14) if use_random else seed_input
            
            if agent.is_server_ready():
                try:
                    modifier = WorkflowModifier(TEMPLATE_PATH)
                    final_prompt = f"{user_prompt}, {STYLE_PRESETS[selected_style]}"
                    modifier.update_prompt(NODE_ID_PROMPT, final_prompt)
                    if NODE_ID_SEED in modifier.workflow_data:
                        modifier.workflow_data[NODE_ID_SEED]["inputs"]["seed"] = real_seed
                    
                    success, msg = agent.send_job(modifier.get_workflow())
                    
                    if success:
                        st.success(f"指令发送成功，种子: {real_seed}")
                        bar = st.progress(0)
                        for i in range(100):
                            time.sleep(0.05) 
                            bar.progress(i+1)
                        
                        moved_count = AssetManager(COMFY_OUTPUT_DIR, PROJECT_OUTPUT_DIR).sync_latest_images(time.strftime("%Y%m%d"))
                        cost_time = time.time() - start_time
                        
                        if moved_count > 0:
                            log_job(user_prompt, selected_style, real_seed, "Success", cost_time, f"Single_{moved_count}")
                            st.balloons()
                            st.rerun()
                        else:
                            log_job(user_prompt, selected_style, real_seed, "NoOutput", cost_time)
                            st.warning("⚠️ 未检测到新文件")
                    else:
                        st.error(f"发送失败: {msg}")
                except Exception as e:
                    st.error(f"系统错误: {e}")
            else:
                st.error("无法连接 ComfyUI")

# --- Tab 2: 批量模式 (升级版) ---
with tab2:
    st.subheader("📊 CSV 批量作业")
    
    col_a, col_b = st.columns([2, 1])
    with col_a:
        uploaded_file = st.file_uploader("📂 上传工单文件", type=["csv"])
    with col_b:
        # ✨ 解决“图片一样”的问题
        force_random = st.checkbox("🔥 强制随机化种子", value=True, help="勾选后，将忽略CSV里的种子，全部重新随机生成")
    
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.dataframe(df, use_container_width=True)
        
        if st.button("🚀 启动自动化生产线"):
            agent = ComfyAgent()
            if not agent.is_server_ready():
                st.error("ComfyUI 未启动")
            else:
                progress_bar = st.progress(0)
                status_box = st.empty()
                total_jobs = len(df)
                
                for index, row in df.iterrows():
                    start_time = time.time()
                    
                    current_prompt = str(row['prompt'])
                    style_key = row.get('style', "✨ 通用高画质")
                    style_prompt = STYLE_PRESETS.get(style_key, "")
                    
                    # 种子逻辑：如果强制随机，就随机；否则用CSV里的
                    if force_random:
                        current_seed = random.randint(1, 10**14)
                    else:
                        current_seed = int(row.get('seed', 1001))
                    
                    status_box.info(f"🔄 [{index+1}/{total_jobs}] 生成中: {current_prompt} (Seed: {current_seed})")
                    
                    try:
                        modifier = WorkflowModifier(TEMPLATE_PATH)
                        final_prompt = f"{current_prompt}, {style_prompt}"
                        modifier.update_prompt(NODE_ID_PROMPT, final_prompt)
                        if NODE_ID_SEED in modifier.workflow_data:
                            modifier.workflow_data[NODE_ID_SEED]["inputs"]["seed"] = current_seed
                        
                        success, msg = agent.send_job(modifier.get_workflow())
                        
                        if success:
                            time.sleep(4) # 显卡喘息时间
                            cost_time = time.time() - start_time
                            log_job(current_prompt, style_key, current_seed, "Success", cost_time)
                        else:
                            log_job(current_prompt, style_key, current_seed, "Failed", 0)
                    except Exception as e:
                        log_job(current_prompt, style_key, current_seed, "Error", 0)
                    
                    progress_bar.progress((index + 1) / total_jobs)
                
                time.sleep(2)
                moved = AssetManager(COMFY_OUTPUT_DIR, PROJECT_OUTPUT_DIR).sync_latest_images(time.strftime("%Y%m%d"))
                status_box.success(f"✅ 生产结束！归档 {moved} 张图片。")
                time.sleep(1)
                st.rerun()

# --- Tab 3: BI 数据看板 (这是你的主场) ---
with tab3:
    st.subheader("📈 生产效能分析")
    
    if os.path.exists(HISTORY_FILE):
        # 读取数据
        df_hist = pd.read_csv(HISTORY_FILE)
        
        # 1. KPI 核心指标卡
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("总产出量", f"{len(df_hist)} 张")
        kpi2.metric("平均耗时", f"{df_hist['cost_time_sec'].mean():.2f} 秒")
        
        success_rate = (len(df_hist[df_hist['status']=='Success']) / len(df_hist)) * 100
        kpi3.metric("生产成功率", f"{success_rate:.1f}%")
        
        # 计算今日产量
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_count = len(df_hist[df_hist['timestamp'].str.contains(today_str)])
        kpi4.metric("今日产量", f"{today_count} 张", delta=f"+{today_count}")
        
        st.markdown("---")
        
        # 2. 图表分析区
        c1, c2 = st.columns(2)
        
        with c1:
            st.caption("🎨 风格使用偏好")
            # 统计各风格数量
            style_counts = df_hist['style'].value_counts()
            st.bar_chart(style_counts)
            
        with c2:
            st.caption("⏱️ 生成性能趋势 (最近20单)")
            # 显示最近20条的耗时趋势
            st.line_chart(df_hist.tail(20)['cost_time_sec'])
            
        # 3. 详细数据表
        with st.expander("📄 查看完整生产日志"):
            st.dataframe(df_hist.sort_index(ascending=False), use_container_width=True)
            
    else:
        st.info("暂无历史数据，请先去生产几张图片！")

# --- 公共画廊 (优化版) ---
st.markdown("---")
col_g1, col_g2 = st.columns([4, 1])
with col_g1:
    st.subheader("🖼️ 资产监控")
with col_g2:
    # 增加画廊显示数量控制
    limit_num = st.number_input("显示数量", value=8, min_value=4, max_value=100, step=4)

if st.button("🔄 刷新画廊"):
    st.rerun()

if os.path.exists(PROJECT_OUTPUT_DIR):
    images = [f for f in os.listdir(PROJECT_OUTPUT_DIR) if f.endswith(('.png', '.jpg'))]
    if images:
        images.sort(key=lambda x: os.path.getmtime(os.path.join(PROJECT_OUTPUT_DIR, x)), reverse=True)
        
        # 使用动态数量
        cols = st.columns(4)
        for idx, img in enumerate(images[:limit_num]): 
            with cols[idx % 4]:
                st.image(os.path.join(PROJECT_OUTPUT_DIR, img), caption=img, use_container_width=True)
    else:
        st.info("暂无图片")