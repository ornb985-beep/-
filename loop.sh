#!/usr/bin/env bash
# 自动化流水线主程序。
# 用法：
#   ./loop.sh start "我想做一个帮我记录客户跟进的小工具"
#   ./loop.sh go        继续往下跑
#   ./loop.sh status    看现在到哪一步了
#   ./loop.sh explain   用大白话讲一遍现在的情况
#   ./loop.sh back      退回上一步重做
#   ./loop.sh reset     全部清空重来（会先备份）

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib.sh
source "$ROOT/scripts/lib.sh"

MAX_BUILD_ROUNDS="${MAX_BUILD_ROUNDS:-30}"   # 造东西阶段最多循环多少轮，防止无限烧钱
MAX_FIX_TRIES="${MAX_FIX_TRIES:-3}"          # 单个任务测试不过，最多自动修几次

# ============================================================
# 阶段执行
# ============================================================

# 跑一个非 build 阶段
run_stage() {
  local stage="$1"
  local cmd_file="$CMD_DIR/$stage.md"
  [ -f "$cmd_file" ] || die "找不到这一步的说明书：$cmd_file"

  title "$(stage_label "$stage")"
  rule

  # 把之前所有阶段的产出当作上下文喂进去，保证它记得前因后果
  local ctx=()
  local s
  for s in "${STAGES[@]}"; do
    [ "$s" = "$stage" ] && break
    local d; d="$(stage_doc "$s")"
    [ -n "$d" ] && [ -f "$d" ] && ctx+=("$d")
  done

  local rc=0
  claude_run "$cmd_file" "${ctx[@]+"${ctx[@]}"}" || rc=$?
  if [ "$rc" -eq 3 ]; then
    return 3   # 没装 claude，已提示手动执行
  elif [ "$rc" -ne 0 ]; then
    die "这一步没跑成功（退出码 $rc）。日志在 .loop/log/ 里，可以直接把日志贴给我看。"
  fi

  local doc; doc="$(stage_doc "$stage")"
  if [ -n "$doc" ] && [ ! -f "$doc" ]; then
    warn "这一步应该产出 $doc，但没找到。可能是它写到别的地方了，去 docs/ 翻一下。"
  fi
  state_set "ran_$stage" yes    # 明确记下"这一步真的跑过了"
  return 0
}

# 需要你点头的阶段，停下来等确认
signoff_gate() {
  local stage="$1"
  local doc; doc="$(stage_doc "$stage")"

  rule
  title "该你拍板了"
  say "刚才这一步的结果写在：${C_BOLD}${doc}${C_OFF}"
  say ""
  say "请打开看一遍。这一步是${C_BOLD}你的判断${C_OFF}，不是技术问题——"
  case "$stage" in
    edge)  say "  它给出了「共性该守什么、独特该赌什么」。这是这东西的命，看仔细。" ;;
    taste) say "  它列了几个「什么算好」的标准和取舍，挑你认同的，划掉你不认同的。" ;;
    spec)  say "  它列了要做的功能和验收标准，砍掉你觉得没必要的，补上它漏掉的。" ;;
    stack) say "  它列了在哪儿落地、用什么做、大概花多少钱。你确认花销和方式能接受。" ;;
  esac
  say ""
  say "${C_DIM}提示：你直接在文件里改字、划掉、补充就行。你改过的地方，后面每一步都会当成最高优先级。${C_OFF}"
  say ""
  say "改完（或者觉得没问题）之后，跑这个继续："
  say "  ${C_BOLD}./loop.sh go${C_OFF}"
  rule
}

# ============================================================
# build 阶段：真正的自动循环
# ============================================================
run_build_loop() {
  title "$(stage_label build)"
  say "${C_DIM}规则：挑一个任务 → 做 → 跑检查 → 不过就自己修（最多 ${MAX_FIX_TRIES} 次）→ 过了就勾掉，下一个${C_OFF}"
  rule

  local round=0
  while :; do
    local open; open="$(tasks_open)"
    if [ "$open" -eq 0 ]; then
      ok "任务清单全部勾完了。"
      return 0
    fi

    round=$((round+1))
    if [ "$round" -gt "$MAX_BUILD_ROUNDS" ]; then
      warn "已经跑了 $MAX_BUILD_ROUNDS 轮，先停下来喘口气（防止无限循环烧钱）。"
      say  "确认没问题就再跑一次 ./loop.sh go 继续，或者调大 MAX_BUILD_ROUNDS。"
      return 1
    fi

    local task; task="$(next_task)"
    printf '\n%s[第 %s 轮]%s 正在做：%s\n' "$C_BOLD" "$round" "$C_OFF" "$task"

    # 1) 做
    claude_run "$CMD_DIR/build.md" \
      "$DOC_DIR/02-共性与独特.md" "$DOC_DIR/03-什么算好.md" \
      "$DOC_DIR/04-要做什么.md" "$DOC_DIR/06-技术与落地.md" "$TASKS_FILE" || {
        local rc=$?; [ "$rc" -eq 3 ] && return 3; die "做的过程中出错了（退出码 $rc）"; }

    # 2) 检查 + 修
    local try=0 passed=0
    while [ "$try" -le "$MAX_FIX_TRIES" ]; do
      local out; out="$STATE_DIR/last-check.txt"
      if bash "$ROOT/scripts/check.sh" > "$out" 2>&1; then
        ok "检查通过"
        passed=1
        break
      fi
      try=$((try+1))
      if [ "$try" -gt "$MAX_FIX_TRIES" ]; then break; fi
      warn "检查没过，自动修第 $try 次…"
      # 把失败输出塞进提示词里
      {
        cat "$CMD_DIR/fix.md"
        printf '\n\n---- 检查失败的原始输出 ----\n'
        tail -c 8000 "$out"
      } > "$STATE_DIR/fix-prompt.md"
      claude_run "$STATE_DIR/fix-prompt.md" "$TASKS_FILE" || {
        local rc=$?; [ "$rc" -eq 3 ] && return 3; die "修的过程中出错了（退出码 $rc）"; }
    done

    if [ "$passed" -ne 1 ]; then
      rule
      warn "这个任务连修 $MAX_FIX_TRIES 次都没过，卡住了，需要你看一眼。"
      say  "卡住的任务：$task"
      say  "失败详情：$STATE_DIR/last-check.txt"
      say  ""
      say  "两个选择："
      say  "  1. 直接跑 ${C_BOLD}./loop.sh explain${C_OFF}，让它用大白话讲清楚卡在哪、你要做什么决定"
      say  "  2. 觉得这个任务不重要，去 docs/07-任务清单.md 里把它划掉，再 ./loop.sh go"
      return 1
    fi

    # 3) 确认它真把任务勾掉了，没勾就是没进展，避免死循环
    local still; still="$(tasks_open)"
    if [ "$still" -ge "$open" ]; then
      warn "检查过了但任务清单没变化，可能它忘了勾。手动去 docs/07-任务清单.md 勾掉「$task」再继续。"
      return 1
    fi

    ok "完成（剩 $still 个任务）"
  done
}

# ============================================================
# 子命令
# ============================================================

cmd_start() {
  local goal="${1:-}"
  [ -n "$goal" ] || die '用法：./loop.sh start "你想做的事，一句话就行"'

  mkdir -p "$STATE_DIR" "$LOG_DIR" "$DOC_DIR"
  printf '%s\n' "$goal" > "$STATE_DIR/原始想法.txt"

  # 学习笔记要先建出来，第9步才有地方往里追加
  if [ ! -f "$DOC_DIR/学习笔记.md" ]; then
    cat > "$DOC_DIR/学习笔记.md" <<'EOF'
# 学习笔记

做的过程中遇到的技术名词，都会顺手记在这里。
不用专门学，攒着就行——等这个项目做完，你大概就懂个七七八八了。

EOF
  fi

  state_set stage goal
  ok "记下了：$goal"
  cmd_go
}

cmd_go() {
  local stage; stage="$(state_get stage goal)"

  if [ "$stage" = "done" ]; then
    title "已经全部做完了 🎉"
    say "想加新功能就跑：./loop.sh start \"新的想法\"（会另起一轮）"
    return 0
  fi

  # 需要你点头的阶段：如果这一步已经跑过、且还没确认过，那这次 go 就是你的"确认"，往下走。
  # 注意用 ran_ 标记而不是"文档在不在"来判断——上一轮遗留的旧文档会让整步被误跳过。
  if stage_needs_signoff "$stage" \
     && [ "$(state_get "ran_$stage" no)" = "yes" ] \
     && [ "$(state_get "signoff_$stage" no)" = "no" ]; then
    state_set "signoff_$stage" yes
    ok "已确认「$(stage_label "$stage")」"
    state_set stage "$(next_stage "$stage")"
    cmd_go
    return
  fi

  if [ "$stage" = "build" ]; then
    local rc=0
    run_build_loop || rc=$?
    [ "$rc" -eq 0 ] || return "$rc"
    state_set stage done
    title "全部做完了 🎉"
    say "接下来可以跑 ./loop.sh explain 让它讲一遍你现在拥有的是个什么东西、怎么用。"
    return 0
  fi

  local rc=0
  run_stage "$stage" || rc=$?
  [ "$rc" -eq 3 ] && return 0     # 没装 claude，已经提示手动执行了

  if stage_needs_signoff "$stage"; then
    signoff_gate "$stage"
    return 0
  fi

  state_set stage "$(next_stage "$stage")"
  cmd_go   # 不需要点头的，直接连着往下跑
}

cmd_status() {
  local stage; stage="$(state_get stage goal)"
  title "现在的进度"
  say "原始想法：$(cat "$STATE_DIR/原始想法.txt" 2>/dev/null || echo '（还没开始）')"
  say ""
  local s mark
  for s in "${STAGES[@]}"; do
    [ "$s" = "done" ] && continue
    local si ci; si="$(stage_index "$s")"; ci="$(stage_index "$stage")"
    if [ "$stage" = "done" ] || [ "$si" -lt "$ci" ]; then mark="${C_GREEN}✓${C_OFF}"
    elif [ "$si" -eq "$ci" ]; then mark="${C_YELLOW}▶${C_OFF}"
    else mark="${C_DIM}·${C_OFF}"; fi
    printf '  %s %s\n' "$mark" "$(stage_label "$s")"
  done
  if [ -f "$TASKS_FILE" ]; then
    say ""
    say "任务：$(tasks_done)/$(tasks_total) 已完成"
  fi
  say ""
  say "${C_DIM}继续：./loop.sh go${C_OFF}"
}

cmd_explain() {
  [ -f "$CMD_DIR/explain.md" ] || die "缺少 .claude/commands/explain.md"
  local ctx=() s d
  for s in "${STAGES[@]}"; do
    d="$(stage_doc "$s")"
    [ -n "$d" ] && [ -f "$d" ] && ctx+=("$d")
  done
  [ -f "$STATE_DIR/last-check.txt" ] && ctx+=("$STATE_DIR/last-check.txt")
  claude_run "$CMD_DIR/explain.md" "${ctx[@]+"${ctx[@]}"}" || true
}

cmd_back() {
  local stage; stage="$(state_get stage goal)"
  local i; i="$(stage_index "$stage")"
  [ "$i" -le 0 ] && die "已经在第一步了，退不回去。"
  local prev="${STAGES[$((i-1))]}"
  state_set stage "$prev"
  state_set "signoff_$prev" no
  state_set "ran_$prev" no      # 清掉"跑过"标记，否则 go 会直接确认跳过，等于没退
  ok "退回：$(stage_label "$prev")"
  say "跑 ./loop.sh go 重做这一步。"
  say "${C_DIM}（旧的那份文档还在，它会在原来的基础上重做——想彻底重来就先把那个文件删了）${C_OFF}"
}

cmd_reset() {
  if [ -d "$STATE_DIR" ] || [ -d "$DOC_DIR" ]; then
    local bak="$ROOT/.loop-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$bak"
    # 用 mv 不用 cp：docs 必须真的挪走。
    # 留在原地的旧文档会让后面的步骤以为"这步已经做过了"，直接跳过——等于没重置。
    [ -d "$STATE_DIR" ] && mv "$STATE_DIR" "$bak/" 2>/dev/null || true
    [ -d "$DOC_DIR" ]   && mv "$DOC_DIR"   "$bak/" 2>/dev/null || true
    ok "旧的东西都挪到了 $bak（没删，随时能翻出来）"
  fi
  rm -rf "$STATE_DIR"
  ok "已重置。跑 ./loop.sh start \"你的想法\" 重新开始。"
}

cmd_help() {
  cat <<'EOF'
自动化流水线 —— 从一个模糊想法，到一个能用的东西

  ./loop.sh start "你想做什么"   开始（一句话说清就行，不用想得多完整）
  ./loop.sh go                   继续往下跑
  ./loop.sh status               看进度
  ./loop.sh explain              用大白话讲一遍现在什么情况
  ./loop.sh back                 上一步做得不满意，退回去重做
  ./loop.sh reset                全部清空重来（先自动备份）

九步流程：
  1 目标   把一句话想法变成能落地的目标
  2 巨人   把前人做到最好的全扒出来、找现成轮子、挖信息差
  3 独特   共性守什么、独特赌什么      ← 你拍板
  4 标准   定义什么叫「做得好」        ← 你拍板
  5 需求   拆成具体要做的东西          ← 你拍板
  6 补课   找出你不知道的事并讲明白
  7 选型   在哪落地、用什么、多少钱    ← 你拍板
  8 计划   排成可勾选的任务清单
  9 开做   做→检查→修，自动循环到全部通过

只有标着「你拍板」的四步会停下来等你，其余全自动。
这四步都是生意问题，不是技术问题——只有你能定。

可调开关（环境变量）：
  MAX_BUILD_ROUNDS=30   第9步最多循环几轮
  MAX_FIX_TRIES=3       一个任务最多自动修几次
  CLAUDE_BIN=claude     claude 命令的路径
EOF
}

# ============================================================
main() {
  local sub="${1:-help}"; shift || true
  case "$sub" in
    start)   cmd_start "${1:-}" ;;
    go|next|continue) cmd_go ;;
    status|st) cmd_status ;;
    explain|讲讲) cmd_explain ;;
    back)    cmd_back ;;
    reset)   cmd_reset ;;
    help|-h|--help) cmd_help ;;
    *) die "不认识的命令：$sub（跑 ./loop.sh help 看用法）" ;;
  esac
}
main "$@"
