"""AI 生成合成内容双标识。

依据：《AI生成合成内容标识办法》（网信办+工信部+公安部+广电总局，
2025-3-14 发布，2025-9-1 施行）+ 强制国标 GB 45438-2025。

    显式标识（用户可明显感知）：文本在起始/末尾/中间适当位置加文字提示，
                                或在交互界面加显著提示。
    隐式标识（文件元数据，用户不易感知）：须含生成合成内容属性信息、
                                          服务提供者名称或编码、内容编号。

对本系统的含义：生成的商机分析报告须双标识 ——
正文加显式 AI 提示 + 导出文件元数据嵌入提供者编码与内容编号。
**导出/下载的报告文件必须保留合规显式标识。**
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Mapping

#: 显式标识文案（放在正文起始与末尾）
EXPLICIT_NOTICE = "本内容由AI生成，仅供参考"

#: 隐式标识的属性值
CONTENT_ATTRIBUTE = "AI生成合成内容"


@dataclass(frozen=True)
class ProviderIdentity:
    """服务提供者身份 —— 隐式标识必填项。"""

    name: str
    #: 服务提供者编码（算法备案号 / 统一社会信用代码等）
    code: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("服务提供者名称不能为空 —— 隐式标识必填")
        if not self.code.strip():
            raise ValueError("服务提供者编码不能为空 —— 隐式标识必填")


@dataclass(frozen=True)
class LabeledContent:
    body: str
    metadata: Mapping[str, str] = field(default_factory=dict)

    def metadata_json(self) -> str:
        return json.dumps(dict(self.metadata), ensure_ascii=False,
                          sort_keys=True, separators=(",", ":"))


def content_id(body: str, provider: ProviderIdentity) -> str:
    """内容编号 —— 对正文与提供者做确定性摘要。

    确定性很重要：同一份报告重新导出必须得到同一编号，
    否则审计时无法把线上内容与存档对上。
    """
    digest = hashlib.sha256()
    digest.update(provider.code.encode("utf-8"))
    digest.update(b"\x00")
    digest.update(body.encode("utf-8"))
    return "OIC-" + digest.hexdigest()[:32]


def add_explicit_label(body: str, notice: str = EXPLICIT_NOTICE) -> str:
    """在正文起始与末尾加显式提示；已有则不重复添加。"""
    marker = f"【{notice}】"
    text = body.strip()
    parts = []
    if not text.startswith(marker):
        parts.append(marker)
    parts.append(text)
    if not text.endswith(marker):
        parts.append(marker)
    return "\n\n".join(parts)


def build_implicit_metadata(
    body: str,
    provider: ProviderIdentity,
    generated_at: str,
    extra: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """构造隐式标识元数据。

    ``generated_at`` 由调用方传入（ISO 8601 字符串）——
    本模块不读时钟，以保持确定性与可测试性。
    """
    metadata = {
        "AIGC-Attribute": CONTENT_ATTRIBUTE,
        "AIGC-Provider-Name": provider.name,
        "AIGC-Provider-Code": provider.code,
        "AIGC-Content-ID": content_id(body, provider),
        "AIGC-Generated-At": generated_at,
        "AIGC-Standard": "GB 45438-2025",
    }
    if extra:
        for key in sorted(extra):
            metadata[key] = extra[key]
    return metadata


def label(
    body: str,
    provider: ProviderIdentity,
    generated_at: str,
    extra: Mapping[str, str] | None = None,
) -> LabeledContent:
    """一次性完成双标识。导出路径上必须调用这个，而不是只加显式提示。"""
    labeled_body = add_explicit_label(body)
    metadata = build_implicit_metadata(labeled_body, provider, generated_at, extra)
    return LabeledContent(labeled_body, metadata)


class LabelingError(RuntimeError):
    """标识缺失 —— 导出前的最后一道闸。"""


def assert_labeled(content: LabeledContent) -> None:
    """导出闸门：显式与隐式任一缺失都不许导出。"""
    if EXPLICIT_NOTICE not in content.body:
        raise LabelingError("正文缺少显式 AI 标识 —— 不得导出")
    required = (
        "AIGC-Attribute",
        "AIGC-Provider-Name",
        "AIGC-Provider-Code",
        "AIGC-Content-ID",
    )
    missing = [key for key in required if not content.metadata.get(key)]
    if missing:
        raise LabelingError(f"隐式标识缺少必填项：{missing} —— 不得导出")
