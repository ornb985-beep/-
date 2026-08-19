#!/usr/bin/env bash
# 试金石命令的自测。不花钱、不联网(用假 claude)。
#
# 守四件事:
#   1. 没设预算不让起跑(闸门前置,不许跑一半没钱)
#   2. 两个模型各跑一次,分歧数出来(数字,不是"大致相同")
#   3. 调用日志里的模型和要的对不上,必须当场死——配置写的不等于真用的(第 6 条)
#   4. 分歧为 0 时必须报警,不许绿色通过——「全票通过应该触发警报,不是让人放心」
#
# 想亲眼看它会红:BREAK=1 bash scripts/test-试金石.sh
#   会把沙盒里【loop.sh 本体】的模型验证掐掉(if 条件改成 false),
#   于是说谎的模型溜过去,第 3 件事的断言必须红。注入点在被测代码上。

set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FAILED=0
pass() { printf '  [通过] %s\n' "$1"; }
fail() { printf '  [失败] %s\n' "$1"; FAILED=1; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

# ---- 沙盒:整套拷进去,不碰真仓库的 .loop ----
SB="$TMP/sandbox"
mkdir -p "$SB/.claude/commands" "$SB/.loop/接口"
cp "$REPO/loop.sh" "$SB/"
cp -r "$REPO/scripts" "$SB/"
rm -rf "$SB/scripts/__pycache__"
cp "$REPO/.claude/commands/听懂.md" "$SB/.claude/commands/"
chmod +x "$SB/loop.sh"
printf 'ANTHROPIC_AUTH_TOKEN=fake-key-for-test\nunset ANTHROPIC_API_KEY\n' > "$SB/.loop/接口/deepseek.key"

if [ -n "${BREAK:-}" ]; then
  sed -i 's/if \[ "\$actual" != "\$model" \]; then/if false; then/' "$SB/loop.sh"
fi

# ---- 假 claude:不联网,按收到的环境变量报模型;能被指使说谎/输出全一致 ----
mkdir -p "$TMP/bin"
cat > "$TMP/bin/claude" <<'FAKE'
#!/usr/bin/env bash
cat > /dev/null
rep="${ANTHROPIC_MODEL:-?}"
[ -n "${FAKE_LIE:-}" ] && rep="deepseek-v4-pro"
variant="${ANTHROPIC_MODEL:-?}"
[ -n "${FAKE_SAME:-}" ] && variant="deepseek-v4-pro"
# FAKE_NOISY:同一个模型第二次跑就换个答案——模拟「模型自己抖」。
# 真事:2026-08-18 flash 对同一句话上午判 ★★、下午判 ★★★。
if [ -n "${FAKE_NOISY:-}" ]; then
  cnt="$(cat "${NOISE_COUNTER:-/tmp/nc}" 2>/dev/null || echo 0)"
  cnt=$((cnt+1)); echo "$cnt" > "${NOISE_COUNTER:-/tmp/nc}"
  [ "$cnt" = 2 ] && variant="第二次就变了"
fi
python3 - "$rep" "$variant" <<'PY'
import json, sys
rep, variant = sys.argv[1], sys.argv[2]
star1 = "★★" if variant == "deepseek-v4-pro" else "★"
result = f"""# 00 · 我听到的

原话：「我要一个记账的东西，老是忘了记。」

| # | 你原话里的哪句 | 这是什么 | 轻重 | 为什么这么判 |
|---|---|---|---|---|
| 1 | 「我要一个记账的东西」 | 方案 | {star1} | 方案不是问题 |
| 2 | 「老是忘了记」 | 痛点 | ★★★ | 频次词 |

一点推断 `[推断]`
"""
print(json.dumps({"result": result, "total_cost_usd": 0.01, "duration_ms": 5,
                  "modelUsage": {rep: {"inputTokens": 1, "outputTokens": 1}}}))
PY
FAKE
chmod +x "$TMP/bin/claude"

run() { ( cd "$SB" && CLAUDE_BIN="$TMP/bin/claude" ./loop.sh "$@" ); }

echo
echo "=== 试金石自测 ==="

# ---------- 一、没设预算不让起跑 ----------
out="$(run 试金石 "随便一句" 2>&1)"; rc=$?
[ "$rc" -ne 0 ] && printf '%s' "$out" | grep -q "budget" \
  && pass "没设预算:拦住了,并指路 budget" \
  || fail "没设预算:该拦住并提示设上限(rc=$rc)"

echo 5 > "$SB/.loop/budget"

# ---------- 二、正常跑:两腿都验明正身,分歧是数字 ----------
out="$(run 试金石 "随便一句" 2>&1)"; rc=$?
[ "$rc" -eq 0 ] && pass "两腿都跑完:退出码 0" || fail "两腿该跑完(rc=$rc)"
printf '%s' "$out" | grep -q "真用的是 deepseek-v4-pro" \
  && pass "pro 腿验明正身(从调用日志)" || fail "没验出 pro 腿的真实模型"
printf '%s' "$out" | grep -q "真用的是 deepseek-v4-flash" \
  && pass "flash 腿验明正身(从调用日志)" || fail "没验出 flash 腿的真实模型"
printf '%s' "$out" | grep -q "相同 1 对,不同 1 对" \
  && pass "分歧是数字:相同 1 / 不同 1" || fail "分歧没数出来(该是 相同 1 对,不同 1 对)"
printf '%s' "$out" | grep -q "全票一致——这是警报" \
  && fail "有分歧还报了全票警报" || pass "有分歧时没有误报警报"

# ---------- 三、模型说谎必须当场死(第 6 条) ----------
out="$(FAKE_LIE=1 run 试金石 "随便一句" 2>&1)"; rc=$?
[ "$rc" -ne 0 ] && printf '%s' "$out" | grep -q "模型验证失败" \
  && pass "说谎的模型被当场抓住,命令非零退出" \
  || fail "模型说谎没被抓住——配置写的不等于真用的(rc=$rc)"

# ---------- 四、全票一致必须报警,不许绿色通过 ----------
out="$(FAKE_SAME=1 run 试金石 "随便一句" 2>&1)"; rc=$?
[ "$rc" -ne 0 ] && pass "全票时退出码非 0(不算通过)" || fail "全票时退出码该非 0(rc=$rc)"
printf '%s' "$out" | grep -q "全票一致——这是警报" \
  && pass "全票时打出了警报" || fail "全票时没报警"
printf '%s' "$out" | grep -q "全票通过应该触发警报" \
  && pass "警报里带着交接包那句原话" || fail "警报里少了交接包那句原话"

# ---------- 五、比对工具自己崩了,不许长得像通过(第 2 条) ----------
#
# 这一节补的是一个真漏:旧代码 `out="$(python3 对分歧.py …)" || true`
# 把 0/1/2 三个退出码全丢了。对分歧.py 特意用 exit 2 表示「解析不了」,
# 被 || true 静音之后,全票警报的 grep 匹配不上、照样打印「分歧就是信息」、
# 退出码 0——【比对失败长得跟比对成功一模一样】。
# 注入点在被测代码上:把沙盘里的 对分歧.py 换成一个必崩的假货。
cp "$SB/scripts/对分歧.py" "$SB/scripts/对分歧.py.bak"
printf '#!/usr/bin/env python3\nimport sys\nsys.stderr.write("解析不了\\n")\nsys.exit(2)\n' \
  > "$SB/scripts/对分歧.py"

out="$(run 试金石 "随便一句" 2>&1)"; rc=$?
[ "$rc" -ne 0 ] && pass "比对工具崩了,命令非零退出(没当成通过)" \
                || fail "比对工具崩了却退出 0——这就是假绿(rc=$rc)"
printf '%s' "$out" | grep -q "分歧没数成" \
  && pass "崩了的时候明说「没数成」" || fail "崩了却没说没数成"
printf '%s' "$out" | grep -q "不算数" \
  && pass "崩了的时候明说这一跑不算数" || fail "崩了却没说这一跑不算数"
printf '%s' "$out" | grep -q "分歧就是信息" \
  && fail "崩了还打印了让人放心的那句「分歧就是信息」" \
  || pass "崩了就不再打印任何让人放心的话"

mv "$SB/scripts/对分歧.py.bak" "$SB/scripts/对分歧.py"

# ---------- 六、噪声底：同一个模型自己抖得比换脑子还多，不许算证据 ----------
#
# 这一节防的是核心一唯一那份证据的地基：
# 「两个模型差了 N 句」听起来像证据，可要是同一个模型自己跑两次也差 N 句，
# 那 N 句跟换不换脑子毫无关系——买到的是噪声，不是判断。
# 真事：2026-08-18 flash 对「每天一百多款」上午判 ★★、下午判 ★★★。
NC="$TMP/noise-counter"; rm -f "$NC"
out="$(FAKE_NOISY=1 NOISE_COUNTER="$NC" run 试金石 "随便一句" 2>&1)"; rc=$?
[ "$rc" -ne 0 ] && pass "自己抖得不比换脑子少时,退出码非 0(不算证据)" \
                || fail "自己抖得不比换脑子少,却当成通过了(rc=$rc)"
printf '%s' "$out" | grep -q "它自己跟自己差" \
  && pass "报告里两个数都给了(自己抖多少 / 换脑子差多少)" || fail "没报出噪声底那个数"
printf '%s' "$out" | grep -q "不许当成" \
  && pass "明说了这一跑不许当「换脑子有用」的证据" || fail "没说清这一跑不算证据"
printf '%s' "$out" | grep -q "净信号" \
  && fail "自己抖得更多,还打印了「净信号」" || pass "自己抖得更多时,不打印净信号"

echo
if [ "$FAILED" = 0 ]; then echo "试金石自测:全部通过"; else echo "试金石自测:有失败项"; fi
exit "$FAILED"
