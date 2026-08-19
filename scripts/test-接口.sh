#!/usr/bin/env bash
# 「每个员工是不是真的一个独立接口」自测。
#
# 为什么必须有这个测试：
# 换接口这件事，最坏的失败方式不是报错，是【看起来换了但其实没换】——
# 你以为客服在用便宜的 DeepSeek，实际上他一直在烧官方的钱，
# 而账单里那个数字还是按官方价目表算的，你完全看不出来。
#
# 所以这里不测"命令跑没跑成功"，测的是：
#   调用这个员工的时候，claude 这个程序【真正收到的环境变量】是什么。
# 办法是用一个假的 claude，让它把自己收到的环境倒出来。
#
# 不花钱、不联网、几秒钟跑完。

set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FAILED=0
pass() { printf '  [通过] %s\n' "$1"; }
fail() { printf '  [失败] %s\n' "$1"; FAILED=1; }
check() { # check <说明> <期望> <实际>
  if [ "$2" = "$3" ]; then pass "$1"
  else fail "$1"; printf '         期望：%s\n         实际：%s\n' "$2" "$3"; fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# ---- 一个假的 claude：不联网，只把自己收到的环境倒进文件 ----
mkdir -p "$TMP/bin"
cat > "$TMP/bin/claude" <<'FAKE'
#!/usr/bin/env bash
cat > /dev/null            # 提示词从 stdin 进来，丢掉
{
  echo "BASE_URL=${ANTHROPIC_BASE_URL:-}"
  echo "MODEL=${ANTHROPIC_MODEL:-}"
  echo "TOKEN=${ANTHROPIC_AUTH_TOKEN:-}"
  echo "APIKEY=${ANTHROPIC_API_KEY:-}"
  echo "PROVIDER=${LOOP_PROVIDER:-}"
  echo "ARGS=$*"
} >> "$FAKE_CLAUDE_DUMP"
# 装成 --output-format json 的正常返回
echo '{"result":"假的回答","total_cost_usd":0.01,"duration_ms":1000}'
FAKE
chmod +x "$TMP/bin/claude"

# ---- 一个干净的沙盘，别碰用户真实的 .loop ----
export ROOT="$TMP/sandbox"
mkdir -p "$ROOT/docs"
cp -r "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/roles-模板" "$ROOT/" 2>/dev/null || true
# shellcheck disable=SC1091
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

export CLAUDE_BIN="$TMP/bin/claude"
export FAKE_CLAUDE_DUMP="$TMP/dump.txt"

mkdir -p "$ROLE_DIR"
printf '层：执行\n一句话：管客服的\n\n你是客服。\n'   > "$(role_file 客服)"
printf '层：参谋\n一句话：管战略的\n\n你是战略。\n'   > "$(role_file 战略)"
printf '层：执行\n一句话：管内容的\n模型：sonnet\n\n你是内容。\n' > "$(role_file 内容)"

echo
echo "=== 接口隔离自测 ==="

# ---------- 1. 默认全走官方 ----------
check "没配接口时，认定是官方" "官方" "$(role_provider 客服)"

# ---------- 2. 切一个人，只有他变 ----------
provider_save_key deepseek "sk-假钥匙-测试用"
provider_apply 客服 deepseek
check "切过的人认得出是 deepseek" "deepseek" "$(role_provider 客服)"
check "没切的人还是官方"          "官方"     "$(role_provider 战略)"

# ---------- 3. 真调用一次，看 claude 到底收到什么 ----------
: > "$FAKE_CLAUDE_DUMP"
NO_GROUP_CHAT=1 ROLE_ISOLATED=1 ask_role 客服 "随便问一句" >/dev/null 2>&1
got_url="$(grep -m1 '^BASE_URL=' "$FAKE_CLAUDE_DUMP" | cut -d= -f2-)"
got_mdl="$(grep -m1 '^MODEL='    "$FAKE_CLAUDE_DUMP" | cut -d= -f2-)"
got_tok="$(grep -m1 '^TOKEN='    "$FAKE_CLAUDE_DUMP" | cut -d= -f2-)"
got_key="$(grep -m1 '^APIKEY='   "$FAKE_CLAUDE_DUMP" | cut -d= -f2-)"
check "客服 真的连到 DeepSeek"     "https://api.deepseek.com/anthropic" "$got_url"
check "客服 真的用 v4-pro"         "deepseek-v4-pro"                    "$got_mdl"
check "客服 真的用那把新钥匙"       "sk-假钥匙-测试用"                    "$got_tok"
check "官方 key 被清掉了（不打架）" ""                                   "$got_key"

# ---------- 4. 同一秒问另一个人，他不该被污染 ----------
: > "$FAKE_CLAUDE_DUMP"
NO_GROUP_CHAT=1 ROLE_ISOLATED=1 ask_role 战略 "随便问一句" >/dev/null 2>&1
got_url2="$(grep -m1 '^BASE_URL=' "$FAKE_CLAUDE_DUMP" | cut -d= -f2-)"
got_tok2="$(grep -m1 '^TOKEN='    "$FAKE_CLAUDE_DUMP" | cut -d= -f2-)"
# 注意这里不能断言"地址是空的"——机器上本来可能就设了官方地址，
# 那是正常的、该继承的。要断言的是：他【没有】拿到 DeepSeek 那个地址。
case "$got_url2" in
  *deepseek*) fail "战略 被 DeepSeek 污染了（地址=$got_url2）" ;;
  *) pass "战略 没被 DeepSeek 污染（地址=${got_url2:-默认})" ;;
esac
check "战略 没拿到别人的钥匙" "" "$got_tok2"

# ---------- 5. 出事时要能说清为什么（LAST_LOG 必须活着穿过子 shell） ----------
# 这条测的是一个真栽过的坑：接了别家接口的角色，claude_run 在子 shell 里跑，
# 子 shell 里的赋值出不来，于是"没通"报得出来、"为什么没通"整段空白。
[ -n "${LAST_LOG:-}" ] && [ -f "$LAST_LOG" ] \
  && pass "换过接口的员工，出事时还能拿到日志（LAST_LOG 活着）" \
  || fail "换过接口的员工的日志路径丢了——出事只会说'没通'，说不出为什么"

# ---------- 6. 台账必须标出这笔走的谁家 ----------
last_provider="$(tail -1 "$COST_LOG" 2>/dev/null | awk -F'\t' '{print $5}')"
check "账单标了走的谁家接口" "官方" "$last_provider"

# ---------- 7. 接口指定了模型，就不许再传角色定义里的「模型：」 ----------
# 拿别家的接口点一道人家菜单上没有的菜，只会调不通。
provider_apply 内容 deepseek
: > "$FAKE_CLAUDE_DUMP"
NO_GROUP_CHAT=1 ROLE_ISOLATED=1 ask_role 内容 "随便问一句" >/dev/null 2>&1
if grep -q '^ARGS=.*--model sonnet' "$FAKE_CLAUDE_DUMP"; then
  fail "接口已指定模型，却还把角色定义里的「模型：sonnet」传过去了"
else
  pass "接口指定了模型时，不再传角色定义里的「模型：」"
fi

# ---------- 8. 换回官方要换得干净 ----------
provider_apply 客服 官方
check "换回官方后认定为官方" "官方" "$(role_provider 客服)"
[ -f "$(role_env 客服)" ] && fail "换回官方了，接口文件却还在" \
  || pass "换回官方后，接口文件清干净了"

echo
if [ "$FAILED" = 0 ]; then echo "接口隔离自测：全部通过"; else echo "接口隔离自测：有失败项"; fi
exit "$FAILED"
