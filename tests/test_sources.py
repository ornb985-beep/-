"""取数适配层测试：RSS / 通用 HTTP / SDK。

**整个文件不发一个真实请求。** transport 是注入的，
所以 robots 判定、限速、条件请求、解码这些逻辑全部可离线确定性验证 ——
这也是把 HTTP 客户端做成参数而不是依赖的主要理由。
"""

from __future__ import annotations

import unittest

from oic.compliance.provenance import (
    AccessMethod, LegalStatus, Registry, SourceNotAllowed, SourceRecord,
)
from oic.research import metrics as mx
from oic.research.dossier import Observation
from oic.sdk import OIC, DataRejected, NotCalibrated, SourceBlocked
from oic.sources import http_fetch as hf
from oic.sources.rss import FeedError, FeedItem, filter_by_date, parse_feed

# ---------------------------------------------------------------------------
# 测试替身
# ---------------------------------------------------------------------------

UA = "OIC-Test/1.0 (+mailto:test@example.com)"


class FakeTransport:
    """按 URL 返回预置响应，并记录每个 URL 被请求了几次。

    调用计数是关键：403 之后**必须只有 1 次**请求 ——
    「不重试」这条纪律只有靠计数才能真的测出来。
    """

    def __init__(self, routes: dict[str, hf.RawResponse | Exception]) -> None:
        self.routes = routes
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, url, headers, timeout):
        self.calls.append((url, dict(headers)))
        result = self.routes.get(url)
        if result is None:
            return hf.RawResponse(404, {}, b"not found")
        if isinstance(result, Exception):
            raise result
        return result

    def count(self, url: str) -> int:
        return sum(1 for u, _ in self.calls if u == url)


def ok(body: bytes, content_type="text/html; charset=utf-8", **headers):
    merged = {"Content-Type": content_type}
    merged.update(headers)
    return hf.RawResponse(200, merged, body)


def robots(text: str):
    return hf.RawResponse(200, {"Content-Type": "text/plain"},
                          text.encode("utf-8"))


def allowing_registry(key="rss_36kr") -> Registry:
    """一个把指定源放行的登记表 —— 只在测试里这么做。"""
    registry = Registry()
    registry.register(SourceRecord(
        key=key, name=f"测试源 {key}",
        access_method=AccessMethod.PUBLIC_DOWNLOAD,
        tos_url="https://example.com/tos",
        legal_status=LegalStatus.CLEARED,
        legal_note="测试用", reviewed_on="2026-08-04",
    ))
    return registry


def fetcher(routes, registry=None, policy=None):
    transport = FakeTransport(routes)
    client = hf.HttpFetcher(
        policy or hf.FetchPolicy(user_agent=UA, min_interval_s=0.0),
        registry or allowing_registry(),
        transport=transport,
        clock=_FakeClock(),
        sleeper=lambda s: None,
        now=lambda: "2026-08-04T00:00:00+00:00",
    )
    return client, transport


class _FakeClock:
    """单调假时钟。每次读取前进 0 秒 —— 由测试显式 advance。"""

    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


# ---------------------------------------------------------------------------
# RSS / Atom
# ---------------------------------------------------------------------------

RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>36氪</title>
  <item>
    <title>某新消费品牌完成 A 轮融资</title>
    <link>https://example.com/a</link>
    <pubDate>Tue, 15 Oct 2024 08:30:00 +0800</pubDate>
    <description>金额 1.2 亿元</description>
  </item>
  <item>
    <title>无日期的条目</title>
    <link>https://example.com/b</link>
    <description>没有 pubDate</description>
  </item>
</channel></rss>"""

ATOM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>虎嗅</title>
  <entry>
    <title>即时零售的价格战</title>
    <link href="https://example.com/c"/>
    <published>2025-03-02T10:00:00Z</published>
    <summary>毛利率下滑</summary>
  </entry>
</feed>"""


class TestRss(unittest.TestCase):
    def test_parses_rss2(self):
        items = parse_feed(RSS_XML, "rss_36kr")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].title, "某新消费品牌完成 A 轮融资")
        self.assertEqual(items[0].published_at, "2024-10-15")
        self.assertEqual(items[0].source_key, "rss_36kr")

    def test_parses_atom_link_from_attribute(self):
        items = parse_feed(ATOM_XML, "rss_huxiu")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].link, "https://example.com/c")
        self.assertEqual(items[0].published_at, "2025-03-02")

    def test_empty_feed_raises_not_returns_empty(self):
        """空列表会被上层读成「今天没有新内容」—— 那是错误结论，不是数据。"""
        with self.assertRaises(FeedError):
            parse_feed("", "rss_36kr")
        with self.assertRaises(FeedError):
            parse_feed("<rss version='2.0'><channel/></rss>", "rss_36kr")

    def test_malformed_xml_raises(self):
        with self.assertRaises(FeedError):
            parse_feed("<rss><channel><item>", "rss_36kr")

    def test_undated_items_excluded_by_asof(self):
        items = parse_feed(RSS_XML, "rss_36kr")
        kept = filter_by_date(items, "2025-01-01")
        self.assertEqual([i.link for i in kept], ["https://example.com/a"])

    def test_asof_excludes_future_items(self):
        items = parse_feed(ATOM_XML, "rss_huxiu")
        self.assertEqual(filter_by_date(items, "2024-01-01"), ())

    def test_unparseable_date_stays_empty_not_today(self):
        item = FeedItem("t", "u", "", "s", "k")
        self.assertFalse(item.has_date)


# ---------------------------------------------------------------------------
# 诚实身份
# ---------------------------------------------------------------------------


class TestHonestIdentity(unittest.TestCase):
    def test_browser_impersonation_rejected(self):
        for bad in ("Mozilla/5.0 (Windows NT 10.0)",
                    "MyBot Chrome/120 (+mailto:a@b.com)",
                    "AppleWebKit/537.36 (+mailto:a@b.com)"):
            with self.assertRaises(hf.DishonestUserAgent):
                hf.FetchPolicy(user_agent=bad)

    def test_contactless_ua_rejected(self):
        with self.assertRaises(hf.DishonestUserAgent):
            hf.FetchPolicy(user_agent="OIC-Research/1.0")

    def test_empty_ua_rejected(self):
        with self.assertRaises(hf.DishonestUserAgent):
            hf.FetchPolicy(user_agent="  ")

    def test_honest_ua_accepted(self):
        policy = hf.FetchPolicy(user_agent=UA)
        self.assertEqual(policy.user_agent, UA)
        hf.FetchPolicy(user_agent="OIC-Research/1.0 (+https://example.com/bot)")


# ---------------------------------------------------------------------------
# robots.txt
# ---------------------------------------------------------------------------


class TestRobots(unittest.TestCase):
    def test_disallow_blocks(self):
        client, _ = fetcher({
            "https://site.test/robots.txt": robots("User-agent: *\nDisallow: /private"),
            "https://site.test/private/x": ok(b"secret"),
        })
        with self.assertRaises(hf.RobotsDisallowed):
            client.fetch("https://site.test/private/x", "rss_36kr")

    def test_allow_passes(self):
        client, _ = fetcher({
            "https://site.test/robots.txt": robots("User-agent: *\nDisallow: /private"),
            "https://site.test/public/x": ok("市场规模 226.94 亿元".encode("utf-8")),
        })
        result = client.fetch("https://site.test/public/x", "rss_36kr")
        self.assertIn("226.94", result.text)

    def test_404_robots_means_unrestricted(self):
        """RFC 9309 §2.3.1.4：4xx = Unavailable → 可以抓。"""
        client, _ = fetcher({
            "https://site.test/robots.txt": hf.RawResponse(404, {}, b""),
            "https://site.test/x": ok(b"hello"),
        })
        self.assertTrue(client.robots_decision("https://site.test/x").allowed)

    def test_5xx_robots_means_full_disallow(self):
        """RFC 9309：5xx = Unreachable → **视为完全禁止**。

        「拿不到规则」不等于「没有规则」。
        """
        client, _ = fetcher({
            "https://site.test/robots.txt": hf.RawResponse(503, {}, b""),
            "https://site.test/x": ok(b"hello"),
        })
        with self.assertRaises(hf.RobotsDisallowed):
            client.fetch("https://site.test/x", "rss_36kr")

    def test_network_error_on_robots_means_disallow(self):
        client, _ = fetcher({
            "https://site.test/robots.txt": hf.FetchError("DNS 失败"),
            "https://site.test/x": ok(b"hello"),
        })
        with self.assertRaises(hf.RobotsDisallowed):
            client.fetch("https://site.test/x", "rss_36kr")

    def test_robots_fetched_once_per_origin(self):
        """缓存是必须的：每页都拉 robots.txt 会让它成为压力最大的请求。"""
        client, transport = fetcher({
            "https://site.test/robots.txt": robots("User-agent: *\nAllow: /"),
            "https://site.test/a": ok(b"a"),
            "https://site.test/b": ok(b"b"),
        })
        client.fetch("https://site.test/a", "rss_36kr")
        client.fetch("https://site.test/b", "rss_36kr")
        self.assertEqual(transport.count("https://site.test/robots.txt"), 1)

    def test_no_ignore_robots_switch_exists(self):
        """没有绕过开关，不是「默认关闭」。"""
        names = set(dir(hf.FetchPolicy)) | set(hf.FetchPolicy.__dataclass_fields__)
        for forbidden in ("ignore_robots", "obey_robots", "bypass_robots",
                          "force", "respect_robots", "obey_crawl_delay"):
            self.assertNotIn(forbidden, names)

    def test_arbitrary_transport_failure_still_disallows(self):
        """catch 得宽是刻意的：漏掉一种异常类型 = 那种情况下默认放行。"""
        for boom in (TimeoutError("timed out"), OSError("connection reset"),
                     ValueError("proxy said no")):
            client, _ = fetcher({
                "https://site.test/robots.txt": boom,
                "https://site.test/x": ok(b"hello"),
            })
            with self.assertRaises(hf.RobotsDisallowed):
                client.fetch("https://site.test/x", "rss_36kr")


# ---------------------------------------------------------------------------
# 限速
# ---------------------------------------------------------------------------


class TestRateLimiter(unittest.TestCase):
    def test_waits_between_requests_to_same_host(self):
        clock = _FakeClock()
        slept: list[float] = []
        limiter = hf.RateLimiter(2.0, clock=clock, sleeper=slept.append)
        limiter.wait("https://a.test")
        self.assertEqual(slept, [])
        limiter.wait("https://a.test")
        self.assertEqual(slept, [2.0])

    def test_no_wait_when_enough_time_already_passed(self):
        clock = _FakeClock()
        slept: list[float] = []
        limiter = hf.RateLimiter(2.0, clock=clock, sleeper=slept.append)
        limiter.wait("https://a.test")
        clock.t = 5.0
        limiter.wait("https://a.test")
        self.assertEqual(slept, [])

    def test_partial_wait_when_some_time_passed(self):
        clock = _FakeClock()
        slept: list[float] = []
        limiter = hf.RateLimiter(2.0, clock=clock, sleeper=slept.append)
        limiter.wait("https://a.test")
        clock.t = 0.5
        limiter.wait("https://a.test")
        self.assertEqual(slept, [1.5])

    def test_different_hosts_do_not_block_each_other(self):
        clock = _FakeClock()
        slept: list[float] = []
        limiter = hf.RateLimiter(2.0, clock=clock, sleeper=slept.append)
        limiter.wait("https://a.test")
        limiter.wait("https://b.test")
        self.assertEqual(slept, [])

    def test_crawl_delay_only_lengthens_never_shortens(self):
        """站点说慢点就慢点；我方配置不用来覆盖站点声明。"""
        clock = _FakeClock()
        slept: list[float] = []
        limiter = hf.RateLimiter(5.0, clock=clock, sleeper=slept.append)
        limiter.wait("https://a.test", crawl_delay=1.0)
        limiter.wait("https://a.test", crawl_delay=1.0)
        self.assertEqual(slept, [5.0])          # 取 max，不是取站点的 1.0

        slept.clear()
        limiter2 = hf.RateLimiter(1.0, clock=_FakeClock(), sleeper=slept.append)
        limiter2.wait("https://b.test", crawl_delay=9.0)
        limiter2.wait("https://b.test", crawl_delay=9.0)
        self.assertEqual(slept, [9.0])

    def test_crawl_delay_read_from_robots(self):
        client, _ = fetcher({
            "https://site.test/robots.txt":
                robots("User-agent: *\nCrawl-delay: 7\nAllow: /"),
            "https://site.test/x": ok(b"x"),
        })
        self.assertEqual(client.robots_decision("https://site.test/x").crawl_delay, 7.0)


# ---------------------------------------------------------------------------
# 拒绝即停止
# ---------------------------------------------------------------------------


class TestRefusalIsFinal(unittest.TestCase):
    def test_403_raises_and_does_not_retry(self):
        client, transport = fetcher({
            "https://site.test/robots.txt": robots("User-agent: *\nAllow: /"),
            "https://site.test/x": hf.RawResponse(403, {}, b"forbidden"),
        })
        with self.assertRaises(hf.AccessRefused) as ctx:
            client.fetch("https://site.test/x", "rss_36kr")
        self.assertEqual(transport.count("https://site.test/x"), 1)
        self.assertIn("停止信号", str(ctx.exception))

    def test_429_raises(self):
        client, transport = fetcher({
            "https://site.test/robots.txt": robots("User-agent: *\nAllow: /"),
            "https://site.test/x": hf.RawResponse(429, {}, b""),
        })
        with self.assertRaises(hf.AccessRefused):
            client.fetch("https://site.test/x", "rss_36kr")
        self.assertEqual(transport.count("https://site.test/x"), 1)

    def test_ua_is_identical_across_requests(self):
        """不轮换身份 —— 换 UA 重试会把「被拒绝」变成「规避技术措施」。"""
        client, transport = fetcher({
            "https://site.test/robots.txt": robots("User-agent: *\nAllow: /"),
            "https://site.test/a": ok(b"a"),
            "https://site.test/b": ok(b"b"),
        })
        client.fetch("https://site.test/a", "rss_36kr")
        client.fetch("https://site.test/b", "rss_36kr")
        agents = {h.get("User-Agent") for _, h in transport.calls}
        self.assertEqual(agents, {UA})


# ---------------------------------------------------------------------------
# 条件请求
# ---------------------------------------------------------------------------


class TestConditionalRequests(unittest.TestCase):
    def test_etag_sent_on_second_request_and_304_uses_cache(self):
        client, transport = fetcher({
            "https://site.test/robots.txt": robots("User-agent: *\nAllow: /"),
            "https://site.test/x": ok("规模 478 亿元".encode("utf-8"), ETag='"v1"'),
        })
        first = client.fetch("https://site.test/x", "rss_36kr")
        self.assertFalse(first.from_cache)

        transport.routes["https://site.test/x"] = hf.RawResponse(304, {}, b"")
        second = client.fetch("https://site.test/x", "rss_36kr")
        self.assertTrue(second.from_cache)
        self.assertEqual(second.text, first.text)

        sent = [h for u, h in transport.calls if u == "https://site.test/x"]
        self.assertEqual(sent[1].get("If-None-Match"), '"v1"')

    def test_304_without_cache_is_an_error_not_empty(self):
        client, _ = fetcher({
            "https://site.test/robots.txt": robots("User-agent: *\nAllow: /"),
            "https://site.test/x": hf.RawResponse(304, {}, b""),
        })
        with self.assertRaises(hf.FetchError):
            client.fetch("https://site.test/x", "rss_36kr")


# ---------------------------------------------------------------------------
# 解码 —— 数量级错误的另一个入口
# ---------------------------------------------------------------------------


class TestDecoding(unittest.TestCase):
    def test_gb18030_page_decoded_correctly(self):
        body = "市场规模为 226.94 亿元".encode("gb18030")
        text = hf.decode_body(body, "text/html; charset=gb18030")
        self.assertIn("226.94 亿元", text)

    def test_meta_charset_used_when_header_missing(self):
        body = ("<html><head><meta charset=\"gb18030\"></head>"
                "<body>规模 478 亿元</body></html>").encode("gb18030")
        text = hf.decode_body(body, "text/html")
        self.assertIn("478 亿元", text)

    def test_never_silently_replaces(self):
        """errors='replace' 会把「226.94亿元」变成「226.94�元」而不报错。"""
        with self.assertRaises(hf.DecodeError):
            hf.decode_body(b"\xff\xfe\x00\x00\xff\xff", "application/octet-stream")

    def test_empty_body_raises(self):
        with self.assertRaises(hf.DecodeError):
            hf.decode_body(b"", "text/html")

    def test_oversize_raises_instead_of_truncating(self):
        policy = hf.FetchPolicy(user_agent=UA, min_interval_s=0.0, max_bytes=10)
        client, _ = fetcher({
            "https://site.test/robots.txt": robots("User-agent: *\nAllow: /"),
            "https://site.test/x": ok(b"0123456789abcdef"),
        }, policy=policy)
        with self.assertRaises(hf.FetchError) as ctx:
            client.fetch("https://site.test/x", "rss_36kr")
        self.assertIn("不截断", str(ctx.exception))


class TestHtmlToText(unittest.TestCase):
    def test_keeps_numbers_and_drops_scripts(self):
        html = ("<html><script>var x=999999;</script><style>p{}</style>"
                "<p>2024 年市场规模 <b>226.94</b> 亿元，同比增长 12.3%</p></html>")
        text = hf.html_to_text(html)
        self.assertIn("226.94", text)
        self.assertIn("12.3%", text)
        self.assertNotIn("999999", text)

    def test_entities_unescaped(self):
        self.assertIn("增长>10%", hf.html_to_text("<p>增长&gt;10%</p>"))

    def test_no_body_extraction_paragraphs_survive(self):
        """刻意不做正文抽取：抽取算法丢掉的可能正是含数字的那一段。"""
        html = ("<div class='sidebar'><p>广告</p></div>"
                "<div class='footer'><p>备案号 京ICP备 12345 号</p></div>"
                "<p>2022 年新增注册 3.81万家</p>")
        text = hf.html_to_text(html)
        self.assertIn("3.81万家", text)
        self.assertIn("12345", text)          # 噪声也留着，不猜哪段是正文


# ---------------------------------------------------------------------------
# provenance 闸
# ---------------------------------------------------------------------------


class TestProvenanceGate(unittest.TestCase):
    def test_unregistered_source_blocked_before_any_request(self):
        client, transport = fetcher({
            "https://site.test/robots.txt": robots("User-agent: *\nAllow: /"),
            "https://site.test/x": ok(b"x"),
        })
        with self.assertRaises(PermissionError):
            client.fetch("https://site.test/x", "没登记过的源")
        self.assertEqual(transport.calls, [])       # 一个请求都没发出去

    def test_scraping_source_never_allowed(self):
        registry = Registry()
        registry.register(SourceRecord(
            key="weibo_hot", name="微博热搜",
            access_method=AccessMethod.SCRAPING,
            tos_url="https://weibo.com/tos",
            legal_status=LegalStatus.CLEARED,       # 就算法务放行
            legal_note="假设已过法务", reviewed_on="2026-08-04",
        ))
        client, transport = fetcher({
            "https://site.test/robots.txt": robots("User-agent: *\nAllow: /"),
            "https://site.test/x": ok(b"x"),
        }, registry=registry)
        with self.assertRaises(SourceNotAllowed):
            client.fetch("https://site.test/x", "weibo_hot")
        self.assertEqual(transport.calls, [])


# ---------------------------------------------------------------------------
# SDK
# ---------------------------------------------------------------------------


def sdk() -> OIC:
    return OIC.for_app(app_name="OIC-Test", contact="test@example.com")


class TestSdkConstruction(unittest.TestCase):
    def test_contact_required(self):
        with self.assertRaises(ValueError):
            OIC.for_app(app_name="X", contact="")

    def test_user_agent_is_honest(self):
        self.assertIn("mailto:test@example.com", sdk().fetch_policy.user_agent)

    def test_chinese_app_name_still_yields_usable_ua(self):
        client = OIC.for_app(app_name="我的商机助手", contact="me@example.com")
        self.assertTrue(client.fetch_policy.user_agent.startswith("OIC-App/"))

    def test_missing_filing_number_is_visible_not_silent(self):
        """一个看起来像真编码的默认值会被原样带上线，带 UNFILED- 的不会。"""
        client = sdk()
        self.assertTrue(client.provider.code.startswith("UNFILED-"))
        report = client.capabilities()
        self.assertNotIn("aigc_filing", report.available_keys)

        filed = OIC.for_app(app_name="OIC-Test", contact="t@example.com",
                            provider_code="网信算备110108xxxxxx号")
        self.assertIn("aigc_filing", filed.capabilities().available_keys)

    def test_no_source_allowed_by_default(self):
        """默认全部拒绝 —— 在填上授权依据之前，采集层本就不该能跑。"""
        self.assertEqual(sdk().registry.allowed_keys(), ())


class TestSdkSourceClearing(unittest.TestCase):
    def test_clear_source_requires_evidence(self):
        client = sdk()
        with self.assertRaises(ValueError):
            client.clear_source("rss_36kr", tos_url="", legal_note="ok",
                                reviewed_on="2026-08-04")

    def test_clear_source_works(self):
        client = sdk()
        client.clear_source("rss_36kr", tos_url="https://36kr.com/terms",
                            legal_note="RSS 由发布方主动提供", reviewed_on="2026-08-04")
        self.assertIn("rss_36kr", client.registry.allowed_keys())

    def test_cannot_clear_a_scraping_source(self):
        """这条是硬规则，SDK 覆盖不了 —— 也不该能覆盖。"""
        client = sdk()
        client.clear_source("weibo_hot", tos_url="https://weibo.com/tos",
                            legal_note="我确认自己负责", reviewed_on="2026-08-04")
        self.assertNotIn("weibo_hot", client.registry.allowed_keys())

    def test_fetch_on_blocked_source_raises_sourceblocked(self):
        client = sdk()
        with self.assertRaises(SourceBlocked):
            client.fetch("https://weibo.com/x", "weibo_hot")


class TestSdkGrounding(unittest.TestCase):
    RAW = "据企查查数据，2022 年露营相关企业新增注册 3.81万家，同比增长 68%。"

    def test_catches_the_100x_transcription_error(self):
        """我真犯过的错：把「3.81万」记成 3,810,000。"""
        client = sdk()
        result = client.check_claim(
            value=3_810_000, raw_text=self.RAW, snippet="新增注册 3.81万家",
            metric="新增注册企业数", unit="家")
        self.assertFalse(result.accepted)

    def test_correct_value_accepted(self):
        client = sdk()
        result = client.check_claim(
            value=38_100, raw_text=self.RAW, snippet="新增注册 3.81万家",
            metric="新增注册企业数", unit="家")
        self.assertTrue(result.accepted)

    def test_snippet_not_in_raw_text_is_rejected(self):
        client = sdk()
        with self.assertRaises(DataRejected):
            client.check_claim(value=38_100, raw_text=self.RAW,
                               snippet="我自己改写过的片段")


def obs(cat, key, year, value, source, snippet, measure=None):
    return Observation(
        category_key=cat, metric_family=key.family, metric_scope=key.scope,
        metric_measure=measure or key.measure, year=year, value=value,
        currency="NONE", unit_note="", source_url="https://example.com",
        source_name=source, source_grade="B", published_at="2022-06-01",
        retrieved_at="2026-08-04", snippet=snippet,
    )


class TestSdkAuditGate(unittest.TestCase):
    def test_error_blocks_downstream_use(self):
        client = sdk()
        bad = [obs("camping", mx.COMPANY_NEW, 2022, 3_810_000, "qcc",
                   "新增注册 3.81万家")]
        with self.assertRaises(DataRejected):
            client.assert_data_usable(bad)

    def test_clean_data_passes_through(self):
        client = sdk()
        good = [obs("camping", mx.COMPANY_NEW, 2022, 38_100, "qcc",
                    "新增注册 3.81万家")]
        self.assertEqual(len(client.assert_data_usable(good)), 1)


class TestSdkRefusals(unittest.TestCase):
    def test_probability_refused_below_30(self):
        with self.assertRaises(NotCalibrated) as ctx:
            sdk().predict_probability(score=72.0, n_resolved=11)
        self.assertIn("11", str(ctx.exception))

    def test_probability_still_refused_at_30_because_not_fitted(self):
        """样本够了不等于已经拟合。够了也要先拟合再说。"""
        with self.assertRaises(NotCalibrated):
            sdk().predict_probability(score=72.0, n_resolved=30)

    def test_capabilities_admit_effectiveness_unproven(self):
        report = sdk().capabilities(n_resolved_outcomes=11)
        self.assertNotIn("effectiveness", report.available_keys)
        self.assertNotIn("probability", report.available_keys)
        self.assertIn("scoring", report.available_keys)


class TestSdkExport(unittest.TestCase):
    def test_export_labels_content(self):
        content = sdk().export("剪刀差 33 个百分点，窗口开着。",
                               generated_at="2026-08-04T00:00:00Z")
        self.assertIn("AIGC-Content-ID", content.metadata)
        self.assertNotEqual(content.body, "剪刀差 33 个百分点，窗口开着。")

    def test_export_blocks_securities_content(self):
        with self.assertRaises(PermissionError):
            sdk().export("建议买入 sh600519，目标价 2000 元",
                         generated_at="2026-08-04T00:00:00Z")

    def test_export_survives_urls_in_evidence(self):
        """真实踩过：`doc-ikyamrmz7882579.shtml` 被判成 A 股代码。"""
        body = ("依据：market_size = 478亿元（来源：sina · "
                "https://finance.sina.com.cn/chanjing/cyxw/2022-01-28/"
                "doc-ikyamrmz7882579.shtml）")
        content = sdk().export(body, generated_at="2026-08-04T00:00:00Z")
        self.assertIn("478亿元", content.body)

    def test_check_export_reports_without_raising(self):
        lines = sdk().check_export("建议买入 sh600519")
        self.assertTrue(any("S1" in line for line in lines))


class TestSdkFeed(unittest.TestCase):
    def test_feed_requires_cleared_source(self):
        with self.assertRaises(PermissionError):
            sdk().read_feed(RSS_XML, "rss_36kr")

    def test_feed_after_clearing(self):
        client = sdk()
        client.clear_source("rss_36kr", tos_url="https://36kr.com/terms",
                            legal_note="RSS", reviewed_on="2026-08-04")
        items = client.read_feed(RSS_XML, "rss_36kr", as_of="2025-01-01")
        self.assertEqual(len(items), 1)


class TestSdkInvestigation(unittest.TestCase):
    def test_plan_covers_supply_side_angles(self):
        plan = sdk().plan_investigation("即时零售", [2024, 2025])
        angles = {angle for angle, _, _ in plan.queries}
        self.assertIn("supply_entry", angles)
        self.assertIn("supply_exit", angles)
        self.assertIn("concentration", angles)

    def test_independence_collapses_reposts(self):
        """10 个源转引同一家 = 1 个证据，不是 10 个。"""
        report = sdk().assess_independence([
            ("新浪财经", "据艾媒咨询数据显示"),
            ("网易新闻", "艾媒咨询报告指出"),
            ("36氪", "企查查数据显示"),
        ])
        self.assertEqual(report.n_sources, 3)
        self.assertEqual(report.n_effective, 2)

    def test_saturation_flags_empty_angles(self):
        report = sdk().assess_saturation([
            ("demand_size", 2), ("supply_entry", 4), ("capital", 0),
        ])
        self.assertIn("capital", report.angles_empty)


if __name__ == "__main__":
    unittest.main()
