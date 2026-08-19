#!/usr/bin/env bash
# 面板自测。不花钱、不联网（用假的 loop.sh，不真跑 claude）。
#
# 面板最坏的失败方式不是打不开，是【网页上点了，屏幕说好了，.loop/ 里什么都没变】，
# 或者反过来——【一个本不该让网页碰的命令，被放进去跑了】。
# 所以这里不测"接口返回 200"，测两件真事：
#   1. 白名单外的命令，到底有没有【真的】被挡住
#   2. 点了按钮之后，.loop/ 里到底有没有【真的】发生变化
#
# 想亲眼看它会红：BREAK=1 bash scripts/test-面板.sh
#   会把沙盘里那道白名单检查掐掉——接口照样返回 200，但 reset 就能被网页调用了。
#   这就是"看起来对但其实没做"，测试必须因此变红。

set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FAILED=0
pass() { printf '  [通过] %s\n' "$1"; }
fail() { printf '  [失败] %s\n' "$1"; FAILED=1; }

command -v python3 >/dev/null 2>&1 || { echo "  [跳过] 没有 python3"; exit 0; }
command -v curl    >/dev/null 2>&1 || { echo "  [跳过] 没有 curl"; exit 0; }

TMP="$(mktemp -d)"
SRV=""
cleanup() { [ -n "$SRV" ] && kill "$SRV" 2>/dev/null; rm -rf "$TMP"; }
trap cleanup EXIT

SB="$TMP/sb"; mkdir -p "$SB/.loop" "$SB/docs"
cp -r "$REPO/scripts" "$SB/"
rm -rf "$SB/scripts/__pycache__"

# —— 假 loop.sh：不真跑 claude，只把「我被调用了」写进 .loop/，供后面核对 ——
# 面板测的是"点了到底有没有真发生"，所以关键是这个副作用文件，不是屏幕上的字。
cat > "$SB/loop.sh" <<'FAKE'
#!/usr/bin/env bash
mkdir -p .loop
printf '%s\n' "$*" >> .loop/被调用了.txt
echo "假 loop.sh 跑过了：$*"
FAKE
chmod +x "$SB/loop.sh"

# —— 故意弄坏（证明测试会红）：把三条不可逆的命令塞进白名单 ——
#
# 为什么这么弄坏，而不是把那行检查删掉：删掉检查会让程序在别处崩掉，
# 测试是红了，但红的原因不对。而【有人往白名单里加了一条危险命令】
# 才是这件事真正会发生的样子——它不崩，它老老实实把 reset 跑了。
# 注入点落在被测代码上，不在下面任何一条期望值上。
if [ -n "${BREAK:-}" ]; then
  sed -i 's/^ALLOWED = {/ALLOWED = {"reset": 0, "上线": 0, "close": 0,/' "$SB/scripts/面板.py"
fi

# 一份带题的听懂产出，用来验 /api/ask 是不是真从 lib.sh 读的
cat > "$SB/docs/00-听到的.md" <<'DOC'
# 00 · 我听到的

原话：「自测用」

轮次：第 1 轮   状态：还没听懂

## 四、我不许替你猜的

### 问题 1：那位老板的数字记在哪？
- **A** 基本在脑子里
- **B** 记在表格里
- **C** 平台后台能拉

### 问题 2：这事你想做成什么
- **A** 一次性帮忙
- **B** 做成产品

## 五、我可能听错的地方
1. ____
DOC

echo
echo "=== 面板自测 ==="

# ---------- 起服务 ----------
PORT=$(( 17800 + RANDOM % 900 ))
( cd "$SB" && LOOP_PANEL_PORT="$PORT" python3 scripts/面板.py > "$TMP/srv.log" 2>&1 ) &
SRV=$!
URL=""
for _ in $(seq 1 40); do
  URL="$(head -1 "$TMP/srv.log" 2>/dev/null)"
  case "$URL" in http*) break ;; esac
  sleep 0.25
done
case "$URL" in
  http*) pass "面板起来了，第一行就是带令牌的地址" ;;
  *) fail "面板没起来（看 $TMP/srv.log）"; echo; echo "面板自测：有失败"; exit 1 ;;
esac

TOKEN="${URL##*token=}"
# 去掉「?token=…」那一截。注意 ? 在 shell 的花括号里是通配符，必须转义，
# 不转的话 ${URL%%/?*} 会把 http://127.0.0.1:7788 整段吃掉，只剩 http:
BASE="${URL%%\?*}"; BASE="${BASE%/}"
j() { curl -s -m 8 -H "X-Token: $TOKEN" -H 'Content-Type: application/json' "$@"; }

# ---------- 一、令牌：不带就不给 ----------
code="$(curl -s -m 8 -o /dev/null -w '%{http_code}' "$BASE/api/state")"
[ "$code" = "403" ] && pass "不带令牌，接口直接拒（403）" \
                    || fail "不带令牌居然给了（HTTP $code）——别的网页就能偷偷调你本机"

code="$(curl -s -m 8 -o /dev/null -w '%{http_code}' -H 'X-Token: 瞎编的' "$BASE/api/state")"
[ "$code" = "403" ] && pass "令牌错了也拒" || fail "令牌错了还给（HTTP $code）"

# ---------- 二、白名单：不可逆的东西，网页碰不到 ----------
# 这一节是这个测试存在的第一理由。
for danger in reset 上线 close; do
  r="$(j -X POST -d "{\"cmd\":\"$danger\",\"args\":[]}" "$BASE/api/run")"
  if printf '%s' "$r" | grep -q '不认识的命令'; then
    pass "「$danger」被白名单挡住了（网页点不到不可逆的事）"
  else
    fail "「$danger」竟然能从网页调用 —— 红线破了。返回：$r"
  fi
done
# 挡住之后，副作用文件里不许有它
if [ -f "$SB/.loop/被调用了.txt" ] && grep -qE '^(reset|上线|close)' "$SB/.loop/被调用了.txt"; then
  fail "挡是挡了，可 loop.sh 还是被调用了 —— 这才是最坏的那种假挡"
else
  pass "挡住的命令，loop.sh 一次都没被调用（不是嘴上挡）"
fi

# ---------- 三、白名单里的：点了要【真的】发生 ----------
j -X POST -d '{"cmd":"status","args":[]}' "$BASE/api/run" >/dev/null
for _ in $(seq 1 20); do
  [ -f "$SB/.loop/被调用了.txt" ] && grep -q '^status' "$SB/.loop/被调用了.txt" && break
  sleep 0.2
done
grep -q '^status' "$SB/.loop/被调用了.txt" 2>/dev/null \
  && pass "点了「看看到哪了」，loop.sh 真被调用了（不是只回了个 200）" \
  || fail "接口回了，但 loop.sh 没被调用 —— 屏幕说好了，底下什么都没发生"

# ---------- 四、答题：参数必须原样传下去 ----------
j -X POST -d '{"cmd":"答","args":["B"]}' "$BASE/api/run" >/dev/null
for _ in $(seq 1 20); do grep -q '^答 B' "$SB/.loop/被调用了.txt" 2>/dev/null && break; sleep 0.2; done
grep -q '^答 B' "$SB/.loop/被调用了.txt" 2>/dev/null \
  && pass "答题传下去的就是「答 B」，一个字没变" \
  || fail "答题没传对（.loop/被调用了.txt 里没有「答 B」）"

# 参数个数不对要拦——防手滑传空
r="$(j -X POST -d '{"cmd":"答","args":[]}' "$BASE/api/run")"
printf '%s' "$r" | grep -q '要 1 个参数' \
  && pass "答题少给参数会被拦" || fail "答题少给参数没拦住：$r"

# ---------- 五、/api/ask：题必须是从 lib.sh 读的 ----------
a="$(j "$BASE/api/ask")"
printf '%s' "$a" | grep -q '"第几题": *1' \
  && pass "现在轮到第 1 题（跟命令行读的是同一套）" || fail "题号不对：$a"
printf '%s' "$a" | grep -q '"共": *2' \
  && pass "数出来一共 2 题" || fail "题数不对：$a"
printf '%s' "$a" | grep -q '基本在脑子里' \
  && pass "选项被拆出来了（网页上才点得成按钮）" || fail "选项没拆出来：$a"

# 记上「第 1 题答过了」，它必须跳到第 2 题——不跳就是没真读进度
printf "1:1" > "$SB/.loop/答题进度"
a2="$(j "$BASE/api/ask")"
printf '%s' "$a2" | grep -q '"第几题": *2' \
  && pass "答过第 1 题之后，自动跳到第 2 题" || fail "没跳题（进度没真读）：$a2"

# ---------- 六、页面：令牌要真被塞进去 ----------
h="$(curl -s -m 8 "$BASE/")"
printf '%s' "$h" | grep -q '__TOKEN__' \
  && fail "页面里还留着 __TOKEN__ 没替换 —— 一点就 403" \
  || pass "页面里的令牌被替换过了"
printf '%s' "$h" | grep -q '轮到你了' \
  && pass "页面里有「轮到你了」那一块（答题是这个界面的心脏）" \
  || fail "页面里找不到答题那一块"

echo
if [ "$FAILED" -eq 0 ]; then echo "面板自测：全部通过"; else echo "面板自测：有失败"; fi
exit "$FAILED"
