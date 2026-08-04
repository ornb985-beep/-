"""通用 HTTP 取数器 —— 「全网抓取」的合法完整版。

## 它能抓什么

**任何站点允许你抓的内容。** 这不是缩水版：绝大部分公开数据
（政府公开页、法定披露、开放 API、RSS、允许索引的媒体页）都在这条路上。

## 它拒绝做什么，以及为什么

这个模块**在代码层**做不到下面三件事，不是"默认关闭"而是没有这条路径：

1. **伪装浏览器 UA。** ``_assert_honest_user_agent`` 会拒绝含 Mozilla/Chrome
   等字样的 UA。伪装身份正是《反不正当竞争法》(2025) 第13条第3款所指的
   「避开技术管理措施」，而 UA 伪装是其中最容易被举证的一种 ——
   它留在对方日志里，是书面证据。
2. **无视 robots.txt。** 没有 ``ignore_robots`` 开关。
3. **对 403/429 重试或换身份。** 见 ``NO_RETRY_STATUSES``：
   **拒绝就是拒绝。反爬不是待修的 bug，是停止信号。**

德恒统计 2011–2022 年 12 起「爬虫 + 不正当竞争」案，爬取方胜诉率 < 16.67%。
上面三条恰好是败诉方的共同特征。

## robots.txt 不可达时怎么办

按 RFC 9309 §2.3.1.4：

    4xx（"Unavailable"）  → 视为无限制，可以抓
    5xx（"Unreachable"）  → **视为完全禁止**
    网络错误              → 同 5xx，按禁止处理

「拿不到规则」不等于「没有规则」。这条默认值是保守的，且是标准写明的。

## 为什么 transport 是注入的

不同部署环境的网络栈不同（代理、证书、限速）。把 HTTP 客户端做成参数
而不是依赖，让本模块的全部逻辑（robots 判定、限速、条件请求、解码）
都能离线确定性测试 —— 测试里不会有一个真实请求。
"""

from __future__ import annotations

import html as _html
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, field
from typing import Callable, Mapping, Protocol

from oic.compliance.provenance import Registry

# ---------------------------------------------------------------------------
# 异常 —— 每一种失败都有自己的类型，因为处理方式完全不同
# ---------------------------------------------------------------------------


class FetchError(RuntimeError):
    """取数失败。**永不返回空字符串** —— 空会被下游读成「这页没数据」。"""


class RobotsDisallowed(PermissionError):
    """robots.txt 明确禁止。这是站点的意思表示，不是障碍。"""


class AccessRefused(PermissionError):
    """站点用状态码拒绝了访问（403/429/451…）。

    **不重试、不换 UA、不换 IP。** 换个身份再来一次就从「被拒绝」
    变成了「规避技术管理措施」，法律性质完全不同。
    """


class DecodeError(FetchError):
    """字节解不成文本。

    宁可报错也不用 ``errors='replace'`` —— 静默替换会把
    「226.94亿元」变成「226.94�元」，而下游只会看到少了一个字。
    数量级错误就是这么产生的。
    """


class DishonestUserAgent(ValueError):
    """UA 伪装成浏览器。这条在构造阶段就拦，不给运行的机会。"""


# ---------------------------------------------------------------------------
# ① 诚实身份
# ---------------------------------------------------------------------------

#: 出现任一即判为伪装。真实抓取程序没有理由自称 Chrome。
_BROWSER_TOKENS = (
    "mozilla", "chrome", "safari", "firefox", "edge/", "edg/",
    "opera", "webkit", "gecko", "trident", "msie",
)

#: 可识别 UA 的最低要求：带联系方式。
#: SEC 明文要求 User-Agent 含联系邮箱（否则封禁），这不是我加的洁癖。
_CONTACT = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+|https?://\S+")


def _assert_honest_user_agent(ua: str) -> str:
    """UA 必须自报家门且带联系方式，且不得伪装浏览器。"""
    if not ua or not ua.strip():
        raise DishonestUserAgent(
            "User-Agent 不能为空 —— 匿名抓取在被追溯时无法自证善意"
        )
    lowered = ua.lower()
    for token in _BROWSER_TOKENS:
        if token in lowered:
            raise DishonestUserAgent(
                f"User-Agent 含浏览器标识「{token}」—— 伪装身份属于"
                "《反不正当竞争法》第13条第3款所指的规避行为，本模块不提供该能力。"
                "正确写法：'OIC-Research/1.0 (+mailto:you@example.com)'"
            )
    if not _CONTACT.search(ua):
        raise DishonestUserAgent(
            "User-Agent 必须含联系邮箱或主页 URL —— "
            "站点管理员要能找到你，这是 SEC 等来源的明文要求。"
            "例：'OIC-Research/1.0 (+mailto:you@example.com)'"
        )
    return ua


# ---------------------------------------------------------------------------
# ② 传输层（可注入）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RawResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes

    def header(self, name: str, default: str = "") -> str:
        """HTTP 头大小写不敏感。"""
        lowered = name.lower()
        for key, value in self.headers.items():
            if key.lower() == lowered:
                return value
        return default


class Transport(Protocol):
    def __call__(self, url: str, headers: Mapping[str, str], timeout: float
                 ) -> RawResponse: ...


def urllib_transport(ca_bundle: str | None = None) -> Transport:
    """标准库传输层。走环境里的代理设置，不绕过 TLS 校验。

    ``ca_bundle`` 为空时按 ``SSL_CERT_FILE`` / ``REQUESTS_CA_BUNDLE``
    环境变量取；都没有就用系统默认。**没有关闭校验的开关。**
    """
    cafile = ca_bundle or os.environ.get("SSL_CERT_FILE") \
        or os.environ.get("REQUESTS_CA_BUNDLE") or None
    context = ssl.create_default_context(cafile=cafile)

    def _fetch(url: str, headers: Mapping[str, str], timeout: float) -> RawResponse:
        request = urllib.request.Request(url, headers=dict(headers), method="GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout,
                                        context=context) as response:
                return RawResponse(
                    status=response.status,
                    headers=dict(response.headers.items()),
                    body=response.read(),
                )
        except urllib.error.HTTPError as exc:      # 4xx/5xx 是回答，不是异常
            return RawResponse(
                status=exc.code,
                headers=dict(exc.headers.items()) if exc.headers else {},
                body=exc.read() if exc.fp else b"",
            )
        except urllib.error.URLError as exc:
            raise FetchError(f"{url} 网络层失败: {exc.reason}") from exc

    return _fetch


# ---------------------------------------------------------------------------
# ③ 策略
# ---------------------------------------------------------------------------

#: 收到这些状态码时**立即停止**，不重试、不改身份。
#: 429/403 的正确回应是降频或走授权渠道，不是再试一次。
NO_RETRY_STATUSES = frozenset({401, 402, 403, 407, 429, 451})

#: 默认每站最小请求间隔（秒）。SEC 允许 10 req/s，但那是上限不是目标。
DEFAULT_MIN_INTERVAL_S = 1.0

#: 单页最大字节数。超限**报错而不截断** ——
#: 截断会正好切掉含数字的那一段，而下游看不出来。
DEFAULT_MAX_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class FetchPolicy:
    """抓取策略。

    注意这里**没有**任何一个「忽略 robots」「忽略 Crawl-delay」的字段。
    站点声明的延迟一律遵守 —— 遇到 ``Crawl-delay: 3600`` 的正确回应是
    一小时抓一页或者不抓，不是加个开关把它关掉。
    """

    user_agent: str
    min_interval_s: float = DEFAULT_MIN_INTERVAL_S
    timeout_s: float = 20.0
    max_bytes: int = DEFAULT_MAX_BYTES
    accept: str = "text/html,application/xhtml+xml,application/xml,text/plain,*/*"

    def __post_init__(self) -> None:
        _assert_honest_user_agent(self.user_agent)
        if self.min_interval_s < 0:
            raise ValueError("请求间隔不能为负")
        if self.max_bytes <= 0:
            raise ValueError("max_bytes 必须为正")


# ---------------------------------------------------------------------------
# ④ robots.txt
# ---------------------------------------------------------------------------


@dataclass
class RobotsDecision:
    allowed: bool
    reason: str
    crawl_delay: float | None = None


def _origin(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise FetchError(f"只支持 http/https：{url}")
    if not parts.netloc:
        raise FetchError(f"URL 缺少主机名：{url}")
    return f"{parts.scheme}://{parts.netloc}"


class RobotsCache:
    """按 origin 缓存 robots.txt 判定。

    缓存是必须的，不是优化：每抓一页都去拉一次 robots.txt，
    会让 robots.txt 本身成为你对该站压力最大的请求。
    """

    def __init__(self, transport: Transport, policy: FetchPolicy) -> None:
        self._transport = transport
        self._policy = policy
        self._cache: dict[str, RobotsDecision | urllib.robotparser.RobotFileParser] = {}
        self._unreachable: dict[str, str] = {}

    def _load(self, origin: str) -> None:
        url = origin + "/robots.txt"
        headers = {"User-Agent": self._policy.user_agent, "Accept": "text/plain"}
        try:
            response = self._transport(url, headers, self._policy.timeout_s)
        except Exception as exc:
            # 任何取不到的原因（超时、DNS、TLS、代理）都按 5xx 处理。
            # catch 得这么宽是刻意的：**拿不到规则不等于没有规则**，
            # 而漏掉一种异常类型就等于在那种情况下默认放行。
            self._unreachable[origin] = f"robots.txt 不可达（{type(exc).__name__}: {exc}）"
            return

        if 400 <= response.status < 500:
            # RFC 9309: "Unavailable" → 视为无限制
            parser = urllib.robotparser.RobotFileParser()
            parser.parse([])
            self._cache[origin] = parser
            return
        if response.status >= 500 or response.status < 200:
            self._unreachable[origin] = f"robots.txt 返回 {response.status}"
            return

        try:
            text = response.body.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            text = response.body.decode("latin-1")
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(text.splitlines())
        self._cache[origin] = parser

    def decide(self, url: str) -> RobotsDecision:
        origin = _origin(url)
        if origin not in self._cache and origin not in self._unreachable:
            self._load(origin)

        if origin in self._unreachable:
            return RobotsDecision(
                allowed=False,
                reason=(f"{self._unreachable[origin]} —— 按 RFC 9309 §2.3.1.4，"
                        "robots.txt 不可达时应视为完全禁止。"
                        "「拿不到规则」不等于「没有规则」。"),
            )

        parser = self._cache[origin]
        assert isinstance(parser, urllib.robotparser.RobotFileParser)
        ua = self._policy.user_agent
        if not parser.can_fetch(ua, url):
            return RobotsDecision(
                allowed=False,
                reason=f"robots.txt 禁止 {ua} 访问该路径 —— 这是站点的意思表示",
            )
        delay = parser.crawl_delay(ua)
        return RobotsDecision(
            allowed=True,
            reason="robots.txt 允许",
            crawl_delay=float(delay) if delay is not None else None,
        )


# ---------------------------------------------------------------------------
# ⑤ 限速
# ---------------------------------------------------------------------------


class RateLimiter:
    """按 origin 的最小间隔限速。时钟与 sleep 都可注入，便于确定性测试。"""

    def __init__(self, min_interval_s: float,
                 clock: Callable[[], float] | None = None,
                 sleeper: Callable[[float], None] | None = None) -> None:
        import time as _time
        self._min = min_interval_s
        self._clock = clock or _time.monotonic
        self._sleep = sleeper or _time.sleep
        self._last: dict[str, float] = {}

    def wait(self, origin: str, crawl_delay: float | None = None) -> float:
        """返回实际等待的秒数。

        站点声明的 ``Crawl-delay`` **只会让间隔变长，不会变短** ——
        站点说慢点就慢点，我方配置不用来覆盖它。
        """
        interval = max(self._min, crawl_delay or 0.0)
        now = self._clock()
        last = self._last.get(origin)
        waited = 0.0
        if last is not None:
            gap = now - last
            if gap < interval:
                waited = interval - gap
                self._sleep(waited)
        self._last[origin] = self._clock()
        return waited


# ---------------------------------------------------------------------------
# ⑥ 解码
# ---------------------------------------------------------------------------

_CHARSET_HEADER = re.compile(r"charset\s*=\s*[\"']?([\w\-]+)", re.I)
_CHARSET_META = re.compile(
    rb"""<meta[^>]+charset\s*=\s*["']?\s*([\w\-]+)""", re.I)

#: 解码顺序有讲究：gb18030 几乎能解出任意字节序列（全码位映射），
#: 放在最后才不会抢在 utf-8 前面产出一堆乱码而不报错。
_FALLBACK_ENCODINGS = ("utf-8", "gb18030", "big5")


def decode_body(body: bytes, content_type: str = "") -> str:
    """字节 → 文本。声明编码 → meta → utf-8 → gb18030 → big5，全失败则抛错。"""
    if not body:
        raise DecodeError("响应体为空 —— 拒绝当作「该页无内容」")

    candidates: list[str] = []
    declared = _CHARSET_HEADER.search(content_type or "")
    if declared:
        candidates.append(declared.group(1))
    meta = _CHARSET_META.search(body[:4096])
    if meta:
        try:
            candidates.append(meta.group(1).decode("ascii"))
        except UnicodeDecodeError:
            pass
    candidates.extend(_FALLBACK_ENCODINGS)

    seen: set[str] = set()
    for encoding in candidates:
        key = encoding.lower().replace("_", "-")
        if key in seen:
            continue
        seen.add(key)
        try:
            return body.decode(encoding, errors="strict")
        except (UnicodeDecodeError, LookupError):
            continue

    raise DecodeError(
        f"无法解码（已试 {sorted(seen)}）—— 不使用 errors='replace'，"
        "静默替换会把数字旁的字符换成 �，而下游看不出来"
    )


_SCRIPT_STYLE = re.compile(r"<(script|style)\b.*?</\1>", re.I | re.S)
_TAG = re.compile(r"<[^>]+>")
_BLANKS = re.compile(r"[ \t\r\f\v]+")
_MANY_NEWLINES = re.compile(r"\n{3,}")


def html_to_text(html_text: str) -> str:
    """极简 HTML 去标签。

    刻意不做正文抽取（Readability 那类）：抽取算法会丢段落，
    而丢掉的可能正是含数字的那一段。宁可留噪声，也不让证据凭空消失。
    """
    text = _SCRIPT_STYLE.sub("", html_text)
    text = re.sub(r"<br\s*/?>|</p>|</div>|</li>|</tr>|</h[1-6]>", "\n", text, flags=re.I)
    text = _TAG.sub(" ", text)
    text = _html.unescape(text)
    text = _BLANKS.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return _MANY_NEWLINES.sub("\n\n", text).strip()


# ---------------------------------------------------------------------------
# ⑦ 条件请求缓存
# ---------------------------------------------------------------------------


@dataclass
class CacheEntry:
    etag: str = ""
    last_modified: str = ""
    text: str = ""
    fetched_at: str = ""


# ---------------------------------------------------------------------------
# ⑧ 取数器
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FetchResult:
    url: str
    source_key: str
    status: int
    text: str
    content_type: str
    from_cache: bool
    waited_s: float
    robots_reason: str

    @property
    def is_html(self) -> bool:
        return "html" in self.content_type.lower()

    def as_text(self) -> str:
        """HTML 自动去标签，其余原样返回。"""
        return html_to_text(self.text) if self.is_html else self.text


class HttpFetcher:
    """通用取数器。

    调用顺序是固定的，每一步都是闸门：

        provenance 白名单 → robots.txt → 限速 → 条件请求 → 状态码 → 解码

    任何一步不过就抛异常，**不返回退化结果**。
    """

    def __init__(
        self,
        policy: FetchPolicy,
        registry: Registry,
        transport: Transport | None = None,
        clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
        now: Callable[[], str] | None = None,
    ) -> None:
        self.policy = policy
        self.registry = registry
        self._transport = transport or urllib_transport()
        self._robots = RobotsCache(self._transport, policy)
        self._limiter = RateLimiter(policy.min_interval_s, clock, sleeper)
        self._cache: dict[str, CacheEntry] = {}
        self._now = now or _iso_now

    # -- 审计 --------------------------------------------------------------
    def robots_decision(self, url: str) -> RobotsDecision:
        """暴露出来供人工复核：为什么这个 URL 抓了 / 没抓。"""
        return self._robots.decide(url)

    # -- 主流程 ------------------------------------------------------------
    def fetch(self, url: str, source_key: str) -> FetchResult:
        # ① 数据源必须已登记且放行 —— 没有例外通道
        self.registry.assert_source_allowed(source_key)

        origin = _origin(url)

        # ② robots.txt
        decision = self._robots.decide(url)
        if not decision.allowed:
            raise RobotsDisallowed(f"{url} 不予抓取：{decision.reason}")

        # ③ 限速（站点声明的 Crawl-delay 只会让间隔更长）
        waited = self._limiter.wait(origin, decision.crawl_delay)

        # ④ 条件请求：有缓存就带上校验头，省对方的流量也省自己的
        headers = {
            "User-Agent": self.policy.user_agent,
            "Accept": self.policy.accept,
            "Accept-Encoding": "identity",
        }
        entry = self._cache.get(url)
        if entry and entry.etag:
            headers["If-None-Match"] = entry.etag
        if entry and entry.last_modified:
            headers["If-Modified-Since"] = entry.last_modified

        try:
            response = self._transport(url, headers, self.policy.timeout_s)
        except FetchError:
            raise
        except Exception as exc:
            raise FetchError(f"{url} 取数失败（{type(exc).__name__}: {exc}）") from exc

        # ⑤ 状态码
        if response.status == 304:
            if not entry or not entry.text:
                raise FetchError(f"{url} 返回 304 但本地无缓存内容 —— 缓存状态不一致")
            return FetchResult(url, source_key, 304, entry.text,
                               response.header("Content-Type"), True, waited,
                               decision.reason)

        if response.status in NO_RETRY_STATUSES:
            raise AccessRefused(
                f"{url} 返回 {response.status} —— 站点拒绝了本次访问。\n"
                "**不重试、不换 UA、不换 IP。** 反爬是停止信号，不是待修的 bug；"
                "换身份重试会把「被拒绝」变成「规避技术管理措施」"
                "（《反不正当竞争法》2025 第13条第3款）。\n"
                "正确做法：降低频率、走官方 API/授权渠道，或从源清单中移除该站。"
            )

        if response.status >= 400 or response.status < 200:
            raise FetchError(f"{url} 返回 HTTP {response.status}")

        if len(response.body) > self.policy.max_bytes:
            raise FetchError(
                f"{url} 响应 {len(response.body)} 字节超过上限 {self.policy.max_bytes} —— "
                "**不截断**：截断可能正好切掉含数字的那一段，而下游看不出来。"
                "确需抓取请显式调高 max_bytes。"
            )

        content_type = response.header("Content-Type")
        text = decode_body(response.body, content_type)

        self._cache[url] = CacheEntry(
            etag=response.header("ETag"),
            last_modified=response.header("Last-Modified"),
            text=text,
            fetched_at=self._now(),
        )
        return FetchResult(url, source_key, response.status, text, content_type,
                           False, waited, decision.reason)

    # -- 适配 fetchers.Fetcher 协议 ---------------------------------------
    def as_fetcher(self, source_key: str) -> Callable[[str], str]:
        """返回 ``fetcher(url) -> str``，可直接注入 ``fetchers.fetch_filing``。"""
        def _call(url: str) -> str:
            return self.fetch(url, source_key).text
        return _call


def _iso_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
