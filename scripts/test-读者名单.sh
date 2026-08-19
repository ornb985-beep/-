#!/usr/bin/env bash
# 读者名单自测：谁不许读老板的信念库。不花钱、不联网。
#
# 为什么这条要有牙齿：
# references/创造者语言库/价值内核.md 第 6 行写着
# 「读者名单：表达层可读；【分析层、风控、查证方不许读】。」
# 理由很硬——【反方拿着老板的信念去反驳老板，等于没有反方】，
# 这条一破，核心一（判断真独立）整个白做。
#
# 但在这条测试之前，那句话只是一行字：谁在 roles-模板/风控.md 的
# 「上下文：」行里加一句 价值内核.md，没有任何东西会报错。
# 这个仓库的惯例是【规矩写进代码硬查】（六条不许就是这么做的），
# 所以这条也得有一把会响的尺子。
#
# 想亲眼看它会红：BREAK=1 bash scripts/test-读者名单.sh
#   会把 价值内核.md 塞进沙盘里风控的「上下文：」行——这正是要防的那件事。

set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FAILED=0
pass() { printf '  [通过] %s\n' "$1"; }
fail() { printf '  [失败] %s\n' "$1"; FAILED=1; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
SB="$TMP/roles"; mkdir -p "$SB"
cp "$REPO"/roles-模板/*.md "$SB/"

# 不许读信念库的：反方 ＋ 分析层 ＋ 查证方。
# 名单写在这儿而不是猜，改名单要连同 价值内核.md 那行一起改。
BANNED=(风控 战略 财务 合规 行研 增长 竞品 技术 运营 数据 产品 参谋长)

# —— 故意弄坏（证明测试会红）：把信念库塞进风控的上下文 ——
# 注入点落在【被扫描的角色文件】上，不是落在下面的期望值上。
if [ -n "${BREAK:-}" ]; then
  sed -i 's#^上下文：#上下文：价值内核.md #' "$SB/风控.md"
fi

echo
echo "=== 读者名单自测（反方不许读老板的信念库） ==="

# 1. 名单里的角色，上下文行都不许出现信念库
bad=0
for r in "${BANNED[@]}"; do
  f="$SB/$r.md"
  [ -f "$f" ] || continue
  line="$(grep -m1 '^上下文：' "$f" 2>/dev/null || true)"
  case "$line" in
    *价值内核*|*认可的*)
      fail "「$r」的上下文行里出现了信念库 —— 反方拿着老板的信念反驳老板，等于没有反方"
      printf '         %s\n' "$line"
      bad=1
      ;;
  esac
done
[ "$bad" -eq 0 ] && pass "分析层／风控／查证方，没有一个读得到信念库"

# 2. 尺子本身要能扫到东西——名单里的角色文件真的存在，别扫了个空还报绿
hit=0
for r in "${BANNED[@]}"; do [ -f "$SB/$r.md" ] && hit=$((hit+1)); done
[ "$hit" -ge 8 ] && pass "尺子真扫到了 $hit 个角色文件（不是扫了空气报绿）" \
                  || fail "只找到 $hit 个角色文件，尺子可能扫错地方了"

# 3. 名单这件事得在文档里有唯一真身，不能只活在这个脚本里
KB="$REPO/references/创造者语言库/价值内核.md"
if [ -f "$KB" ] && grep -q "不许读" "$KB"; then
  pass "价值内核.md 里写着读者名单（这个脚本守的是那句话，不是自己发明的）"
else
  fail "价值内核.md 里找不到读者名单 —— 那这条测试守的是什么？"
fi

echo
if [ "$FAILED" -eq 0 ]; then echo "读者名单自测：全部通过"; else echo "读者名单自测：有失败"; fi
exit "$FAILED"
