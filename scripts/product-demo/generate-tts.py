#!/usr/bin/env python3
"""为每个场景生成普通话男声旁白（Azure Edge TTS · Yunyang 新闻男声）"""
from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "product-demo" / "v2"
VOICE = "zh-CN-YunyangNeural"  # 新闻播报风，标准普通话男声
RATE = "-5%"  # 稍慢，更清晰


async def synth(text: str, mp3: Path) -> None:
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
    await communicate.save(str(mp3))


def duration_seconds(path: Path) -> float:
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


async def main() -> None:
    narr = json.loads((Path(__file__).parent / "narration.json").read_text(encoding="utf-8"))
    scenes_path = OUT / "scenes.json"
    if not scenes_path.exists():
        raise SystemExit(f"缺少 {scenes_path}，请先运行 record-demo.mjs")

    timeline = json.loads(scenes_path.read_text(encoding="utf-8"))
    audio_dir = OUT / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    narr_map = {n["id"]: n["text"] for n in narr}

    for scene in timeline["scenes"]:
        sid = scene["id"]
        text = narr_map.get(sid) or scene.get("text") or scene.get("title") or sid
        mp3 = audio_dir / f"{scene['index']:02d}-{sid}.mp3"
        print(f"TTS {mp3.name} …")
        await synth(text, mp3)
        # wav 便于 ffmpeg concat
        wav = mp3.with_suffix(".wav")
        subprocess.run(
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
            ],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        scene["audio"] = str(wav)
        scene["audio_duration"] = round(duration_seconds(wav), 3)
        print(f"  {scene['audio_duration']}s")

    # CLI / 片头片尾若在 narration 但不在 web scenes，后面 assemble 再补
    timeline_path = OUT / "scenes-with-audio.json"
    timeline_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DONE → {timeline_path}")


if __name__ == "__main__":
    asyncio.run(main())
