#!/usr/bin/env python3
"""按旁白时长对齐每个场景，合成最终带音视频。"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "product-demo" / "v2"
NARR = Path(__file__).parent / "narration.json"
VOICE_RATE = "-5%"
VOICE = "zh-CN-YunyangNeural"

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
]


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdin=subprocess.DEVNULL)


def duration(path: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(r.stdout.strip())


def load_font(size: int):
    for p in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(p, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_card_png(path: Path, title: str, subtitle: str, size=(1600, 1000)) -> None:
    img = Image.new("RGB", size, (11, 16, 32))
    draw = ImageDraw.Draw(img)
    for y in range(0, size[1], 2):
        shade = 11 + int(10 * (y / size[1]))
        draw.line([(0, y), (size[0], y)], fill=(shade, shade + 4, shade + 18))
    brand = load_font(22)
    title_f = load_font(52)
    sub_f = load_font(26)

    def center(text, font, y, fill=(245, 247, 255)):
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((size[0] - w) / 2, y), text, font=font, fill=fill)

    center("CloudLens", brand, size[1] // 2 - 120, (158, 177, 255))
    center(title, title_f, size[1] // 2 - 48)
    center(subtitle, sub_f, size[1] // 2 + 40, (168, 184, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


async def ensure_tts(text: str, wav: Path) -> float:
    import edge_tts

    wav.parent.mkdir(parents=True, exist_ok=True)
    mp3 = wav.with_suffix(".mp3")
    await edge_tts.Communicate(text, VOICE, rate=VOICE_RATE).save(str(mp3))
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(mp3),
            "-ar",
            "44100",
            "-ac",
            "1",
            str(wav),
        ]
    )
    return duration(wav)


def scene_video_from_frames(scene_dir: Path, frames: list[str], seconds: float, out_mp4: Path) -> None:
    """将若干 PNG 均分铺满旁白时长。"""
    seconds = max(seconds, 2.5)
    paths = [scene_dir / f for f in frames if (scene_dir / f).exists()]
    if not paths:
        raise FileNotFoundError(f"no frames in {scene_dir}")
    # 每帧显示时长
    per = seconds / len(paths)
    list_file = scene_dir / "concat_frames.txt"
    lines = []
    for p in paths:
        lines.append(f"file '{p}'")
        lines.append(f"duration {per:.4f}")
    lines.append(f"file '{paths[-1]}'")  # concat demuxer 需要最后再写一次
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-vf",
            "scale=1600:1000:force_original_aspect_ratio=decrease,pad=1600:1000:(ow-iw)/2:(oh-ih)/2:color=0x0b1020,fps=30",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-t",
            f"{seconds:.3f}",
            str(out_mp4),
        ]
    )


def mux(video: Path, audio: Path, out: Path, seconds: float) -> None:
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            "-t",
            f"{seconds:.3f}",
            "-movflags",
            "+faststart",
            str(out),
        ]
    )


def card_clip(png: Path, wav: Path, out: Path, seconds: float) -> None:
    silent = out.with_name(out.stem + "-silent.mp4")
    run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(png),
            "-t",
            f"{seconds:.3f}",
            "-vf",
            "scale=1600:1000,fps=30",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(silent),
        ]
    )
    mux(silent, wav, out, seconds)


async def main() -> None:
    import asyncio

    narr = {n["id"]: n for n in json.loads(NARR.read_text(encoding="utf-8"))}
    web = json.loads((OUT / "scenes-with-audio.json").read_text(encoding="utf-8"))
    clips_dir = OUT / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    concat_list: list[Path] = []

    # 片头卡（用 intro 旁白，若 web 已有 intro 场景则跳过单独卡）
    concat_list = []
    idx = 0

    for scene in web["scenes"]:
        idx += 1
        sid = scene["id"]
        text = narr.get(sid, {}).get("text") or scene.get("text") or scene.get("title")
        wav = Path(scene["audio"]) if scene.get("audio") else OUT / "audio" / f"{scene['index']:02d}-{sid}.wav"
        if not wav.exists():
            audio_dur = await ensure_tts(text, wav)
        else:
            audio_dur = float(scene.get("audio_duration") or duration(wav))
        seconds = audio_dur + 0.7
        silent = clips_dir / f"{idx:02d}-{sid}-silent.mp4"
        final = clips_dir / f"{idx:02d}-{sid}.mp4"
        scene_video_from_frames(Path(scene["dir"]), scene["frames"], seconds, silent)
        # scene_video_from_frames currently writes to out_mp4 directly as video-only
        # Fix: function writes to out_mp4 - we passed silent
        mux(silent, wav, final, seconds)
        concat_list.append(final)
        print(f"clip {final.name} ({seconds:.1f}s)")

    # CLI 段：用已有 cli-frames + CLI 旁白分段
    cli_frames = ROOT / "artifacts" / "product-demo" / "cli-frames"
    cli_ids = [
        "cli-intro",
        "cli-config",
        "cli-query",
        "cli-analyze",
        "cli-bill",
        "cli-savings",
    ]
    all_cli = sorted(cli_frames.glob("frame-*.png"))
    if all_cli:
        chunk = max(1, len(all_cli) // len(cli_ids))
        for i, cid in enumerate(cli_ids):
            idx += 1
            part = all_cli[i * chunk : (i + 1) * chunk] or all_cli[-1:]
            if i == len(cli_ids) - 1:
                part = all_cli[i * chunk :] or all_cli[-3:]
            tmp_dir = clips_dir / f"cli-{cid}"
            tmp_dir.mkdir(exist_ok=True)
            frames = []
            for j, src in enumerate(part[:8], 1):
                dst = tmp_dir / f"f{j:02d}.png"
                dst.write_bytes(src.read_bytes())
                frames.append(dst.name)
            text = narr[cid]["text"]
            wav = OUT / "audio" / f"cli-{cid}.wav"
            audio_dur = await ensure_tts(text, wav)
            seconds = audio_dur + 0.7
            silent = clips_dir / f"{idx:02d}-{cid}-silent.mp4"
            final = clips_dir / f"{idx:02d}-{cid}.mp4"
            scene_video_from_frames(tmp_dir, frames, seconds, silent)
            mux(silent, wav, final, seconds)
            concat_list.append(final)
            print(f"clip {final.name} ({seconds:.1f}s)")

    # 结束卡
    idx += 1
    outro_png = OUT / "card-outro.png"
    make_card_png(outro_png, "演示结束 · 谢谢观看", "docs/USER_GUIDE.md  |  cloudlens.songqipeng.com")
    wav = OUT / "audio" / "outro.wav"
    audio_dur = await ensure_tts(narr["outro"]["text"], wav)
    seconds = audio_dur + 0.5
    silent = clips_dir / f"{idx:02d}-outro-silent.mp4"
    final = clips_dir / f"{idx:02d}-outro.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(outro_png),
            "-t",
            f"{seconds:.3f}",
            "-vf",
            "scale=1600:1000,fps=30",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(silent),
        ]
    )
    mux(silent, wav, final, seconds)
    concat_list.append(final)

    list_path = OUT / "concat-v2.txt"
    list_path.write_text("\n".join(f"file '{p}'" for p in concat_list) + "\n", encoding="utf-8")
    final_out = ROOT / "artifacts" / "product-demo" / "CloudLens-产品使用演示.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(final_out),
        ]
    )
    print(f"DONE {final_out} duration={duration(final_out):.1f}s")


if __name__ == "__main__":
    import asyncio

    # fix scene_video_from_frames to write to given out path
    asyncio.run(main())
