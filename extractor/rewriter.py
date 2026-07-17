"""文案改写：DeepSeek API（OpenAI 兼容），支持用户自定义改写要求。

API Key 通过环境变量 DEEPSEEK_API_KEY 提供，不落盘、不写入代码。
备选供应商（如通义千问）可通过 base_url/model 参数切换。
"""

from __future__ import annotations

import os

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"

SYSTEM_PROMPT = (
    "你是短视频口播文案改写专家。根据用户的改写要求，把给定的口播文案改写成"
    "适合口播录制的新文案：保留核心信息与叙事结构，输出口语化、有节奏感的中文，"
    "不要输出任何解释、标题或 markdown 标记，只输出改写后的正文。"
)


def rewrite(
    text: str,
    instruction: str,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    temperature: float = 1.3,
) -> str:
    """按用户改写要求改写文案，返回改写后的正文。"""
    from openai import OpenAI

    api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("缺少 API Key：请设置环境变量 DEEPSEEK_API_KEY")

    client = OpenAI(
        api_key=api_key,
        base_url=base_url or os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
    )
    resp = client.chat.completions.create(
        model=model or os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL),
        temperature=temperature,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"改写要求：{instruction}\n\n原始文案：\n{text}",
            },
        ],
    )
    content = resp.choices[0].message.content
    if not content:
        raise RuntimeError("改写失败：模型返回为空")
    return content.strip()
