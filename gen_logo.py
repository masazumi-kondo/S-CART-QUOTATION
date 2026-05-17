#!/usr/bin/env python3
"""Generate high-quality MUSASHI logo PNG"""

from PIL import Image, ImageDraw, ImageFont
import os

# 正式MUSASHIロゴ画像を高品質で生成
# 画像サイズ: 480x120 (高解像度)
img = Image.new('RGB', (480, 120), color='white')
draw = ImageDraw.Draw(img)

# 赤色 (#E31A24)
red = (227, 26, 36)
black = (0, 0, 0)

# ロゴシンボル：横に並んだ楕円
# 複雑な交差パターンを描画
symbol_positions = [
    # (x, y_top_offset, y_bottom_offset)
    (15, 15, 50),   # 1つ目の円グループ
    (45, 15, 50),   # 2つ目
    (75, 15, 50),   # 3つ目
    (30, 50, 85),   # 下段左
    (60, 50, 85),   # 下段右
]

circle_radius = 15

# より正確なロゴシンボル描画
for i in range(4):
    x_center = 30 + i * 30
    # 上の円
    draw.ellipse(
        [x_center - circle_radius, 20 - circle_radius, 
         x_center + circle_radius, 20 + circle_radius],
        outline=red, width=4
    )
    # 下の円（重複配置）
    draw.ellipse(
        [x_center + 15 - circle_radius, 65 - circle_radius,
         x_center + 15 + circle_radius, 65 + circle_radius],
        outline=red, width=4
    )

# MUSASHI テキスト（大きなフォント）
try:
    font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 70)
except:
    try:
        font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 48)
    except:
        font = ImageFont.load_default()

text_x = 180
text_y = 20
draw.text((text_x, text_y), "MUSASHI", fill=black, font=font)

# 保存
output_path = 'app/static/img/musashi-logo.png'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
img.save(output_path, 'PNG')

# 統計出力
file_size = os.path.getsize(output_path)
print(f'✓ Logo created: {output_path}')
print(f'  File size: {file_size} bytes')
print(f'  Image size: {img.size[0]}x{img.size[1]} pixels')
