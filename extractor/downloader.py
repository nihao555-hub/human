"""基于 yt-dlp 的社媒链接解析与音频下载。

支持抖音 / 快手 / B站 / TikTok / YouTube 等 yt-dlp 覆盖的站点。
部分平台（抖音、B站海外 IP）需要 Cookie 才能稳定下载，
可传入 Netscape 格式 cookies.txt 或指定从浏览器读取。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yt_dlp

URL_RE = re.compile(r"https?://[^\s\u4e00-\u9fff，。；！？、]+")


@dataclass
class DownloadResult:
    audio_path: Path
    title: str
    duration: float | None
    uploader: str | None
    webpage_url: str
    platform: str | None


def extract_url(text: str) -> str:
    """从用户粘贴的分享文本中提取第一个 URL（抖音分享口令常混杂中文）。"""
    match = URL_RE.search(text)
    if not match:
        raise ValueError(f"未在输入中找到链接: {text!r}")
    return match.group(0)


def download_audio(
    url_or_text: str,
    out_dir: str | Path = "downloads",
    cookies_file: str | Path | None = None,
    cookies_from_browser: str | None = None,
) -> DownloadResult:
    """解析链接并下载音频（m4a/mp3），返回本地路径与元信息。"""
    url = extract_url(url_or_text)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts: dict = {
        "format": "bestaudio/best",
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
            }
        ],
    }
    if cookies_file:
        ydl_opts["cookiefile"] = str(cookies_file)
    if cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (cookies_from_browser,)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    audio_path = out_dir / f"{info['id']}.m4a"
    if not audio_path.exists():
        candidates = sorted(out_dir.glob(f"{info['id']}.*"))
        if not candidates:
            raise FileNotFoundError(f"下载完成但未找到音频文件: {info['id']}")
        audio_path = candidates[0]

    return DownloadResult(
        audio_path=audio_path,
        title=info.get("title") or "",
        duration=info.get("duration"),
        uploader=info.get("uploader"),
        webpage_url=info.get("webpage_url") or url,
        platform=info.get("extractor_key"),
    )
