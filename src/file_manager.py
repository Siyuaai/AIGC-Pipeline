import os
import shutil
import time

class AssetManager:
    """
    负责管理 AIGC 资产（图片）的搬运、归档和清洗。
    v1.2: 修复同名覆盖 BUG，增加精确时间戳
    """
    def __init__(self, comfy_output_dir, project_output_dir):
        self.source_dir = comfy_output_dir
        self.target_dir = project_output_dir
        
        # 如果目标目录不存在，自动创建
        if not os.path.exists(self.target_dir):
            os.makedirs(self.target_dir)

    def sync_latest_images(self, date_str=None):
        """
        将 ComfyUI 输出目录中的最新图片搬运到项目目录。
        """
        if not os.path.exists(self.source_dir):
            print(f"⚠️ 警告：源目录不存在 -> {self.source_dir}")
            return 0

        # 1. 获取源目录所有图片文件
        all_files = os.listdir(self.source_dir)
        image_files = [f for f in all_files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]

        if not image_files:
            return 0

        # 2. 搬运逻辑
        moved_count = 0
        current_time_str = time.strftime('%H%M%S') # 获取当前 时分秒 (例如 110523)
        
        for img in image_files:
            src_path = os.path.join(self.source_dir, img)
            
            # 只搬运最近 60 秒内生成的文件
            file_mtime = os.path.getmtime(src_path)
            if time.time() - file_mtime < 60: 
                # ✨ 核心修复：文件名加入 时分秒(current_time_str) 防止覆盖
                # 新格式：Bili_Project_20260212_110523_ComfyUI_00001_.png
                dst_name = f"Bili_Project_{time.strftime('%Y%m%d')}_{current_time_str}_{img}"
                dst_path = os.path.join(self.target_dir, dst_name)
                
                # 为了防止极短时间内处理多张图导致秒数也一样，再加个保险
                if os.path.exists(dst_path):
                    # 如果这秒钟已经有个同名文件了，就加个随机尾巴
                    dst_name = f"Bili_Project_{time.strftime('%Y%m%d')}_{current_time_str}_{int(time.time()*1000)%1000}_{img}"
                    dst_path = os.path.join(self.target_dir, dst_name)

                try:
                    shutil.move(src_path, dst_path)
                    print(f"📦 归档: {img} -> {dst_name}")
                    moved_count += 1
                except Exception as e:
                    print(f"❌ 搬运失败 {img}: {e}")
        
        return moved_count