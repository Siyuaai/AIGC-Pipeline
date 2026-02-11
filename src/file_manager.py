import os
import shutil
import time
from pathlib import Path

class AssetManager:
    """
    负责文件的搬运、清洗和归档。
    """
    def __init__(self, comfy_output_dir, project_output_dir):
        self.source_dir = Path(comfy_output_dir)
        self.target_dir = Path(project_output_dir)
        
        # 自动创建输出目录
        if not self.target_dir.exists():
            self.target_dir.mkdir(parents=True)

    def sync_latest_images(self, batch_date_str):
        """
        从 ComfyUI 输出目录搬运最新的图片到项目目录
        """
        print(f"🧹 开始归档图片资产...")
        
        # 1. 扫描源文件夹
        if not self.source_dir.exists():
            print(f"❌ 找不到 ComfyUI 输出目录: {self.source_dir}")
            return

        moved_count = 0
        
        # 2. 遍历并搬运
        # 实际生产中，我们会对比文件创建时间，只搬运刚才生成的
        # 这里为了演示简单，我们搬运所有以 ComfyUI_ 开头的临时文件
        for file_item in self.source_dir.iterdir():
            if file_item.is_file() and file_item.name.startswith("ComfyUI_"):
                # 构建新名字: Bili_Project_YYYYMMDD_001.png
                new_name = f"Bili_Project_{batch_date_str}_{moved_count+1:03d}{file_item.suffix}"
                target_path = self.target_dir / new_name
                
                try:
                    # 移动文件 (Move) - 相当于剪切粘贴
                    shutil.move(str(file_item), str(target_path))
                    print(f"📦 归档: {file_item.name} -> {new_name}")
                    moved_count += 1
                except Exception as e:
                    print(f"⚠️ 搬运失败: {e}")
        
        print(f"🎉 归档完成！共处理 {moved_count} 个资产。\n查看路径: {self.target_dir}")