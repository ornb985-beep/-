#!/usr/bin/env bash
# 公共函数库。被 loop.sh 和其他脚本 source，不单独执行。

# ---------- 颜色（终端不支持时自动降级为空串） ----------
if [ -t 1 ] && command -v tput >/dev/null 2>&1 && [ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]; then
  C_BOLD="$(tput bold)"; C_DIM="$(tput dim)"; C_RED="$(tput setaf 1)"
  C_GREEN="$(tput setaf 2)"; C_YELLOW="$(tput setaf 3)"; C_BLUE="$(tput setaf 4)"
  C_OFF="$(tput sgr0)"
else
  C_BOLD=""; C_DIM=""; C_RED=""; C_GREEN=""; C_YELLOW=""; C_BLUE=""; C_OFF=""
fi

say()   { printf '%s\n' "$*"; }
info()  { printf '%s▸%s %s\n' "$C_BLUE" "$C_OFF" "$*"; }
ok()    { printf '%s✓%s %s\n' "$C_GREEN" "$C_OFF" "$*"; }
warn()  { printf '%s!%s %s\n' "$C_YELLOW" "$C_OFF" "$*"; }
die()   { printf '%s✗%s %s\n' "$C_RED" "$C_OFF" "$*" >&2; exit 1; }
title() { printf '\n%s%s%s\n' "$C_BOLD" "$*" "$C_OFF"; }
rule()  { printf '%s%s%s\n' "$C_DIM" "────────────────────────────────────────────────────────" "$C_OFF"; }

# ---------- 路径 ----------
# ROOT 由调用方设置；这里兜底
ROOT="${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STATE_DIR="$ROOT/.loop"
LOG_DIR="$STATE_DIR/log"
DOC_DIR="$ROOT/docs"
CMD_DIR="$ROOT/.claude/commands"

# ---------- 状态读写（纯文本，不依赖 jq） ----------
# 每个状态是一个文件，内容就是值。最笨但最不会坏。
state_get() {
  local key="$1" default="${2:-}"
  if [ -f "$STATE_DIR/$key" ]; then cat "$STATE_DIR/$key"; else printf '%s' "$default"; fi
}
state_set() {
  local key="$1" value="$2"
  mkdir -p "$STATE_DIR"
  printf '%s' "$value" > "$STATE_DIR/$key"
}

# ---------- 阶段定义 ----------
# 顺序即流水线顺序。改这里就能增删阶段。
STAGES=(goal giants edge taste spec unknowns stack plan build done)

# 阶段的中文名，给人看的
stage_label() {
  case "$1" in
    goal)     echo "第1步 · 把想法变成一句能落地的目标" ;;
    giants)   echo "第2步 · 站在巨人肩上：把前人最好的全扒出来" ;;
    edge)     echo "第3步 · 共性与独特：凭什么是我们（只有你能拍板）" ;;
    taste)    echo "第4步 · 定义什么叫「做得好」（只有你能拍板）" ;;
    spec)     echo "第5步 · 把目标拆成具体要做的东西" ;;
    unknowns) echo "第6步 · 找出你不知道的事，并讲明白" ;;
    stack)    echo "第7步 · 决定在哪儿落地、用什么做" ;;
    plan)     echo "第8步 · 排成一份可勾选的任务清单" ;;
    build)    echo "第9步 · 自动开做：做→检查→修，循环到过关" ;;
    done)     echo "完成 · 所有任务已勾完" ;;
    *)        echo "$1" ;;
  esac
}

# 这个阶段做完后，是否需要你本人点头确认
# 判断依据：这一步定的是「生意问题」还是「技术问题」。生意问题必须你拍板。
stage_needs_signoff() {
  case "$1" in
    edge|taste|spec|stack) return 0 ;;
    *) return 1 ;;
  esac
}

# 阶段产出的文档
stage_doc() {
  case "$1" in
    goal)     echo "$DOC_DIR/00-目标.md" ;;
    giants)   echo "$DOC_DIR/01-巨人的肩膀.md" ;;
    edge)     echo "$DOC_DIR/02-共性与独特.md" ;;
    taste)    echo "$DOC_DIR/03-什么算好.md" ;;
    spec)     echo "$DOC_DIR/04-要做什么.md" ;;
    unknowns) echo "$DOC_DIR/05-我不懂的.md" ;;
    stack)    echo "$DOC_DIR/06-技术与落地.md" ;;
    plan)     echo "$DOC_DIR/07-任务清单.md" ;;
    *)        echo "" ;;
  esac
}

# 任务清单的路径，多处用到，集中在这里
TASKS_FILE="$DOC_DIR/07-任务清单.md"

stage_index() {
  local want="$1" i=0
  for s in "${STAGES[@]}"; do
    [ "$s" = "$want" ] && { echo "$i"; return 0; }
    i=$((i+1))
  done
  echo "-1"
}

next_stage() {
  local i; i="$(stage_index "$1")"
  [ "$i" -lt 0 ] && { echo "goal"; return; }
  local n=$((i+1))
  if [ "$n" -ge "${#STAGES[@]}" ]; then echo "done"; else echo "${STAGES[$n]}"; fi
}

# ---------- 调用 Claude ----------
CLAUDE_BIN="${CLAUDE_BIN:-claude}"

# 每一步需要用到的工具，直接点名放行。
#
# 为什么要显式写出来：工作目录没被"信任"过的时候，
# .claude/settings.json 里的权限会被【整个忽略】，
# 于是联网搜索被挡 → 第2步查不了资料 → 整条 loop 卡死在这儿。
# 这是第一次真跑时的实际死因，不是理论问题。
#
# 显式放行比依赖信任开关好：别人 clone 走这个模板，不用改自己的全局配置就能跑。
LOOP_ALLOWED_TOOLS="${LOOP_ALLOWED_TOOLS:-WebSearch WebFetch Read Write Edit Glob Grep TodoWrite Bash}"

have_claude() { command -v "$CLAUDE_BIN" >/dev/null 2>&1; }

# 最近一次调用的日志路径，claude_run 里赋值
LAST_LOG=""

# 分清「外面的原因」和「这一步真做错了」。
#
# 这两种失败在屏幕上长得一模一样（都是"没跑成功"），但处理方式完全相反：
#   额度用完/断网 → 等一会儿再跑就好，重跑一百次也没用
#   真做错了      → 得看日志改东西，不改再跑还是错
#
# 为什么要专门写这个：第一次跑到底的测试里，AI 额度用完了，
# 而循环分不清这两种情况，对着同一个"额度已用完"空转重试了 5 次。
# 分不清的代价不是白等，是把剩下的额度也烧在无用功上。
#
# 输出：<类型>制表符<日志里的原话>；不是外部原因就返回 1。
blocker_reason() {
  local logf="$1" line
  [ -f "$logf" ] || return 1
  line="$(grep -m1 -iE 'hit your (session|usage) limit|usage limit reached|rate limit|too many requests|credit balance|quota exceeded' "$logf" 2>/dev/null || true)"
  [ -n "$line" ] && { printf '%s\t%s' quota "$line"; return 0; }
  line="$(grep -m1 -iE 'getaddrinfo|ENOTFOUND|ECONNREFUSED|ETIMEDOUT|fetch failed|network error|socket hang up' "$logf" 2>/dev/null || true)"
  [ -n "$line" ] && { printf '%s\t%s' network "$line"; return 0; }
  return 1
}

# claude_run <提示词文件> [附加上下文文件...]
# 把提示词和上下文拼起来丢给 claude；没装 claude 就把提示词存下来让用户手动贴。
# 去掉说明书开头那段 --- 包起来的标注（它是给 slash command 用的）。
# 不去掉的话，提示词以 --- 开头，会被命令行当成一个选项，直接报
# "unknown option"——每一步都会挂。这个 bug 用假 claude 测不出来。
strip_frontmatter() {
  sed '1{/^---$/!q};1,/^---$/d' "$1"
}

claude_run() {
  local prompt_file="$1"; shift
  local ctx="" f
  for f in "$@"; do
    [ -f "$f" ] && ctx+=$'\n\n---- 已有资料：'"$(basename "$f")"$' ----\n'"$(cat "$f")"
  done

  local prompt
  prompt="$(strip_frontmatter "$prompt_file")$ctx"

  mkdir -p "$LOG_DIR"
  local ts; ts="$(date +%Y%m%d-%H%M%S)"
  local logf="$LOG_DIR/$ts-$(basename "$prompt_file" .md).log"
  LAST_LOG="$logf"   # 出事的时候要回头翻这个日志，见 blocker_reason

  if ! have_claude; then
    local dump="$STATE_DIR/待手动执行.txt"
    printf '%s' "$prompt" > "$dump"
    warn "没找到 claude 命令，无法自动跑。"
    say  "  提示词已存到：$dump"
    say  "  你可以打开 Claude Code，把这个文件的内容整段贴进去，效果一样。"
    return 3
  fi

  # 提示词走标准输入，不走命令行参数。两个原因：
  #   1. 参数里的特殊开头（比如 ---）会被当成选项
  #   2. 上下文越堆越长，迟早撞上命令行长度上限，走标准输入没这个限制
  # --permission-mode acceptEdits：允许它直接改文件，否则每步都要你按确认，就不叫自动了
  # shellcheck disable=SC2086
  printf '%s' "$prompt" | "$CLAUDE_BIN" -p \
      --permission-mode acceptEdits \
      --allowedTools $LOOP_ALLOWED_TOOLS 2>&1 | tee "$logf"
  return "${PIPESTATUS[1]}"
}

# ---------- 任务清单进度 ----------
# grep -c 在"无匹配"时会输出 0 但返回码非 0，在"文件不存在"时什么都不输出，
# 所以统一兜底成 0，避免后面做算术时炸掉。

# 任务清单末尾有一节「怎么验收这一步」，里面也是 - [ ] 格式，
# 但那是给人对照着检查的，不是要 AI 去做的任务。
# 不排掉的话有两个后果：①任务数虚高，进度全是假的
# ②自动循环走到最后会真的去"做"验收项，比如
#   「所有任务都是 - [ ] 开头的标准格式」——这条根本没法做，循环就死在这儿。
tasks_region() {
  awk '/^##[[:space:]]*怎么验收/ { exit } { print }' "$TASKS_FILE" 2>/dev/null
}

_count() {
  local n
  n="$(tasks_region | grep -cE "$1" 2>/dev/null || true)"
  echo "${n:-0}"
}
tasks_total()   { _count '^[[:space:]]*- \[[ xX]\] '; }
tasks_done()    { _count '^[[:space:]]*- \[[xX]\] '; }
tasks_open()    { _count '^[[:space:]]*- \[ \] '; }
next_task() {
  tasks_region | grep -m1 -E '^[[:space:]]*- \[ \] ' 2>/dev/null \
    | sed -E 's/^[[:space:]]*- \[ \] //' || true
}

# 一条任务在清单里常常是好几行：第一行是标题，后面缩进的是细节。
# 只拿第一行会把关键信息切掉（比如"要你回答什么"正好在第二行），
# 所以连着续行一起取。
next_task_block() {
  tasks_region | awk '
    /^[[:space:]]*- \[ \] / && !found { found=1; print; next }
    found && /^[[:space:]]*- \[[ xX]\] / { exit }
    found && /^#/ { exit }
    found { print }
  ' | sed -e :a -e '/^[[:space:]]*$/{$d;N;ba' -e '}'
}

# 任务清单里有两种任务，AI 干不了，只有人能干：
#   【需要你回答】  要你提供它不可能知道的事实（你的经历、你的预算、你的偏好）
#   【停下来给我看】 要你亲眼验一遍，它自己说"做完了"不算数
#
# 为什么要专门认这两个标记：第一次真跑第9步的时候，任务清单第一条就是
# 【需要你回答】。循环照样派 AI 去做，AI 很正确地拒绝替人编，把问题问了出来——
# 但问题落在日志里没人看，循环只看到"任务没被勾掉"，于是报「可能它忘了勾」，
# 还建议人"手动勾掉这条"。三个错叠一起：冤枉了它、问题被吞掉、31 个任务卡在 0。
#
# 分不清「这条得等人」和「它偷懒」，整个第9步就废了。
HUMAN_GATE_RE='【需要你回答】|【停下来给我看】'
task_is_human_gated() { printf '%s' "$1" | grep -qE "$HUMAN_GATE_RE"; }
tasks_human_gated()   { _count "^[[:space:]]*- \[ \] .*(${HUMAN_GATE_RE})"; }
