import tkinter as tk
from tkinter import filedialog, messagebox
from apng import APNG
from PIL import Image, ImageOps
import os

class APNGMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("双图APNG合并工具")
        self.root.geometry("520x330")
        
        self.cover_path = tk.StringVar()
        self.content_path = tk.StringVar()
        self.output_path = tk.StringVar()

        # 界面布局
        tk.Label(root, text="封面图 (第一帧, QQ里缩略图):", font=("Arial", 10)).pack(pady=5)
        tk.Entry(root, textvariable=self.cover_path, width=55).pack()
        tk.Button(root, text="选择封面图", command=self.select_cover).pack(pady=2)

        tk.Label(root, text="内容图 (第二帧, 点开后显示):", font=("Arial", 10)).pack(pady=5)
        tk.Entry(root, textvariable=self.content_path, width=55).pack()
        tk.Button(root, text="选择内容图", command=self.select_content).pack(pady=2)

        tk.Label(root, text="保存为:", font=("Arial", 10)).pack(pady=5)
        tk.Entry(root, textvariable=self.output_path, width=55).pack()
        tk.Button(root, text="选择保存路径", command=self.select_output).pack(pady=2)

        # 合并按钮
        tk.Button(root, text="开始合并", command=self.merge_images, bg="#4CAF50", fg="white", 
                  font=("Arial", 10, "bold"), width=15).pack(pady=15)

    def select_cover(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg")])
        if path:
            self.cover_path.set(path)

    def select_content(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg")])
        if path:
            self.content_path.set(path)

    def select_output(self):
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if path:
            self.output_path.set(path)

    def merge_images(self):
        cover = self.cover_path.get()
        content = self.content_path.get()
        output = self.output_path.get()

        if not cover or not content or not output:
            messagebox.showerror("错误", "请完整选择封面图、内容图和保存路径！")
            return

        # 临时文件名
        temp_cover = "temp_cover_resized.png"
        temp_content = "temp_content_resized.png"

        try:
            # --- 1. 图片处理阶段：统一尺寸 ---
            img_cover = Image.open(cover).convert("RGBA")
            img_content = Image.open(content).convert("RGBA")

            # 以内容图的尺寸为基准（保证大图清晰度）
            target_size = img_content.size

            # 限制最大边长，防止生成的文件过大 QQ 发不出去
            max_size = 1080
            if max(target_size) > max_size:
                scale = max_size / max(target_size)
                new_size = (int(target_size[0] * scale), int(target_size[1] * scale))
                img_cover = img_cover.resize(new_size, Image.Resampling.LANCZOS)
                img_content = img_content.resize(new_size, Image.Resampling.LANCZOS)
                target_size = new_size

            # 将封面图等比缩放，并居中填充透明背景，使其尺寸与内容图完全一致
            img_cover_fitted = ImageOps.pad(img_cover, target_size, color=(0, 0, 0, 0), method=Image.Resampling.LANCZOS)

            # 保存处理后的临时图片
            img_cover_fitted.save(temp_cover, format="PNG")
            img_content.save(temp_content, format="PNG")

            # --- 2. 生成 APNG ---
            im = APNG()
            
            # 第一帧（封面）：延迟 10 毫秒
            im.append_file(temp_cover, delay=10)
            
            # 第二帧（内容）：延迟 65535 毫秒（约 65.5 秒，APNG 单帧上限）
            # 重复添加 30 次，总时长约 32 分钟，防止立刻循环回第一帧
            repeat_times = 30
            for _ in range(repeat_times):
                im.append_file(temp_content, delay=65535)
            
            # 保存最终文件
            im.save(output)

            # 清理临时文件
            os.remove(temp_cover)
            os.remove(temp_content)

            messagebox.showinfo("成功", f"合并成功！\n文件已保存至:\n{output}\n\n提示：生成的文件可能较大，发送前请先测试。")
        except Exception as e:
            # 发生错误时也要清理临时文件
            if os.path.exists(temp_cover): os.remove(temp_cover)
            if os.path.exists(temp_content): os.remove(temp_content)
            messagebox.showerror("错误", f"合并失败: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = APNGMergerApp(root)
    root.mainloop()