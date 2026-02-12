import os
import shutil
import time

class AssetManager:
    """
    负责管理 AIGC 资产（图片）的搬运、归档和清洗。
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
            return 0 # 返回 0 防止报错

        # 1. 获取源目录所有图片文件
        all_files = os.listdir(self.source_dir)
        image_files = [f for f in all_files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]

        if not image_files:
            return 0

        # 2. 搬运逻辑
        moved_count = 0
        for img in image_files:
            src_path = os.path.join(self.source_dir, img)
            
            # 简单策略：只搬运最近 60 秒内生成的文件 (防止把旧图也搬过来)
            # 或者你可以根据 date_str 前缀来判断
            file_mtime = os.path.getmtime(src_path)
            if time.time() - file_mtime < 60: 
                dst_name = f"Bili_Project_{time.strftime('%Y%m%d')}_{img}"
                dst_path = os.path.join(self.target_dir, dst_name)
                
                shutil.move(src_path, dst_path)
                print(f"📦 归档: {img} -> {dst_name}")
                moved_count += 1
        
        if moved_count > 0:
            print(f"🎉 归档完成！共处理 {moved_count} 个资产。")
        
        return moved_count # ⚠️ 关键：app.py 依赖这个返回值