import streamlit as st
import os
import time
import pandas as pd
import random
import json
from datetime import datetime
from src.data_processor import WorkflowModifier
from src.comfy_client import ComfyAgent
from src.file_manager import AssetManager
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True  # 允许加载截断的图片文件

# === ⚙️ 配置区 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "config", "workflow_api.json")
PROJECT_OUTPUT_DIR = os.path.join(BASE_DIR, "output")
HISTORY_FILE = os.path.join(BASE_DIR, "history.csv")
JOBS_FILE = os.path.join(BASE_DIR, "jobs.csv") # 👈 任务清单文件

# ⚠️ 路径配置
COMFY_MODELS_DIR = r"M:\models\checkpoints"
COMFY_LORAS_DIR = r"M:\models\loras"
COMFY_CN_DIR = r"M:\models\controlnet"
COMFY_UPSCALE_DIR = r"M:\models\upscale_models"
COMFY_INPUT_DIR = r"D:\ComfyUI_Main\ComfyUI-aki-v3\ComfyUI-aki-v3\ComfyUI\input"
COMFY_OUTPUT_DIR = r"D:\ComfyUI_Main\ComfyUI-aki-v3\ComfyUI-aki-v3\ComfyUI\output"

# 🔗 节点 ID
NODE_ID_PROMPT = "6"
NODE_ID_NEGATIVE = "7"
NODE_ID_KSAMPLER = "3"
NODE_ID_KSAMPLER_2 = "18" # 第二遍采样的采样器
NODE_ID_CHECKPOINT = "4"
NODE_ID_EMPTY_LATENT = "5"
NODE_ID_LORA = "10"
NODE_ID_CN_LOADER = "11"
NODE_ID_CN_IMAGE = "13"
NODE_ID_UPSCALE_LOADER = "15"
NODE_ID_UPSCALE_IMAGE = "16"
NODE_ID_SAVE_IMAGE = "9"

RATIO_PRESETS = {"1:1 方形头像": (512, 512), "3:4 小红书": (512, 680), "16:9 壁纸": (912, 512)}
STYLE_PRESETS = {
    "✨ 通用高画质": "masterpiece, best quality, 8k",
    "🤖 赛博朋克": "cyberpunk, neon lights, sci-fi",
    "🦁 霸气线稿风": "intricate details, majestic, ink sketch style, 8k",
    "📸 真实摄影": "photorealistic, raw photo, dslr, soft lighting"
}
DEFAULT_NEGATIVE = "embedding:EasyNegative, nsfw, lowres, bad anatomy, bad hands, text, error, blurry"

st.set_page_config(page_title="Siyua AIGC Factory v2.3", layout="wide", page_icon="🏭")

def get_files(directory, extensions):
    if not os.path.exists(directory): return []
    return [f for f in os.listdir(directory) if f.endswith(extensions)]

def log_job(prompt, style, seed, status, cost_time, filename="N/A"):
    new_data = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "prompt": prompt, "style": style, "seed": seed, "status": status, "cost_time_sec": round(cost_time, 2), "filename": filename}
    if not os.path.exists(HISTORY_FILE): pd.DataFrame([new_data]).to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    else: pd.DataFrame([new_data]).to_csv(HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

# === 核心逻辑函数：生成单张图 ===
def generate_image(prompt, neg_prompt, width, height, ckpt, lora, lora_str, cn, cn_img, upscale, upscale_model, seed, filename_prefix):
    agent = ComfyAgent()
    if not agent.is_server_ready(): return False, "ComfyUI 未启动"
    
    try:
        mod = WorkflowModifier(TEMPLATE_PATH)
        # 1. 基础设置
        mod.update_prompt(NODE_ID_PROMPT, prompt)
        if NODE_ID_NEGATIVE: mod.update_prompt(NODE_ID_NEGATIVE, neg_prompt)
        if NODE_ID_CHECKPOINT: mod.workflow_data[NODE_ID_CHECKPOINT]["inputs"]["ckpt_name"] = ckpt
        if NODE_ID_EMPTY_LATENT: 
            mod.workflow_data[NODE_ID_EMPTY_LATENT]["inputs"]["width"] = width
            mod.workflow_data[NODE_ID_EMPTY_LATENT]["inputs"]["height"] = height
        
        # 2. 文件名前缀 (Tier 7 核心)
        if NODE_ID_SAVE_IMAGE:
            mod.workflow_data[NODE_ID_SAVE_IMAGE]["inputs"]["filename_prefix"] = filename_prefix

        # 3. LoRA
        if NODE_ID_LORA:
            valid_loras = [f for f in get_files(COMFY_LORAS_DIR, (".safetensors", ".ckpt"))]
            dummy = valid_loras[0] if valid_loras else "blindbox_v1_mix.safetensors"
            mod.workflow_data[NODE_ID_LORA]["inputs"]["lora_name"] = lora if lora != "None" else dummy
            strength = lora_str if lora != "None" else 0
            mod.workflow_data[NODE_ID_LORA]["inputs"]["strength_model"] = strength
            mod.workflow_data[NODE_ID_LORA]["inputs"]["strength_clip"] = strength

        # 4. ControlNet
        if NODE_ID_CN_LOADER and cn != "None":
            mod.workflow_data[NODE_ID_CN_LOADER]["inputs"]["control_net_name"] = cn
            if NODE_ID_CN_IMAGE and cn_img:
                mod.workflow_data[NODE_ID_CN_IMAGE]["inputs"]["image"] = cn_img
        elif NODE_ID_CN_LOADER:
             if "inputs" in mod.workflow_data.get("12", {}): mod.workflow_data["12"]["inputs"]["strength"] = 0

        # 5. Upscale
        # 5. Upscale 动态路由 (核心修复)
        # 如果启用放大：SaveImage -> Node 19 (高清解码)
        # 如果关闭放大：SaveImage -> Node 8 (基础解码)
        if upscale and upscale_model:
            mod.workflow_data[NODE_ID_UPSCALE_LOADER]["inputs"]["model_name"] = upscale_model
            mod.workflow_data[NODE_ID_SAVE_IMAGE]["inputs"]["images"] = ["19", 0]
            # 确保第二遍采样器的降噪不为0
            if NODE_ID_KSAMPLER_2 in mod.workflow_data:
                mod.workflow_data[NODE_ID_KSAMPLER_2]["inputs"]["denoise"] = 0.5
        else:
            # 关键：当不放大时，必须跳过高清流程，直接连到基础解码
            mod.workflow_data[NODE_ID_SAVE_IMAGE]["inputs"]["images"] = ["8", 0]
            # 可选优化：关闭放大时，让第二遍采样器跑 0 步以节省资源（或直接不管它，因为输出已重定向）
            if NODE_ID_KSAMPLER_2 in mod.workflow_data:
                mod.workflow_data[NODE_ID_KSAMPLER_2]["inputs"]["steps"] = 0
        
        # 6. 种子 (处理所有采样器)
        final_seed = seed if seed != -1 else random.randint(1, 10**14)
        if NODE_ID_KSAMPLER: mod.workflow_data[NODE_ID_KSAMPLER]["inputs"]["seed"] = final_seed
        if NODE_ID_KSAMPLER_2: mod.workflow_data[NODE_ID_KSAMPLER_2]["inputs"]["seed"] = final_seed

        # 发送任务
        succ, msg = agent.send_job(mod.get_workflow())
        return succ, msg, final_seed

    except Exception as e: return False, str(e), 0


st.title("🏭 Siyua AIGC 智能数据工厂 (v2.3 批量完全体)")

with st.sidebar:
    st.header("⚙️ 引擎室")
    ckpt_list = get_files(COMFY_MODELS_DIR, (".safetensors", ".ckpt"))
    selected_ckpt = st.selectbox("🧠 核心模型", ckpt_list if ckpt_list else ["无模型"])
    
    st.markdown("---")
    enable_upscale = st.checkbox("启用 2x 放大 (Tier 6)", value=True)
    upscale_list = get_files(COMFY_UPSCALE_DIR, (".pth", ".pt"))
    selected_upscaler = st.selectbox("放大模型", upscale_list if upscale_list else ["无模型"]) if enable_upscale else None

    st.markdown("---")
    lora_list = ["None"] + get_files(COMFY_LORAS_DIR, (".safetensors", ".ckpt"))
    selected_lora = st.selectbox("选择 LoRA", lora_list)
    lora_strength = st.slider("LoRA 权重", 0.0, 2.0, 1.0, 0.1) if selected_lora != "None" else 0
    
    st.markdown("---")
    cn_list = ["None"] + get_files(COMFY_CN_DIR, (".safetensors", ".ckpt"))
    def format_cn_name(filename):
        if filename == "None": return "🚫 关闭 (None)"
        
        name = filename.lower()
        # === 完整匹配字典 ===
        if "canny" in name:    return "🖍️ Canny (线稿)"
        if "depth" in name:    return "🗿 Depth (深度图)"
        if "openpose" in name: return "🦴 OpenPose (姿态)"
        if "softedge" in name: return "☁️ SoftEdge (柔边)"
        if "lineart" in name:  return "✏️ Lineart (艺术线)"
        if "scribble" in name: return "🖌️ Scribble (涂鸦)"
        if "tile" in name:     return "🧱 Tile (细节增强)"
        if "inpaint" in name:  return "🩹 Inpaint (局部重绘)"
        if "ip2p" in name:     return "✨ IP2P (指令替换)"
        if "shuffle" in name:  return "🔀 Shuffle (随机重组)"
        if "mlsd" in name:     return "📐 MLSD (建筑线稿)"
        if "normal" in name:   return "🔮 Normal (法线贴图)"
        if "seg" in name:      return "🧩 Seg (语义分割)"
        
        # 没见过的模型，只显示文件名（去掉后缀）
        return f"📄 {filename.split('.')[0]}"
    selected_cn = st.selectbox("选择 CN", cn_list, format_func=format_cn_name)
    
    st.markdown("---")
    ratio_name = st.selectbox("比例", list(RATIO_PRESETS.keys()))
    width, height = RATIO_PRESETS[ratio_name]

tab1, tab2, tab3 = st.tabs(["🎮 单人控制台", "🚀 批量流水线", "📊 画廊"])

# === Tab 1: 单人控制台 (逻辑不变，调用封装函数) ===
with tab1:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("指令")
        prompt = st.text_area("正向 Prompt", "1girl, full body", height=80)
        neg_prompt = st.text_area("负向 Prompt", DEFAULT_NEGATIVE, height=80)
        style = st.selectbox("风格", list(STYLE_PRESETS.keys()))
        
        cn_image_name = None
        if selected_cn != "None":
            uploaded_cn_img = st.file_uploader("📤 上传参考图", type=["png", "jpg"], key="tab1_upload")
            if uploaded_cn_img:
                st.image(uploaded_cn_img, width=200)
                cn_image_name = f"CN_{int(time.time())}_{uploaded_cn_img.name}"
                with open(os.path.join(COMFY_INPUT_DIR, cn_image_name), "wb") as f: f.write(uploaded_cn_img.getbuffer())

        if st.button("✨ 启动单人任务", type="primary"):
            full_prompt = f"{prompt}, {STYLE_PRESETS[style]}"
            succ, msg, seed = generate_image(full_prompt, neg_prompt, width, height, selected_ckpt, selected_lora, lora_strength, selected_cn, cn_image_name, enable_upscale, selected_upscaler, -1, "Single_Task")
            
            if succ:
                progress_text = st.empty()
                bar = st.progress(0)
                manager = AssetManager(COMFY_OUTPUT_DIR, PROJECT_OUTPUT_DIR)
                max_wait = 300 
                for i in range(max_wait):
                    progress_text.text(f"AI 绘图中... {i}s")
                    moved = manager.sync_latest_images()
                    if moved > 0: bar.progress(100); break
                    time.sleep(1)
                    bar.progress(min(int((i/max_wait)*90), 90))
                
                if moved: 
                    st.balloons(); st.rerun()
                else: st.warning("等待超时")
            else: st.error(msg)

# === Tab 2: 批量流水线 (Tier 7 核心) ===
with tab2:
    st.subheader("🏭 批量生产车间")
    
    # 1. 任务预览
    if os.path.exists(JOBS_FILE):
        
        df_jobs = pd.read_csv(JOBS_FILE, quotechar='"', skipinitialspace=True)
        # 强制 seed 列为整数，NaN 转为 -1
        df_jobs['seed'] = pd.to_numeric(df_jobs['seed'], errors='coerce').fillna(-1).astype(int)
        st.dataframe(df_jobs, use_container_width=True)
        st.info(f"📋 检测到 {len(df_jobs)} 个待办任务")
    else:
        st.error("❌ 未找到 jobs.csv，请在项目根目录创建")
        st.stop()

    # 2. ControlNet 统一设置 (批量模式下通常用同一张骨架图，或者不开启)
    cn_batch_img = None
    if selected_cn != "None":
        st.warning(f"⚠️ 批量模式已启用 ControlNet: {format_cn_name(selected_cn)}。所有任务将使用同一张参考图。")
        uploaded_cn_img_batch = st.file_uploader("📤 上传批量参考图", type=["png", "jpg"], key="tab2_upload")
        if uploaded_cn_img_batch:
            st.image(uploaded_cn_img_batch, width=150)
            cn_batch_img = f"CN_Batch_{int(time.time())}_{uploaded_cn_img_batch.name}"
            with open(os.path.join(COMFY_INPUT_DIR, cn_batch_img), "wb") as f: f.write(uploaded_cn_img_batch.getbuffer())
    
    # 3. 启动按钮
    if st.button("🚀 启动批量流水线", type="primary"):
        batch_bar = st.progress(0)
        status_text = st.empty()
        manager = AssetManager(COMFY_OUTPUT_DIR, PROJECT_OUTPUT_DIR)
        
        total_jobs = len(df_jobs)
        success_count = 0
        
        # 🛡️ 安全升级：使用 enumerate 生成独立的序号 i，无视 DataFrame 索引格式
        for i, (index, row) in enumerate(df_jobs.iterrows()):
            job_prompt = str(row['prompt'])
            job_filename = str(row['filename'])
            # 安全获取 seed，防止空值报错
            try:
                job_seed = int(row['seed'])
            except:
                job_seed = -1
            
            # 这里改成 i+1，绝对是整数，绝不会报错
            status_text.text(f"正在处理: {job_filename} ({i+1}/{total_jobs})...")
            
            # 调用生成函数
            succ, msg, used_seed = generate_image(
                prompt=job_prompt,
                neg_prompt=DEFAULT_NEGATIVE, 
                width=width, height=height,
                ckpt=selected_ckpt,
                lora=selected_lora, lora_str=lora_strength,
                cn=selected_cn, cn_img=cn_batch_img,
                upscale=enable_upscale, upscale_model=selected_upscaler,
                seed=job_seed,
                filename_prefix=job_filename
            )
            
            # 更新进度条
            batch_bar.progress(int((i + 1) / total_jobs * 100))
            
            
            
            if succ:
                # 等待单张图完成
                wait_success = False
                for i in range(300): # 每张图最多等 300秒
                    moved = manager.sync_latest_images()
                    if moved > 0: wait_success = True; break
                    time.sleep(1)
                
                if wait_success:
                    success_count += 1
                    log_job(job_prompt, "Batch", used_seed, "Success", 0, job_filename)
                else:
                    st.error(f"任务 {job_filename} 超时")
            else:
                st.error(f"任务 {job_filename} 失败: {msg}")
            
            # 更新总进度条
            batch_bar.progress(int((index + 1) / total_jobs * 100))
        
        st.success(f"🎉 批量任务结束！成功: {success_count}/{total_jobs}")
        st.balloons()
        time.sleep(2)
        st.rerun()

# === Tab 3 修复版 ===
with tab3:
    st.subheader("🖼️ 资产监控")
    limit_num = st.number_input("数量", 8, step=4)
    if st.button("🔄 刷新"): st.rerun()
    
    if os.path.exists(PROJECT_OUTPUT_DIR):
        imgs = sorted(
            [f for f in os.listdir(PROJECT_OUTPUT_DIR) if f.endswith('.png')], 
            key=lambda x: os.path.getmtime(os.path.join(PROJECT_OUTPUT_DIR, x)), 
            reverse=True
        )
        
        cols = st.columns(4)
        for i, img in enumerate(imgs[:limit_num]):
            with cols[i % 4]:
                img_path = os.path.join(PROJECT_OUTPUT_DIR, img)
                try:
                    # 增加防御：尝试打开图片，如果失败则跳过
                    with Image.open(img_path) as verified_img:
                        st.image(verified_img, caption=img, use_container_width=True)
                except Exception:
                    # 如果文件正在被占用或损坏，显示占位符或直接跳过
                    st.warning(f"⏳ 加载中: {img[:10]}...")