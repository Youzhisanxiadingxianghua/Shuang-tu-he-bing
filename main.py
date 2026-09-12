import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageOps
import struct
import zlib
import os


def _make_chunk(chunk_type, data):
    """构造一个 PNG 数据块：长度(4) + 类型(4) + 数据 + CRC(4)"""
    length = struct.pack('>I', len(data))
    chunk_type_bytes = chunk_type.encode('ascii')
    crc = zlib.crc32(chunk_type_bytes + data) & 0xffffffff
    return length + chunk_type_bytes + data + struct.pack('>I', crc)


def _image_to_raw_data(img):
    """把 PIL 图像转成 PNG 原始扫描线数据（每行开头加一个过滤器字节 0）"""
    width, height = img.size
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    raw = img.tobytes()
    row_bytes = width * 4
    out = bytearray()
    for y in range(height):
        out.append(0)  # 过滤器类型：None
        out.extend(raw[y * row_bytes:(y + 1) * row_bytes])
    return bytes(out)


def build_apng(cover_path, content_path, output_path,
               num_content_frames=3, max_size=1080):
    """
    生成一个 APNG：
      - 封面图 -> IDAT（默认静态图，只做缩略图，不参与动画）
      - 内容图 -> 动画帧（fdAT），每帧延迟 65535 秒
      - 只播放一次（num_plays=1），播完停在内容图上
    """
    img_cover = Image.open(cover_path).convert('RGBA')
    img_content = Image.open(content_path).convert('RGBA')

    # 以内容图尺寸为基准，统一尺寸
    target_size = img_content.size
    if max(target_size) > max_size:
        scale = max_size / max(target_size)
        new_size = (int(target_size[0] * scale), int(target_size[1] * scale))
        img_cover = img_cover.resize(new_size, Image.Resampling.LANCZOS)
        img_content = img_content.resize(new_size, Image.Resampling.LANCZOS)
        target_size = new_size

    # 封面图等比缩放 + 居中透明填充
    img_cover = ImageOps.pad(img_cover, target_size, color=(0, 0, 0, 0),
                             method=Image.Resampling.LANCZOS)

    width, height = target_size

    # 生成内容帧：每帧微调一个像素，防止播放器做“重复帧合并”
    frames = []
    for i in range(num_content_frames):
        frame = img_content.copy()
        if i > 0:
            r, g, b, a = frame.getpixel((0, 0))
            frame.putpixel((0, 0), ((r + i * 17) % 256, g, b, a))
        frames.append(frame)

    out = bytearray()

    # 1. PNG 文件头
    out.extend(b'\x89PNG\r\n\x1a\n')

    # 2. IHDR
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    out.extend(_make_chunk('IHDR', ihdr))

    # 3. acTL：帧数 = 内容帧数，播放次数 = 1（只播放一次）
    actl = struct.pack('>II', len(frames), 1)
    out.extend(_make_chunk('acTL', actl))

    # 4. IDAT：封面图（默认静态图，不是动画帧）
    out.extend(_make_chunk('IDAT', zlib.compress(_image_to_raw_data(img_cover), 9)))

    # 5. 动画帧：fcTL + fdAT
    seq = 0
    for frame in frames:
        # fcTL：delay_num=65535, delay_den=1 -> 每帧延迟 65535 秒
        fctl = struct.pack('>IIIIIHHBB',
                           seq,          # 序列号
                           width, height,
                           0, 0,          # x_offset, y_offset
                           65535, 1,      # delay_num, delay_den
                           0,             # dispose_op = NONE
                           0)             # blend_op = SOURCE
        out.extend(_make_chunk('fcTL', fctl))
        seq += 1

        # fdAT：序列号 + 压缩后的扫描线数据
        fdat = struct.pack('>I', seq) + zlib.compress(_image_to_raw_data(frame), 9)
        out.extend(_make_chunk('fdAT', fdat))
        seq += 1

    # 6. IEND
    out.extend(_make_chunk('IEND', b''))

    with open(output_path, 'wb') as f:
        f.write(out)


class APNGMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("双图APNG合并工具")
        self.root.geometry("520x330")

        self.cover_path = tk.StringVar()
        self.content_path = tk.StringVar()
        self.output_path = tk.StringVar()

        tk.Label(root, text="封面图 (缩略图，不参与动画):", font=("Arial", 10)).pack(pady=5)
        tk.Entry(root, textvariable=self.cover_path, width=55).pack()
        tk.Button(root, text="选择封面图", command=self.select_cover).pack(pady=2)

        tk.Label(root, text="内容图 (点开后显示):", font=("Arial", 10)).pack(pady=5)
        tk.Entry(root, textvariable=self.content_path, width=55).pack()
        tk.Button(root, text="选择内容图", command=self.select_content).pack(pady=2)

        tk.Label(root, text="保存为:", font=("Arial", 10)).pack(pady=5)
        tk.Entry(root, textvariable=self.output_path, width=55).pack()
        tk.Button(root, text="选择保存路径", command=self.select_output).pack(pady=2)

        tk.Button(root, text="开始合并", command=self.merge_images, bg="#4CAF50",
                  fg="white", font=("Arial", 10, "bold"), width=15).pack(pady=15)

    def select_cover(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg")])
        if path:
            self.cover_path.set(path)

    def select_content(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg")])
        if path:
            self.content_path.set(path)

    def select_output(self):
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG files", "*.png")])
        if path:
            self.output_path.set(path)

    def merge_images(self):
        cover = self.cover_path.get()
        content = self.content_path.get()
        output = self.output_path.get()

        if not cover or not content or not output:
            messagebox.showerror("错误", "请完整选择封面图、内容图和保存路径！")
            return

        try:
            build_apng(cover, content, output)
            messagebox.showinfo("成功", f"合并成功！\n文件已保存至:\n{output}")
        except Exception as e:
            messagebox.showerror("错误", f"合并失败: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = APNGMergerApp(root)
    root.mainloop()