"""证券边界拦截器。

核心判据 = 是否触及"**具体证券**"。

《证券法》第160条第2款：从事证券投资咨询服务业务须经证监会核准。
"荐股软件"认定标准（任一功能即算）：
  ① 对具体证券做投资分析意见或预测价格走势
  ② 推荐具体证券
  ③ 推荐具体证券的买卖时机
  ④ 其他证券投资分析/预测/建议

关键豁免：仅有证券信息汇总或历史数据统计、不具备上述四功能的
软件不属于荐股软件。

对本系统的含义：纯商业/市场/创业机会分析（行业趋势、商业模式、
市场规模）**不需要**证监会牌照。但"投资级决策建议"是高危措辞，
必须改为"商业/市场机会分析"。**"投资"二字本身不触发，证券关联才触发。**

罚则：第213条 —— 责令改正、没收违法所得、并处 1–10 倍罚款；
无/不足 50 万违法所得的处 50万–500万，责任人 20万–200万；
可升级为刑法 225 条非法经营罪。
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from typing import Iterable

# --- ① 具体证券标识 -------------------------------------------------------
# A股6位代码（含常见前缀）、港股5位、美股 ticker 与常见交易所标注
_SECURITY_ID = re.compile(
    r"(?:(?:sh|sz|bj|SH|SZ|BJ)\s*[.:]?\s*\d{6})"
    r"|(?:\d{6}\s*\.?\s*(?:SH|SZ|BJ|sh|sz|bj))"
    r"|(?:(?:股票|个股|证券|基金|标的)\s*代码\s*[:：]?\s*\d{5,6})"
    r"|(?:\bHK\s*\d{4,5}\b)"
    r"|(?:\b(?:NASDAQ|NYSE|纳斯达克|纽交所)\s*[:：]\s*[A-Z]{1,5}\b)"
)

# --- ② 荐股动作 -----------------------------------------------------------
_RECOMMEND = re.compile(
    r"荐股|推荐(?:买入|卖出|建仓|加仓|减仓|持有)"
    r"|(?:建议|可以|应该)\s*(?:买入|卖出|建仓|清仓|加仓|减仓|抄底|逢低吸纳)"
    r"|(?:强烈|重点)\s*推荐.{0,6}(?:股|基金|ETF|标的)"
)

# --- ③ 买卖时机 -----------------------------------------------------------
_TIMING = re.compile(
    r"(?:买入|卖出|入场|出场|建仓|清仓|抄底|逃顶)\s*(?:时机|时点|信号|点位)"
    r"|(?:现在|当前|近期|本周|今日)\s*(?:是|正是)?\s*(?:买入|卖出|入场|抄底)"
)

# --- ④ 价格预测 -----------------------------------------------------------
_PRICE_FORECAST = re.compile(
    r"目标价|目标位|股价\s*(?:将|会|预计|有望)"
    r"|(?:预计|预测|有望)\s*(?:涨|跌|上涨|下跌)\s*(?:到|至)\s*\d"
    r"|涨停|跌停|翻倍行情"
)

# --- 高危措辞（不必然违法，但必须改写）-----------------------------------
_RISKY_PHRASING = re.compile(r"投资级决策建议|投资建议|荐股|投顾服务")

_RULES: tuple[tuple[str, str, re.Pattern[str], str], ...] = (
    ("S1", "specific_security", _SECURITY_ID,
     "出现具体证券代码 —— 触及《证券法》第160条监管范围"),
    ("S2", "recommend_security", _RECOMMEND,
     "推荐具体证券买卖 —— 命中荐股软件认定标准②"),
    ("S3", "trading_timing", _TIMING,
     "给出买卖时机 —— 命中荐股软件认定标准③"),
    ("S4", "price_forecast", _PRICE_FORECAST,
     "预测证券价格走势 —— 命中荐股软件认定标准①"),
    ("S5", "risky_phrasing", _RISKY_PHRASING,
     "高危措辞 —— 应改为「商业/市场机会分析」"),
)

#: 建议替换表：把高危措辞换成安全表述
SAFE_REWRITES: tuple[tuple[str, str], ...] = (
    ("投资级决策建议", "商业/市场机会分析"),
    ("投资建议", "商业机会评估"),
    ("投顾服务", "商业研究服务"),
)


@dataclass(frozen=True)
class Violation:
    code: str
    category: str
    matched: str
    position: int
    message: str


@dataclass(frozen=True)
class GuardResult:
    blocked: bool
    violations: tuple[Violation, ...]
    text: str

    def report(self) -> tuple[str, ...]:
        if not self.violations:
            return ("证券边界检查：通过",)
        return tuple(
            f"🔴 [{v.code}/{v.category}] 位置 {v.position}「{v.matched}」—— {v.message}"
            for v in self.violations
        )


def scan(text: str) -> tuple[Violation, ...]:
    """按固定规则顺序扫描，返回全部命中。"""
    found: list[Violation] = []
    for code, category, pattern, message in _RULES:
        for match in pattern.finditer(text):
            found.append(Violation(code, category, match.group(0), match.start(), message))
    # 按位置排序，保证确定性
    return tuple(sorted(found, key=lambda v: (v.position, v.code)))


def rewrite_risky_phrasing(text: str) -> str:
    """把可安全改写的高危措辞替换掉（只处理 S5 类）。"""
    out = text
    for risky, safe in SAFE_REWRITES:
        out = out.replace(risky, safe)
    return out


def guard(text: str, auto_rewrite: bool = True) -> GuardResult:
    """输出层闸门。

    S5（措辞）可自动改写后放行；S1–S4（真正触及具体证券）一律阻断，
    **不做自动改写** —— 改写会掩盖问题，而这类内容根本不该生成。
    """
    working = rewrite_risky_phrasing(text) if auto_rewrite else text
    violations = scan(working)
    hard = tuple(v for v in violations if v.code != "S5")
    return GuardResult(blocked=bool(hard), violations=violations, text=working)


def assert_safe(text: str) -> str:
    """在报告导出路径上调用；命中硬违规直接抛错，不允许静默通过。"""
    result = guard(text)
    if result.blocked:
        detail = "\n".join(result.report())
        raise PermissionError("输出触及具体证券，已阻断：\n" + detail)
    return result.text


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

#: 必须 100% 拦截
_MUST_BLOCK: tuple[str, ...] = (
    "建议买入 sh600519，目标价 2000 元",
    "股票代码：000858，现在是买入时机",
    "强烈推荐这只基金，近期可以抄底",
    "该股目标位看到 50 元，股价将持续上涨",
    "600036.SH 值得建仓",
    "NASDAQ: AAPL 建议加仓",
    "本周正是入场时机，逢低吸纳",
)

#: 必须 0 误杀 —— 纯商业机会分析
_MUST_PASS: tuple[str, ...] = (
    "该品类需求增速 45%，供给增速 12%，剪刀差 33 个百分点，窗口开着。",
    "建议先做 10 个用户访谈验证切换势能，成本上限 5000 元。",
    "TAM = 潜在客户数 × 客户年均支出 = 200 万人 × 800 元 = 16 亿元。",
    "这个赛道白牌占比高，靠供应链和运营即可切入。",
    "落地页留资率低于 15% 说明痛点是假的，应停止投入。",
    "初期投入 50 万元用于打样和测流量，止损线设在 15 万元。",
    "该商机的资源匹配度为 68 分，团队缺销售技能。",
)


def _selftest() -> int:
    failures = 0

    def check(label: str, ok: bool) -> None:
        nonlocal failures
        if not ok:
            failures += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")

    print("oic.compliance.securities_guard 自检\n")
    print("必须拦截：")
    for sample in _MUST_BLOCK:
        result = guard(sample)
        check(f"拦截「{sample[:28]}…」", result.blocked)

    print("\n必须放行（0 误杀）：")
    for sample in _MUST_PASS:
        result = guard(sample)
        codes = ",".join(v.code for v in result.violations)
        check(f"放行「{sample[:28]}…」{' 误报:' + codes if codes else ''}",
              not result.blocked)

    print("\n措辞改写：")
    rewritten = guard("本报告提供投资级决策建议。")
    check("高危措辞被改写", "商业/市场机会分析" in rewritten.text)
    check("改写后不阻断", not rewritten.blocked)

    print("\n硬闸门：")
    try:
        assert_safe("建议买入 sh600519")
        check("assert_safe 抛 PermissionError", False)
    except PermissionError:
        check("assert_safe 抛 PermissionError", True)
    check("assert_safe 放行纯商业文本",
          assert_safe("剪刀差 33% 且成熟度 L2") is not None)

    print(f"\n{'全部通过' if failures == 0 else f'{failures} 项失败'}")
    return 1 if failures else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)
