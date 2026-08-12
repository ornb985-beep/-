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

# claude 跑挂了之后，统一在这儿决定「怎么跟人说」。
#
# 关键是分清两种失败：外面的原因（额度用完、断网）重跑没用，等就行；
# 真做错了才需要看日志改东西。混为一谈的后果是对着上限空转——真发生过。
# 返回 2 表示外部原因卡住（可以等），真失败直接 die。
report_failure() {
  local rc="$1" what="$2"
  local b; b="$(blocker_reason "$LAST_LOG" || true)"
  if [ -n "$b" ]; then
    rule
    case "${b%%$'\t'*}" in
      quota)   warn "不是代码坏了，是 AI 的额度用完了。" ;;
      network) warn "不是代码坏了，是连不上网。" ;;
    esac
    say "  它自己的原话：${C_DIM}${b#*$'\t'}${C_OFF}"
    say ""
    say "${C_BOLD}现在重跑没有用${C_OFF}，会得到一模一样的结果。等恢复了再跑 ${C_BOLD}./loop.sh go${C_OFF}——"
    say "前面做完的几步不会重做，直接从卡住的这一步接着跑。"
    rule
    return 2
  fi
  die "${what}（退出码 $rc）。日志在 .loop/log/ 里，可以直接把日志贴给我看。"
}

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
    report_failure "$rc" "这一步没跑成功"
    return $?
  fi

  # 「跑过」不等于「跑成了」。
  # claude 可能正常退出（退出码 0），但因为查不了资料、权限不够等原因
  # 根本没产出该产出的东西。这时候如果照样标记成功、照样往下走，
  # 后面每一步都会建立在空气上——而且每步看着都是 ✓。
  # 所以：该产出的文件不在，就是没做成，停下。
  local doc; doc="$(stage_doc "$stage")"
  if [ -n "$doc" ] && [ ! -f "$doc" ]; then
    rule
    warn "这一步没有产出 $(basename "$doc")，按「没做成」处理，不往下走。"
    say ""
    if [ -f "$DOC_DIR/05-我不懂的.md" ]; then
      say "它把卡在哪写下来了，先看这个：${C_BOLD}docs/05-我不懂的.md${C_OFF}"
      say "里面通常有一道选择题，你选完再跑 ./loop.sh go 继续。"
    else
      say "日志在 .loop/log/ 里，最新那个就是。可以直接把它贴给我看。"
    fi
    rule
    return 1
  fi

  state_set "ran_$stage" yes    # 到这儿才算真的跑成了
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
  # 把文档里的「怎么验收这一步」直接打出来，省得你还要翻文件找
  local checklist; checklist="$(extract_checklist "$doc")"
  if [ -n "$checklist" ]; then
    say ""
    printf '%s五分钟验收单%s（照着过一遍就行，不用懂技术）\n' "$C_BOLD" "$C_OFF"
    printf '%s\n' "$checklist"
  fi

  say ""
  say "${C_DIM}提示：你直接在文件里改字、划掉、补充就行。你改过的地方，后面每一步都会当成最高优先级。${C_OFF}"
  say ""
  say "接下来你可以："
  say "  ${C_BOLD}./loop.sh go${C_OFF}      看完没问题，继续往下"
  say "  ${C_BOLD}./loop.sh judge${C_OFF}   不知道好不好？让它逼问自己一遍，给你选择题"
  say "  ${C_BOLD}./loop.sh back${C_OFF}    这一步方向就不对，退回重做"
  rule
}

# 从文档里抠出「## 怎么验收这一步」那一段
extract_checklist() {
  local f="$1"
  [ -f "$f" ] || return 0
  awk '
    /^##[[:space:]]*怎么验收这一步/ { on=1; next }
    on && /^##[[:space:]]/ { on=0 }
    on && !/^```/ { print }
  ' "$f" | sed '/^[[:space:]]*$/d'
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
    local open done_before rev_before
    open="$(tasks_open)"; done_before="$(tasks_done)"; rev_before="$(revisions_count)"
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

    # 轮到只有你能干的任务，就停下来交给你，别派 AI 去替你猜。
    # 白跑一次不只是浪费额度，更糟的是它问出来的问题会掉进日志里没人看见。
    if task_is_human_gated "$task"; then
      rule
      title "轮到你了 —— 这条 AI 干不了，只有你能干"
      say ""
      next_task_block
      say ""
      rule
      say "干完之后，去 ${C_BOLD}docs/07-任务清单.md${C_OFF} 把这条前面的 ${C_BOLD}[ ]${C_OFF} 改成 ${C_BOLD}[x]${C_OFF}，"
      say "再跑 ${C_BOLD}./loop.sh go${C_OFF}，它会自己接着往下做。"
      say ""
      local gated; gated="$(tasks_human_gated)"
      say "${C_DIM}还剩 $open 个任务，其中 $gated 个是这样需要你本人的，其余 $((open-gated)) 个它自己能做。${C_OFF}"
      rule
      return 2   # 2 = 在等你，不是出错了
    fi

    printf '\n%s[第 %s 轮]%s 正在做：%s\n' "$C_BOLD" "$round" "$C_OFF" "$task"

    # 1) 做
    claude_run "$CMD_DIR/build.md" \
      "$DOC_DIR/02-共性与独特.md" "$DOC_DIR/03-什么算好.md" \
      "$DOC_DIR/04-要做什么.md" "$DOC_DIR/06-技术与落地.md" "$TASKS_FILE" || {
        local rc=$?; [ "$rc" -eq 3 ] && return 3
        report_failure "$rc" "做的过程中出错了"; return $?; }

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
        local rc=$?; [ "$rc" -eq 3 ] && return 3
        report_failure "$rc" "修的过程中出错了"; return $?; }
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
    #
    # 看的是「勾掉的有没有变多」，不是「剩下的有没有变少」。
    # 因为做任务时发现新问题、往清单里补一条，是好事，不是没进展；
    # 按剩余数判断的话，勾掉 1 条 + 新增 1 条 = 剩余不变 = 被误判成卡住。
    # 第一次真跑第9步就撞上了：它写完函数、勾了任务、还老实记下
    # "check.sh 探测不到 src/ 里的代码"这个新发现，结果被报成"没变化"。
    local done_after; done_after="$(tasks_done)"
    if [ "$done_after" -le "$done_before" ]; then
      warn "检查过了但任务清单没变化。"
      say  "卡住的任务：$task"
      say  ""
      say  "两种可能，先看一眼最新日志（.loop/log/ 里最新那个）再定："
      say  "  1. 它确实做完了只是忘了勾 → 手动在 docs/07-任务清单.md 里勾掉，再 ./loop.sh go"
      say  "  2. 这条其实得你本人来（它在日志里问了你问题） → 你答完再勾"
      say  "     顺手在这条任务前面加上「【需要你回答】」，以后就会直接停下来问你，不会白跑一趟"
      return 1
    fi

    # 4) 双回路转了没有。
    #
    # 见了实物就必须回头问一句「有没有哪条标准要改」——这是这套东西
    # 跟同类工具唯一的区别，也是「像人一样复盘迭代」这句话的落地。
    # 只更新东西、不更新标准的系统，会非常高效地跑向一个错的地方，
    # 而且每一步验收都通过。所以这一条和「任务有没有勾掉」一样是硬检查。
    if [ -f "$STANDARDS_FILE" ]; then
      local rev_after; rev_after="$(revisions_count)"
      if [ "$rev_after" -le "$rev_before" ]; then
        rule
        warn "这一轮没有回头看标准，不算跑完整。"
        say  "做完一个任务、见到真东西之后，必须回答一句：${C_BOLD}有没有哪条标准要改？${C_OFF}"
        say  ""
        say  "去 ${C_BOLD}docs/03-什么算好.md${C_OFF} 末尾的「标准修订记录」补一行——"
        say  "  改了 → 记：原来那条是什么、改成什么、为什么"
        say  "  没改 → 也记一行「看过，没改」，${C_DIM}空着才是问题${C_OFF}"
        say  ""
        say  "补完再跑 ${C_BOLD}./loop.sh go${C_OFF} 继续。"
        rule
        return 1
      fi
    fi

    local still; still="$(tasks_open)"
    if [ "$still" -gt "$open" ]; then
      ok "完成（剩 $still 个任务——比刚才多了，因为它顺手记下了新发现的问题）"
    else
      ok "完成（剩 $still 个任务）"
    fi
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
  # 反过来也要防一手：状态说"跑过了"、该产出的文件却不在。
  # 这种对不上的状态是旧版本留下的（那时候只要跑完就标成功，不看有没有产出）。
  # 不拦的话，这次 go 会被当成你"确认了这一步"，等于让你确认一份不存在的文件，
  # 后面每一步都建立在空气上。发现对不上就把标记清掉，重跑这一步。
  if stage_needs_signoff "$stage" && [ "$(state_get "ran_$stage" no)" = "yes" ]; then
    local sdoc; sdoc="$(stage_doc "$stage")"
    if [ -n "$sdoc" ] && [ ! -f "$sdoc" ]; then
      warn "状态里记着这一步跑过了，但 $(basename "$sdoc") 不在。"
      say  "这是旧版本留下的错状态（那时候跑完就算成功，不看有没有产出）。"
      say  "按「没跑过」处理，重跑这一步。"
      rule
      state_set "ran_$stage" no
    fi
  fi

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
  # 这一步没做成（比如查不了资料、没产出该产出的文件）就停在这儿。
  # 不停的话，后面每一步都建立在空气上，而且每步看着都是 ✓。
  [ "$rc" -ne 0 ] && return "$rc"

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

# 帮我判断：拿当前这一步的产出，逼问一遍，给出选择题
cmd_judge() {
  [ -f "$CMD_DIR/judge.md" ] || die "缺少 .claude/commands/judge.md"
  local stage; stage="$(state_get stage goal)"
  local ctx=() s d
  for s in "${STAGES[@]}"; do
    d="$(stage_doc "$s")"
    [ -n "$d" ] && [ -f "$d" ] && ctx+=("$d")
  done
  [ -f "$ROOT/references/判断标准.md" ] && ctx+=("$ROOT/references/判断标准.md")
  title "帮你判断：$(stage_label "$stage")"
  rule
  claude_run "$CMD_DIR/judge.md" "${ctx[@]+"${ctx[@]}"}" || true
}

# 纠错：先归因错在哪一层，再决定怎么改
cmd_correct() {
  [ -f "$CMD_DIR/correct.md" ] || die "缺少 .claude/commands/correct.md"
  local ctx=() s d
  for s in "${STAGES[@]}"; do
    d="$(stage_doc "$s")"
    [ -n "$d" ] && [ -f "$d" ] && ctx+=("$d")
  done
  [ -f "$ROOT/references/判断标准.md" ] && ctx+=("$ROOT/references/判断标准.md")
  [ -f "$STATE_DIR/last-check.txt" ] && ctx+=("$STATE_DIR/last-check.txt")
  title "纠错：先搞清楚错在哪一层"
  say "${C_DIM}别急着改东西——改错层，越改越糟。${C_OFF}"
  rule
  claude_run "$CMD_DIR/correct.md" "${ctx[@]+"${ctx[@]}"}" || true
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

  ./loop.sh judge                它给了个东西，我不知道好不好 → 它逼问自己，给你选择题
  ./loop.sh correct              感觉哪儿不对 → 先查错在哪一层，再决定怎么改

  ./loop.sh back                 上一步方向就不对，退回去重做
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
    judge|判断) cmd_judge ;;
    correct|纠错) cmd_correct ;;
    back)    cmd_back ;;
    reset)   cmd_reset ;;
    help|-h|--help) cmd_help ;;
    *) die "不认识的命令：$sub（跑 ./loop.sh help 看用法）" ;;
  esac
}
main "$@"
