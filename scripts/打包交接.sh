#!/usr/bin/env bash
# 把仓库打成三个单文件包，给拿不到仓库、只能贴文件的接手方。
# 用法：bash scripts/打包交接.sh
#
# 为什么要有这个脚本：三个 .txt 是【生成物】，不是源文件。
# 手改 .txt 等于让同一份内容有两个真身，改一处忘一处——
# 正是 references/验证的规矩.md 第 3 条骂的那种漂移。
# 改内容永远改源文件，然后跑这个脚本。
set -euo pipefail
cd "$(dirname "$0")/.."

pack() {          # pack <输出文件> <抬头> <文件...>
  local out="$1" head="$2"; shift 2
  {
    echo "═══ $head ═══"
    echo "（每个文件以「▼▼▼ FILE: 路径 ▼▼▼」开头，按这行切分）"
    echo "（生成命令：bash scripts/打包交接.sh —— 别手改这个文件，改源文件后重跑）"
    echo
    local f
    for f in "$@"; do
      [ -f "$f" ] || { echo "缺文件：$f" >&2; continue; }
      printf '\n▼▼▼ FILE: %s ▼▼▼\n' "$f"
      cat "$f"
    done
  } > "$out"
  printf '%-22s %5s 个文件 %6s 行 %6s\n' \
    "$out" "$(grep -c '^▼▼▼ FILE:' "$out")" "$(wc -l < "$out")" "$(du -h "$out" | cut -f1)"
}

pack 交接包-1-规格.txt \
  "MoneyLoop 交接包 1/3 · 规格和文档（任务书在 工程交接包.md 第五节，边界在第八节）" \
  工程交接包.md README.md CLAUDE.md references/*.md

pack 交接包-2-代码.txt \
  "MoneyLoop 交接包 2/3 · 能跑的代码（bash 为主，python 只管看板）" \
  loop.sh scripts/lib.sh scripts/check.sh scripts/状态.py scripts/看板.py \
  scripts/test-*.sh tests/*.py .gitignore

pack 交接包-3-角色.txt \
  "MoneyLoop 交接包 3/3 · 提示词和角色（每一步一份、每个角色一份）" \
  .claude/commands/*.md roles-模板/*.md
