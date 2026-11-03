#!/usr/bin/env python3
"""生成演示片头/章节卡 PNG（不依赖 ffmpeg drawtext）"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[2] / "artifacts" / "product-demo"
OUT.mkdir(parents=True, exist_ok=True)

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_card(filename: str, title: str, subtitle: str, size=(1600, 1000)) -> Path:
    img = Image.new("RGB", size, (11, 16, 32))
    draw = ImageDraw.Draw(img)
    # 轻微渐变条
    for y in range(0, size[1], 2):
        shade = 11 + int(10 * (y / size[1]))
        draw.line([(0, y), (size[0], y)], fill=(shade, shade + 4, shade + 18))

    title_font = load_font(54)
    sub_font = load_font(28)
    brand_font = load_font(22)

    def center_text(text: str, font, y: int, fill=(245, 247, 255)):
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((size[0] - w) / 2, y), text, font=font, fill=fill)

    center_text("CloudLens", brand_font, size[1] // 2 - 120, fill=(158, 177, 255))
    center_text(title, title_font, size[1] // 2 - 50)
    center_text(subtitle, sub_font, size[1] // 2 + 40, fill=(168, 184, 255))

    path = OUT / filename
    img.save(path)
    return path


def main() -> None:
    cards = [
        ("card-intro.png", "产品使用演示", "Web 全功能 + CLI 核心功能  |  现有账号数据"),
        ("card-web.png", "第一部分 · Web 控制台", "仪表盘 / 资源 / 成本 / 折扣 / 省钱机会 / 安全 / 报告 / 设置"),
        ("card-cli.png", "第二部分 · CLI 命令行", "config / query / analyze / bill / savings"),
        ("card-outro.png", "演示结束 · 谢谢观看", "docs/USER_GUIDE.md  |  cloudlens.songqipeng.com"),
    ]
    for name, title, sub in cards:
        p = make_card(name, title, sub)
        print(p)


if __name__ == "__main__":
    main()
