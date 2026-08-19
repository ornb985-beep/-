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

  # 重跑这一步时，把上一版也给它看。
  #
  # 「听懂」那一步天然要跑好几轮（引导式问答）：第2轮必须看得见
  # 第1轮问了什么、你答了什么，否则每轮都从头把同样的问题再问一遍。
  # 对别的步也是对的——back 退回来重做时，看着旧版改比从零重写强。
  local own; own="$(stage_doc "$stage")"
  [ -n "$own" ] && [ -f "$own" ] && ctx+=("$own")

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

  # 开新想法之前先清场。
  # 不清的话：上一个项目的 ran_* 还在，新想法一进来第2、3步就是"已完成"，
  # 而且它们的文档会被当上下文喂给 AI——屏幕上全是 ✓，底下全是别人的材料。
  if had_run; then
    local prev; prev="$(head -c 40 "$STATE_DIR/原始想法.txt" 2>/dev/null || echo '上一个想法')"
    rule
    warn "这儿有上一次没做完的东西，先挪开再开新的。"
    say  "  上一个想法：${C_DIM}${prev}${C_OFF}"
    archive_run || true
    say  "  挪到了：${C_BOLD}$(basename "$ARCHIVED_TO")${C_OFF}　${C_DIM}一个文件都没删，随时能翻出来。${C_OFF}"
    rule
  fi

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

  state_set stage 听懂
  ok "记下了：$goal"
  say "${C_DIM}第一件事不是开工，是先把你这句话拆开、听懂。它可能要问你几个问题。${C_OFF}"
  cmd_go
}

cmd_go() {
  # 结项之后就不往下跑了。没有出口的止损线，人会一直答"还没到"。
  if [ "$(state_get closed no)" = "yes" ]; then
    warn "这个项目已经结项了，复盘在 docs/99-结项.md。"
    say  "真要重开：${C_BOLD}./loop.sh reset${C_OFF}（会先自动备份）"
    return 1
  fi

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

  # 第1步是引导式的，可能要问你好几轮。
  #
  # 它自己没在文档里写「状态：听懂了」之前，再敲一次 go 不算你点头——
  # 不拦的话，下面那段会把这次 go 当成确认，直接溜进第1步，
  # 而它其实还没听懂。后面八步就全建立在一个误解上了。
  #
  # 这时候 go 只把问题再显示一遍，【不重跑】：重跑要花钱，
  # 而且你没给新信息，再问一轮只会得到一模一样的问题。
  # 要往前走就答一句：./loop.sh 答 "..."
  if [ "$stage" = "听懂" ] \
     && [ "$(state_get ran_听懂 no)" = "yes" ] \
     && [ "$(listen_state)" != "听懂了" ]; then
    listen_gate
    return 2
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

  # 「听懂」是唯一一个可能要跑好几轮的阶段。
  # 它自己在文档里写「状态：听懂了 / 还没听懂」，我们照着它的话决定停不停。
  if [ "$stage" = "听懂" ] && [ "$(listen_state)" != "听懂了" ]; then
    listen_gate
    return 2
  fi

  if stage_needs_signoff "$stage"; then
    signoff_gate "$stage"
    return 0
  fi

  state_set stage "$(next_stage "$stage")"
  cmd_go   # 不需要点头的，直接连着往下跑
}

# 它还没听懂，要问你几个问题。把问题直接打出来，别让你去翻文件。
listen_gate() {
  local round; round="$(listen_round)"
  local maxr="$LISTEN_MAX_ROUNDS"

  rule
  if [ "$round" -ge "$maxr" ]; then
    title "问了 $round 轮，还是没聊拢"
    say "${C_DIM}这通常不是问题问得不对，是这个想法本身还没成形。它在文件末尾给了你三条路。${C_OFF}"
    say ""
    printf '%s\n' "$(listen_questions)"
    rule
    return 0
  fi

  # 一次只给一个。剩下的等这个答完再说。
  local total done_n idx
  total="$(listen_q_count)"; done_n="$(listen_answered)"; idx=$((done_n + 1))

  if [ "$total" -eq 0 ]; then
    title "它还没听懂，但也没问出问题来"
    say "${C_DIM}看看它写了什么：${LISTEN_FILE#"$ROOT/"}${C_OFF}"
    say "想推它一把：${C_BOLD}./loop.sh 答 \"你想补充的话\"${C_OFF}"
    rule
    return 0
  fi

  title "有一件事它不许替你猜"
  [ "$total" -gt 1 ] && say "${C_DIM}第 $idx 个，共 $total 个。答完这个再给下一个——一次只想一件事就行。${C_OFF}"
  say ""
  printf '%s\n' "$(listen_q_nth "$idx")"
  rule
  say "怎么答：${C_BOLD}./loop.sh 答 \"A\"${C_OFF}　${C_DIM}或者写句话，怎么顺手怎么来${C_OFF}"
  say ""
  say "${C_DIM}答不上来就直说「这个我答不上来」——那本身就是有用的信息，不是不合格的回答。${C_OFF}"
  rule
}

# 回答第1步的问题，然后自动跑下一轮
cmd_answer() {
  local text="${1:-}"
  [ -n "$text" ] || die '用法：./loop.sh 答 "1A 2C 3 我其实更在意的是…"'
  [ -f "$LISTEN_FILE" ] || die "还没有要回答的东西。先跑 ./loop.sh start \"你的想法\""

  local round total done_n idx
  round="$(listen_round)"; total="$(listen_q_count)"
  done_n="$(listen_answered)"; idx=$((done_n + 1))

  # 把回答记在它对应的那个问题下面，不然回头看不出你答的是哪一题
  {
    if [ "$total" -gt 0 ] && [ "$idx" -le "$total" ]; then
      printf '\n## 你的回答 · 第 %s 轮 · 问题 %s\n\n' "$round" "$idx"
    else
      printf '\n## 你的回答（第 %s 轮）\n\n' "$round"
    fi
    printf '%s\n' "$text"
  } >> "$LISTEN_FILE"
  listen_answered_set "$idx"
  ok "记下了。"

  # 同一轮里还有没答的，就在本地接着问下一个——【不重跑 AI】。
  #
  # 为什么：三个问题重跑三次，就是花三次钱换同一件事。
  # 问题都是这一轮一起生成的，答完再一起送回去，让它重新听一遍就够了。
  if [ "$total" -gt 0 ] && [ "$idx" -lt "$total" ]; then
    rule
    title "记下了。下一个 —— 第 $((idx+1)) 个，共 $total 个"
    say ""
    printf '%s\n' "$(listen_q_nth "$((idx+1))")"
    rule
    say "怎么答：${C_BOLD}./loop.sh 答 \"A\"${C_OFF}"
    rule
    return 0
  fi

  say "${C_DIM}都答完了，让它再听一遍。${C_OFF}"
  rule
  state_set ran_听懂 no      # 这一轮要重跑，清掉「跑过了」的标记
  cmd_go
}

# 单独用：不开项目，只把一段话拆一遍，结果打在屏幕上。
#
# 为什么要有这个：用户要的是一个「基础的分析语言智能体」，
# 那它就该能脱离主流程单独调用——不是只能在开项目的时候用一次。
cmd_listen_once() {
  local text="${1:-}"
  [ -n "$text" ] || die '用法：./loop.sh 听 "你想说的一段话"'
  have_claude || die "这台机器上没装 claude，跑不了。"

  local tmp="$STATE_DIR/听一次.md"
  mkdir -p "$STATE_DIR"
  {
    cat "$CMD_DIR/听懂.md"
    printf '\n\n---- 这次要听的话（不写文件，直接把结果说给我听）----\n'
    printf '%s\n' "$text"
    printf '\n注意：这次【不要】写任何文件，直接把上面那个结构打出来给我看。\n'
  } > "$tmp"

  title "拆一段话"
  rule
  claude_run "$tmp"
}

# ---------- 面板：一个能点的界面，跑在你自己电脑上 ----------
#
# 为什么是"本地网页"而不是真桌面软件：桌面软件要给 Mac/Windows 各打包、要签名。
# 本地网页零安装、零依赖（python3 自带的库就够）、断网能用。
#
# 它不是新做了一套东西——【所有活还是 loop.sh 干的】。
# 这层只做两件事：把状态显示出来、把你点的按钮翻译成一条 loop.sh 命令。
# 面板挂了，命令行照样能用；这是故意的。
cmd_panel() {
  command -v python3 >/dev/null 2>&1 || die "没有 python3，面板跑不了。命令行照常能用。"
  [ -f "$ROOT/scripts/面板.py" ] || die "找不到 scripts/面板.py"

  title "面板"
  rule
  say "把下面这个地址在浏览器里打开（地址里带着一次性令牌，别人拿不到）："
  say ""
  # 面板自己会把地址打在第一行
  exec python3 "$ROOT/scripts/面板.py"
}

# ---------- 试金石:两个脑子跑同一段话,分歧数出来,全票要报警 ----------
#
# 为什么有这条命令:2026-08-18 真机实证——只跑一个模型,一路绿灯;
# 两个模型一对,才抓到一个没打标记的猜测在撑判级。
# 而且那轮里两个模型唯一全票一致判轻的那句,恰好就是判错的那句。
# 所以:分歧是信息,全票是警报。「全票通过应该触发警报,不是让人放心。」
#
# 四条硬规矩(1-3 于 2026-08-18 定死,4 于 08-19 补,不许扩):
#   1. 每一跑【实际用了哪个模型】从调用日志验,不读配置——配置写的不等于真用的
#   2. 分歧为 0 时显示明显警告,不许显示绿色的通过
#   3. 调用前预算闸门硬查,不许跑一半才发现没钱
#   4. 先量噪声底(同一个模型跑两次),换脑子的分歧不超过它自己抖动时,
#      这一跑不许当「换脑子有用」的证据。所以是【三条腿,三次调用】——
#      比原来贵五成,买的是「那个数到底算不算数」
cmd_touchstone() {
  local text="${1:-}"
  [ -n "$text" ] || die '用法:./loop.sh 试金石 "一段话"　(两个模型各拆一遍,分歧数出来)'
  have_claude || die "这台机器上没装 claude,跑不了。"
  command -v python3 >/dev/null 2>&1 || die "没有 python3,分歧数不了(要跑 scripts/对分歧.py)。"

  # 预算闸门前置:这条命令要连打两次,没闸不让起跑,到顶不起跑
  [ -n "$(budget_get)" ] || die "先设上限:./loop.sh budget <数>。两个模型各跑一次,没闸不让跑。"
  budget_ok || return 1

  local kf="$PROVIDER_DIR/deepseek.key"
  [ -f "$kf" ] || die "没有 DeepSeek 的钥匙($kf)。先配一次接口把钥匙存进去。"

  # 提示词和「听」同一份:听懂.md + 这段话,不写文件
  local tmp="$STATE_DIR/听一次.md"
  mkdir -p "$STATE_DIR"
  {
    cat "$CMD_DIR/听懂.md"
    printf '\n\n---- 这次要听的话(不写文件,直接把结果说给我听)----\n'
    printf '%s\n' "$text"
    printf '\n注意:这次【不要】写任何文件,直接把上面那个结构打出来给我看。\n'
  } > "$tmp"

  local dir="$STATE_DIR/试金石"; mkdir -p "$dir"
  local ts; ts="$(date +%Y%m%d-%H%M%S)"
  local url; url="$(provider_field deepseek 3)"

  # 三条腿,不是两条。第三条(pro 再跑一次)是【噪声底】——
  # 同一个模型、同一段话、跑两次,它自己跟自己差多少。
  # 没有这个底,两个模型之间的分歧数说明不了任何事:那些差异
  # 可能压根不是「换脑子」带来的,只是同一个脑子自己在抖。
  # 出处:2026-08-18,flash 对「每天一百多款」上午判 ★★、下午判 ★★★——
  # 同一个模型、同一句话,自己改了自己的判级。
  local leg model out rc logf actual
  for leg in pro pro2 flash; do
    case "$leg" in
      pro|pro2) model="$(provider_field deepseek 4)" ;;
      flash)    model="$(provider_field deepseek-flash 4)" ;;
    esac
    case "$leg" in
      pro2) title "试金石 · $model（第二次，量它自己抖多少）" ;;
      *)    : ;;
    esac
    [ "$leg" != "pro2" ] && title "试金石 · $model"
    rule
    rc=0
    (
      # 子 shell:钥匙和模型只在这一跑里生效,不污染外面
      # shellcheck disable=SC1090
      . "$kf"
      export ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL="$url" \
             ANTHROPIC_MODEL="$model" \
             ANTHROPIC_DEFAULT_OPUS_MODEL="$model" \
             ANTHROPIC_DEFAULT_SONNET_MODEL="$model" \
             ANTHROPIC_DEFAULT_HAIKU_MODEL="$model"
      LOG_SUBDIR="试金石" claude_run "$tmp"
    ) || rc=$?
    [ "$rc" -eq 4 ] && { warn "到预算上限,停在「$model」这一跑之前。已跑完的日志还在 $dir/"; return 1; }
    [ "$rc" -ne 0 ] && { warn "「$model」这一跑没跑成(退出码 $rc),看日志:$(state_get last_log)"; return 1; }

    # 第 6 条:配置里写的不等于真的用了——从调用日志里验实际模型
    logf="$(state_get last_log)"
    actual="$(python3 -c "
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    ks=list((d.get('modelUsage') or {}).keys())
    print(ks[0] if ks else '')
except Exception:
    print('')
" "$logf.json")"
    if [ "$actual" != "$model" ]; then
      die "模型验证失败(第 6 条):要的是「$model」,调用日志里实际是「${actual:-读不到}」。这一轮作废,别拿它的产出当数。"
    fi
    ok "验明正身:这一跑真用的是 $actual(来自调用日志,不是配置)"
    cp "$logf" "$dir/$ts-$leg.log"
  done

  # 分歧交给对分歧.py 数,它的三个检查逻辑这儿一个不碰。
  # 数两遍:一遍量【它自己抖多少】(pro vs pro2),一遍量【换脑子差多少】(pro vs flash)。
  #
  # 为什么必须有第一遍:没有噪声底,第二遍那个数说明不了任何事。
  # 「两个模型差了 2 句」听起来像证据,可要是同一个模型自己跑两次也差 2 句,
  # 那这 2 句就跟换不换脑子毫无关系——你花的钱买到的是噪声,不是判断。
  #
  # 第 2 条:对分歧.py 的退出码(0 干净 / 1 有漏判 / 2 解析不了)必须接住,
  # 不许用 `|| true` 静音——那会让「比对崩了」长得跟「比对通过」一模一样。
  local drc=0 nrc=0 noise_out
  title "试金石 · 先量它自己抖多少（同一个模型跑两次）"
  rule
  noise_out="$(python3 "$ROOT/scripts/对分歧.py" "$dir/$ts-pro.log" "$dir/$ts-pro2.log")" || nrc=$?
  printf '%s\n' "$noise_out"
  if [ "$nrc" -ge 2 ]; then
    rule; warn "分歧没数成:噪声底那一遍就崩了(对分歧.py 退出码 $nrc)。这一跑【不算数】——量不出底,后面的数没有意义。"
    say "  三份原始产出留着:$dir/$ts-{pro,pro2,flash}.log"; rule; return 1
  fi

  title "试金石 · 再量换脑子差多少"
  rule
  out="$(python3 "$ROOT/scripts/对分歧.py" "$dir/$ts-pro.log" "$dir/$ts-flash.log")" || drc=$?
  printf '%s\n' "$out"
  if [ "$drc" -ge 2 ]; then
    rule
    warn "分歧没数成(对分歧.py 退出码 $drc:解析不了)。"
    say  "  这一跑【不算数】——没数出分歧,不等于没有分歧。"
    say  "  三份原始产出留着,自己看:$dir/$ts-{pro,pro2,flash}.log"
    rule
    return 1
  fi

  # 把两个「不同 N 对」抠出来比。抠不到就当没量到,不许蒙混过去。
  local noise sig
  noise="$(printf '%s' "$noise_out" | grep -oE '不同 [0-9]+ 对' | head -1 | grep -oE '[0-9]+' || true)"
  sig="$(  printf '%s' "$out"       | grep -oE '不同 [0-9]+ 对' | head -1 | grep -oE '[0-9]+' || true)"
  if [ -z "$noise" ] || [ -z "$sig" ]; then
    rule; warn "读不出「不同 N 对」这个数,判不了净信号。这一跑不算数。"; rule; return 1
  fi

  rule
  title "试金石 · 结论"
  say "  它自己跟自己差：${C_BOLD}$noise${C_OFF} 句　　换个脑子差：${C_BOLD}$sig${C_OFF} 句"
  say ""

  # 全票 = 警报,不是通过。判据:判级不同 0 对,且两边都没有独有句
  if printf '%s' "$out" | grep -q "不同 0 对" \
     && printf '%s' "$out" | grep -q "前一份独有 0 句,后一份独有 0 句"; then
    rule
    warn "⚠ 全票一致——这是警报,不是让人放心。"
    say  "  「全票通过应该触发警报,不是让人放心。」(工程交接包·核心一)"
    say  "  两个脑子毫无分歧,通常说明它们在顺着同一个先验说话。"
    say  "  实证:2026-08-18 那轮,两模型唯一全票一致判轻的那句,恰好就是判错的那句。"
    say  "  建议:换一个不同家的模型再跑一遍,或人工复核判级表。"
    rule
    return 1
  fi

  if [ "$sig" -le "$noise" ]; then
    warn "⚠ 换脑子差的（$sig）不比它自己抖的（$noise）多——这一跑【不许当成「换脑子有用」的证据】。"
    say  "  同一个模型自己跑两次就能差 $noise 句,那两个模型差 $sig 句什么也证明不了。"
    say  "  实证:2026-08-18,flash 对「每天一百多款」上午判 ★★、下午判 ★★★——"
    say  "  同一个模型、同一句话,自己改了自己的判级。"
    say  "  要么多跑几轮把底量稳,要么换一家真正不同的模型再试。"
    rule
    return 1
  fi

  say "${C_BOLD}净信号 $((sig - noise)) 句${C_OFF}：换脑子带来的分歧，超出了它自己抖动的部分。"
  say ""
  say "分歧就是信息:吵起来的地方是模型差异,别动规则;两边一起错的地方才轮到规则(验证的规矩第 7 条)。"
  say "三份原始产出:$dir/$ts-{pro,pro2,flash}.log"
  if [ "$drc" -eq 1 ]; then
    say ""
    warn "有句子被漏判(见上面的清单)。漏判是个真发现,所以这条命令退出码非 0。"
    return 1
  fi
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

# 执行总监干的两件事：把 CEO 的决策拆成活（派单）、定今天谁做什么（排班）。
#
# 为什么要中间这一层：CEO 定「做什么、为什么」，总监定「谁做、什么时候、什么算完」。
# 没有这一层，CEO 得亲自盯每个人每天干什么——那不叫操盘手，那叫工头。
_run_director() {
  local what="$1" cmd="$2" out="$3"
  [ -f "$CMD_DIR/$cmd.md" ] || die "缺少 .claude/commands/$cmd.md"
  if [ ! -f "$(role_file 执行总监)" ]; then
    warn "还没有执行总监这个角色。"
    say  "招他：${C_BOLD}./loop.sh hire 执行总监${C_OFF}"
    return 1
  fi

  title "$what"
  say "${C_DIM}在岗员工：$(roles_list | tr '\n' ' ')${C_OFF}"
  rule

  local ctx=()
  [ -f "$DOC_DIR/09-操盘记录.md" ] && ctx+=("$DOC_DIR/09-操盘记录.md")
  [ -f "$TASKS_FILE" ]            && ctx+=("$TASKS_FILE")
  [ -f "$DOC_DIR/11-派工单.md" ]  && ctx+=("$DOC_DIR/11-派工单.md")
  [ -f "$DOC_DIR/12-排班.md" ]    && ctx+=("$DOC_DIR/12-排班.md")

  # 在岗名单要喂进去，否则会派给不存在的人
  local roster="$STATE_DIR/在岗名单.md"
  { printf '# 现在在岗的人（只能派给这些人）\n\n'; roles_list | sed 's/^/- /'; } > "$roster"
  ctx+=("$roster")

  local rc=0
  ROLE_ISOLATED=1 ask_role 执行总监 "$(cat "$CMD_DIR/$cmd.md")" "${ctx[@]+"${ctx[@]}"}" || rc=$?
  [ "$rc" -eq 3 ] && return 0
  if [ "$rc" -ne 0 ]; then report_failure "$rc" "$what 的时候出错了"; return $?; fi

  group_say "执行总监" "$(tail -40 "$LAST_LOG" 2>/dev/null)"
  rule
  if [ -f "$DOC_DIR/$out" ]; then
    ok "写好了：${C_BOLD}docs/$out${C_OFF}"
  else
    warn "没产出 docs/$out，按没做成处理。"
    return 1
  fi
}

cmd_dispatch() { _run_director "派单 · 把 CEO 的决策拆成每个人的活" 派单 "11-派工单.md"; }
cmd_roster()   { _run_director "排班 · 今天每个人做什么" 排班 "12-排班.md"; }

# 看板：从真实状态生成一个本地 HTML，双击就开。
#
# 为什么是本地 HTML 不是网页服务：这套东西是你机器上的一个脚本，没有常驻服务。
# 生成一个自包含的 .html，零依赖、断网能用、不会挂。想刷新就再跑一次。
# 它只读状态、不写任何东西——看板坏了不影响 loop 跑。
cmd_board_html() {
  command -v python3 >/dev/null 2>&1 || {
    warn "看板要用 python3 生成，这台机器上没有。"
    say  "不影响跑 loop，只是没有可视化。装个 python3 就有了。"
    return 1
  }
  local out; out="$(python3 "$ROOT/scripts/看板.py" "$ROOT")" || {
    warn "看板没生成成功。"; return 1; }
  ok "看板好了：${C_BOLD}${out#"$ROOT/"}${C_OFF}"
  say "${C_DIM}双击打开就行。想刷新再跑一次 ./loop.sh 看板${C_OFF}"
  # 能自动打开就自动打开
  if   command -v open    >/dev/null 2>&1; then open "$out" 2>/dev/null || true
  elif command -v xdg-open>/dev/null 2>&1; then xdg-open "$out" 2>/dev/null || true
  elif command -v explorer.exe >/dev/null 2>&1; then explorer.exe "$(basename "$out")" 2>/dev/null || true
  fi
}

# CEO 设计专家团：先想清楚这个项目缺哪几块判断，再照缺口去找人。
#
# 为什么这一步必须有：行业专家擅长查，但他不知道这个项目缺什么。
# 不给方向，他会按惯性去找"这行最有名的人"——
# 而最有名的人 ≠ 对我们最有用的人。
# 实测教训：没有这一步，找回来的全是网红，有故事没体系，
# 成功还高度依赖那个年代的平台红利，拿到手根本没法用。
cmd_panel_design() {
  [ -f "$CMD_DIR/专家团.md" ] || die "缺少 .claude/commands/专家团.md"
  title "CEO 设计专家团"
  say "${C_DIM}先定缺哪几块判断，再照缺口点名要什么样的专家${C_OFF}"
  rule

  local ctx=()
  [ -f "$DOC_DIR/00-目标.md" ]      && ctx+=("$DOC_DIR/00-目标.md")
  [ -f "$DOC_DIR/02-共性与独特.md" ] && ctx+=("$DOC_DIR/02-共性与独特.md")
  [ -f "$DOC_DIR/05-我不懂的.md" ]   && ctx+=("$DOC_DIR/05-我不懂的.md")
  [ -f "$GROUP_CHAT" ]              && ctx+=("$GROUP_CHAT")

  local rc=0
  claude_run "$CMD_DIR/专家团.md" "${ctx[@]+"${ctx[@]}"}" || rc=$?
  [ "$rc" -eq 3 ] && return 0
  if [ "$rc" -ne 0 ]; then report_failure "$rc" "设计专家团的时候出错了"; return $?; fi

  rule
  if [ -f "$DOC_DIR/13-专家团设计.md" ]; then
    ok "写好了：${C_BOLD}docs/13-专家团设计.md${C_OFF}"
    group_say "CEO" "$(tail -25 "$LAST_LOG" 2>/dev/null)"
    say ""
    say "下一步：${C_BOLD}./loop.sh 行业报告 \"<议题>\"${C_OFF}（行业专家会照这份设计去找人）"
  else
    warn "没产出 docs/13-专家团设计.md，按没做成处理。"
    return 1
  fi
}

# 蒸馏：把行业报告里的真实专家，做成可以单独提问的智能体。
#
# 【这件事唯一可能翻车的地方】蒸馏 ≠ 把这个人复活。
# 「某某会说 XXX」是编的，而且借了真人的权威，比普通编造更糟。
# 蒸馏出来的角色必须写死：超出他公开说过的部分，
# 当场标明「这是从他的方法推的，他本人没这么说过」。
cmd_distill() {
  [ -f "$CMD_DIR/蒸馏.md" ] || die "缺少 .claude/commands/蒸馏.md"
  local rpt; rpt="$(ls -t "$(role_workspace 行业专家)"/*行业报告.md 2>/dev/null | head -1)"
  if [ -z "$rpt" ]; then
    warn "还没有行业报告，没东西可蒸馏。"
    say  "先跑：${C_BOLD}./loop.sh 行业报告 \"你的行业／议题\"${C_OFF}"
    return 1
  fi

  title "蒸馏专家"
  say "${C_DIM}原料：${rpt#"$ROOT/"}${C_OFF}"
  rule

  local before; before="$(roles_list | grep -c '^专家-' || true)"
  local rc=0
  claude_run "$CMD_DIR/蒸馏.md" "$rpt" || rc=$?
  [ "$rc" -eq 3 ] && return 0
  if [ "$rc" -ne 0 ]; then report_failure "$rc" "蒸馏的时候出错了"; return $?; fi

  local after; after="$(roles_list | grep -c '^专家-' || true)"
  rule
  if [ "$after" -gt "$before" ]; then
    ok "蒸馏出 $((after-before)) 位："
    roles_list | grep '^专家-' | sed 's/^/    /'
    group_say "系统" "蒸馏了 $((after-before)) 位行业专家，他们能看到这之后的群聊。"
    say ""
    say "单独问：${C_BOLD}./loop.sh ask 专家-<名字> \"问题\"${C_OFF}"
    say "一起议：${C_BOLD}./loop.sh 专家群 \"议题\"${C_OFF}"
    say "用完封存：${C_BOLD}./loop.sh 封存 专家-<名字>${C_OFF}"
  else
    warn "没有新增任何专家角色，按没蒸馏成处理。"
    return 1
  fi
}

# 专家群：让蒸馏出来的专家依次就同一个议题发言，后面的看得见前面的。
#
# 为什么是依次不是同时：依次的好处是后面的人能反驳前面的，
# 那才叫讨论；同时问只是拿到几份互不相干的独白。
cmd_expert_panel() {
  local topic="${1:-}"
  [ -n "$topic" ] || die "用法：./loop.sh 专家群 \"要议什么\""
  local experts; experts="$(roles_list | grep '^专家-' || true)"
  if [ -z "$experts" ]; then
    warn "还没有蒸馏出任何专家。"
    say  "先跑：${C_BOLD}./loop.sh 行业报告 \"…\"${C_OFF} 然后 ${C_BOLD}./loop.sh 蒸馏${C_OFF}"
    return 1
  fi

  title "专家群讨论：$topic"
  say "${C_DIM}在场：$(printf '%s' "$experts" | tr '\n' ' ')${C_OFF}"
  rule
  group_say "CEO" "【专家群议题】$topic"

  local who n=0
  while IFS= read -r who; do
    [ -z "$who" ] && continue
    budget_ok || { warn "预算到顶，讨论中断。已经发言的都在群聊里。"; break; }
    n=$((n+1))
    rule
    info "第 $n 位 · $who"

    local q="【专家群讨论】$topic

**先看群聊里前面几位说了什么。** 你是第 $n 位发言的。

必须包含：
1. **他明确说过的**（带出处）
2. **从他的方法推的**（他本人没说过，标清楚）
3. **条件对不对得上**：我们现在的处境跟他当年差在哪，这条建议[能直接用／要打折／用不了]
4. **他最可能看走眼的地方**
5. **如果你不同意前面某位的说法，直接点名说哪位、哪一条、为什么**
   —— 这一条最重要。**都点头的讨论等于没讨论。**"

    local ctx=(); local d
    while IFS= read -r d; do [ -n "$d" ] && ctx+=("$d"); done < <(role_context "$who")
    local rc=0
    ROLE_ISOLATED=1 ask_role "$who" "$q" "${ctx[@]+"${ctx[@]}"}" || rc=$?
    if [ "$rc" -eq 0 ]; then
      group_say "$who" "$(tail -35 "$LAST_LOG" 2>/dev/null)"
    else
      warn "$who 这一轮没答成，跳过。"
    fi
  done <<< "$experts"

  [ "$n" -eq 0 ] && { warn "一位都没发言成。"; return 1; }
  rule
  ok "$n 位发言完毕，全在 ${C_BOLD}docs/10-群聊.md${C_OFF}"
  say "让 CEO 裁决：${C_BOLD}./loop.sh ceo${C_OFF}"
}

# 封存：这个角色用完了，收起来。不删——收进 .loop/封存/，随时能起复。
cmd_archive_role() {
  local who="${1:-}"
  if [ -z "$who" ]; then
    title "封存过的角色"
    if [ -d "$STATE_DIR/封存" ]; then
      find "$STATE_DIR/封存" -maxdepth 1 -name '*.md' -exec basename {} .md \; 2>/dev/null | sed 's/^/  /'
    else
      say "  还没封存过谁"
    fi
    say ""
    say "封存：${C_BOLD}./loop.sh 封存 <名字>${C_OFF}　起复：${C_BOLD}./loop.sh 起复 <名字>${C_OFF}"
    return 0
  fi
  [ -f "$(role_file "$who")" ] || die "「$who」不在岗（看看有谁：./loop.sh roles）"
  mkdir -p "$STATE_DIR/封存"
  mv "$(role_file "$who")" "$STATE_DIR/封存/$who.md"
  [ -f "$(role_session "$who")" ] && mv "$(role_session "$who")" "$STATE_DIR/封存/$who.session"
  ok "封存了：$who"
  say "${C_DIM}没删。他说过的话还在群聊里，交付物还在 work/$who/，随时能起复。${C_OFF}"
  group_say "系统" "$who 已封存。"
}

cmd_unarchive_role() {
  local who="${1:-}"
  [ -n "$who" ] || die "用法：./loop.sh 起复 <名字>"
  [ -f "$STATE_DIR/封存/$who.md" ] || die "封存里没有「$who」"
  mkdir -p "$ROLE_DIR"
  mv "$STATE_DIR/封存/$who.md" "$(role_file "$who")"
  [ -f "$STATE_DIR/封存/$who.session" ] && mv "$STATE_DIR/封存/$who.session" "$(role_session "$who")"
  ok "起复了：$who"
  group_say "系统" "$who 起复归队。"
}

# 行业报告：让行业专家去找 10 个真实操盘手的判断，一人一份落盘，最后综合。
#
# 跟「会诊」的区别：会诊是问我们自己的参谋；这个是去外面找【真人的战绩和说法】。
# 关键是可追溯——一人一份单独写，带出处和时间，
# 这样老板能回头核对"这个人说的跟网上搜到的案例对不对得上"。
# 揉成一锅粥就没法核对了，那才是最危险的：读起来很专业，一句都验不了。
cmd_industry() {
  local topic="${1:-}"
  [ -n "$topic" ] || die "用法：./loop.sh 行业报告 \"哪个行业／什么议题\""
  if [ ! -f "$(role_file 行业专家)" ]; then
    warn "还没有行业专家这个角色。"
    say  "招他：${C_BOLD}./loop.sh hire 行业专家${C_OFF}"
    return 1
  fi

  local ws; ws="$(role_workspace 行业专家)"; mkdir -p "$ws"
  local stamp; stamp="$(date +%Y%m%d-%H%M%S)"
  local deliver="$ws/$stamp-行业报告.md"
  local id; id="$(task_add 行业专家 "行业报告：$topic" "${deliver#"$ROOT/"}")"

  title "行业报告（第 $id 号）：$topic"
  say "${C_DIM}目标 10 份实战判断，一人一份落盘带出处；找不够就明写找不够${C_OFF}"
  rule
  group_say "CEO → @行业专家" "【行业报告】$topic"$'\n\n'"交到：\`${deliver#"$ROOT/"}\`"

  # 【不喂项目文档】行业报告的议题经常跟当前项目无关——
  # 你可能正在为下一个方向做调研。喂项目文档的后果实测过：
  # 它读完一堆微信工具的文档，跑去汇报那个项目的进度，
  # 完全没做该做的行业报告。上下文不是越多越好，喂错了会把人带沟里。
  # CEO 的专家团设计如果有，就是你的作业单——照单去找，别自由发挥
  local ctx=()
  if [ -f "$DOC_DIR/13-专家团设计.md" ]; then
    cp "$DOC_DIR/13-专家团设计.md" "$ws/【作业单】专家团设计.md"
    ctx+=("$ws/【作业单】专家团设计.md")
    say "${C_DIM}照 CEO 的专家团设计去找（docs/13-专家团设计.md）${C_OFF}"
  fi
  local instruction; instruction="$(cat <<EOF
【这是一份行业报告的活。照你角色定义里的五步做，一步都不许省。】

## 如果附了【作业单】专家团设计
**那是 CEO 定的，照单去找，别自由发挥。**
里面写了这个项目缺哪几块判断、每一类要找什么样的人、明确不要什么。
**「明确不要」那一栏尤其要守住**——找回来一堆不要的，等于白花钱。

议题：$topic

## 先说清楚：这个议题跟当前项目可能没关系
你现在做的是【对这个议题所在行业】的调研，**不是汇报任何项目的进度**。
群聊里那些别的项目的事，跟这份报告无关，别提。

## 交付物
写到这个文件：$stamp-行业报告.md（就在你当前所在的目录，直接写文件名即可）
**必须是这个文件本身**——只在对话里说一遍不算交付。

## 一人一份，不许揉在一起
这份报告的全部价值在于【可追溯】：老板要能回头核对
"这个人说的，跟网上能搜到的案例对不对得上"。
**揉成一锅粥就没法核对了**——那才是最危险的：读起来很专业，一句都验不了。

## 最后必须自己说一句
「找到 __ 份够格的（目标 10），__ 份背景存疑，__ 份来自失败方。
　够不够支撑一次不可逆的决定：[够 ／ 不够，还缺 ____]」

**不够就说不够。** 一份只找到 3 个人、全是活着的报告，
不足以支撑花大钱的决定——你自己说出来，别让 CEO 事后发现。

干完在群里汇报三行：找到几份／最值得看的是谁为什么／哪一条你自己都觉得可疑。
EOF
)"

  local rc=0
  # NO_GROUP_CHAT=1：群聊里全是别的项目的事，会把它带跑偏（实测过）
  # 在行业专家自己的工作区里跑，不在项目根目录——
  # 项目根目录有 CLAUDE.md，会把它拽去做项目的活（实测两次都跑偏）
  NO_GROUP_CHAT=1 ROLE_ISOLATED=1 ROLE_CWD="$ws" \
    ask_role 行业专家 "$instruction" "${ctx[@]+"${ctx[@]}"}" || rc=$?
  [ "$rc" -eq 3 ] && return 0
  if [ "$rc" -ne 0 ]; then report_failure "$rc" "做行业报告的时候出错了"; return $?; fi

  group_say "行业专家" "$(tail -40 "$LAST_LOG" 2>/dev/null)"

  rule
  if [ -f "$deliver" ]; then
    task_set_state "$id" "干完了"
    local n; n="$(grep -c '^### 第' "$deliver" 2>/dev/null || echo 0)"
    ok "交了：${C_BOLD}${deliver#"$ROOT/"}${C_OFF}（$(wc -l < "$deliver") 行，$n 份单独落盘的专家判断）"
    say "让 CEO 看：${C_BOLD}./loop.sh 验收${C_OFF}　或直接裁决：${C_BOLD}./loop.sh ceo${C_OFF}"
  else
    task_set_state "$id" "没交东西"
    warn "他说完了，但 ${deliver#"$ROOT/"} 不在——按【没交】处理。"
    return 1
  fi
}

# 会诊：CEO 判断该问谁 → 逐个问 → CEO 综合裁决。
#
# 这是组织架构里「CEO 咨询专家再裁决」那一段。
# 关键是 CEO 自己点名，不是全问——全问十个人要十几次调用、几十美元，
# 而且大部分人对某个具体议题给不出增量意见。
# 挑人本身就是判断力的一部分，把它自动化掉等于把判断推给了流程。
cmd_council() {
  local topic="${1:-}"
  [ -n "$topic" ] || die "用法：./loop.sh 会诊 \"要议什么\""
  [ -f "$CMD_DIR/点名.md" ] || die "缺少 .claude/commands/点名.md"
  local onstaff; onstaff="$(roles_list | tr '\n' ' ')"
  [ -n "$onstaff" ] || { warn "还没招人。先 ./loop.sh hire 战略 财务 风控"; return 1; }

  title "会诊：$topic"
  say "${C_DIM}在岗：$onstaff${C_OFF}"
  rule
  group_say "你" "【会诊议题】$topic"

  # ── 第一步：CEO 点名 ────────────────────────────────
  info "第一步 · CEO 判断该问谁"
  local pick_prompt="$STATE_DIR/点名.md"
  { cat "$CMD_DIR/点名.md"
    printf '\n\n## 现在在岗的人\n%s\n\n## 要会诊的议题\n%s\n' "$onstaff" "$topic"
  } > "$pick_prompt"

  local rc=0
  claude_run "$pick_prompt" "$DOC_DIR/00-目标.md" || rc=$?
  [ "$rc" -eq 3 ] && return 0
  if [ "$rc" -ne 0 ]; then report_failure "$rc" "点名的时候出错了"; return $?; fi

  # || true：CEO 要是没照格式写「点名：」，grep 返回 1 + pipefail 会把脚本打死，
  # 下面那句 if [ -z "$picked" ] 根本执行不到——而那句本来就是为这种情况写的。
  local picked; picked="$(grep -oE '^点名[:：].*' "$LAST_LOG" | tail -1 | sed -E 's/^点名(:|：)[[:space:]]*//' || true)"
  if [ -z "$picked" ]; then
    rule
    warn "CEO 没点名（要么它觉得这事不用会诊，要么它没照格式写）。"
    say  "上面是它的说法。要硬会诊就直接 ./loop.sh ask <名字> \"$topic\""
    return 1
  fi

  rule
  ok "CEO 点了：${C_BOLD}$picked${C_OFF}"
  group_say "CEO" "这个议题我点这几个人：$picked"

  # ── 第二步：逐个问 ──────────────────────────────────
  local n=0 who
  for who in $picked; do
    if [ ! -f "$(role_file "$who")" ]; then
      warn "「$who」不在岗，跳过。（招他：./loop.sh hire $who）"
      continue
    fi
    budget_ok || { warn "预算到顶，会诊中断。已经问过的意见都在群聊里。"; break; }
    n=$((n+1))
    # 用位置参数数个数，不用 wc -w —— wc -w 数不了中文（实测返回 0），
    # 而这套东西的角色名全是中文。
    local total; total="$(set -- $picked; echo $#)"
    rule
    info "第二步 · 问「$who」（$n/$total）"

    local q="【会诊】$topic

这是一次会诊，不是闲聊。**先看群聊里别人已经说了什么**，
然后只说你这个位置上、别人给不出的那部分。

必须包含：
1. 结论先行（一句话）
2. 依据（能核对的，带来源和日期；查不到就写查不到）
3. 置信度：高／中／低
4. **反对你自己的最强论据**——这条不写，你的意见对 CEO 没有价值
5. 如果你不同意群里已有的某条判断，直接点名说哪条、为什么"

    local ctx=(); local d
    while IFS= read -r d; do [ -n "$d" ] && ctx+=("$d"); done < <(role_context "$who")
    group_say "CEO → @$who" "【会诊】$topic"
    rc=0
    ROLE_ISOLATED=1 ask_role "$who" "$q" "${ctx[@]+"${ctx[@]}"}" || rc=$?
    if [ "$rc" -eq 0 ]; then
      group_say "$who" "$(tail -40 "$LAST_LOG" 2>/dev/null)"
    else
      warn "「$who」这一轮没答成，跳过。"
    fi
  done

  [ "$n" -eq 0 ] && { warn "一个人都没问成，会诊没开起来。"; return 1; }

  # ── 第三步：CEO 裁决 ────────────────────────────────
  rule
  info "第三步 · CEO 综合裁决"
  budget_ok || { warn "预算到顶，没跑裁决。专家意见都在群聊里，可以之后跑 ./loop.sh ceo"; return 1; }
  cmd_ceo
}

# 派活给某个角色：他自己去搜、去做，交付一个文件，等 CEO 验收。
#
# 跟 ask 的区别：ask 是问一句答一句；派活是「他独立干完一件事并交东西」。
# 交付物必须是文件——**说了 ≠ 交了**，这是这套东西反复栽过的那个坑。
cmd_assign() {
  local role="${1:-}" task="${2:-}"
  [ -n "$role" ] || die "用法：./loop.sh 派活 <角色> \"要他干什么\""
  [ -f "$(role_file "$role")" ] || {
    warn "没有「$role」这个角色。现有的：$(roles_list | tr '\n' ' ')"
    say  "招人：./loop.sh hire"; exit 1; }
  [ -n "$task" ] || die "要他干什么？用法：./loop.sh 派活 $role \"任务\""

  local ws; ws="$(role_workspace "$role")"
  mkdir -p "$ws"
  local stamp; stamp="$(date +%Y%m%d-%H%M%S)"
  local deliver="$ws/$stamp-交付.md"

  local id; id="$(task_add "$role" "$task" "${deliver#"$ROOT/"}")"

  title "派活给「$role」（第 $id 号）"
  say "${C_DIM}$task${C_OFF}"
  say "${C_DIM}他的工作区：${ws#"$ROOT/"}/${C_OFF}"
  rule

  group_say "你 → @$role" "【派活 #$id】$task"$'\n\n'"交到：\`${deliver#"$ROOT/"}\`"

  local ctx=(); local d
  while IFS= read -r d; do [ -n "$d" ] && ctx+=("$d"); done < <(role_context "$role")

  local instruction; instruction="$(cat <<EOF
【这是一件派给你的活，不是问你一句话。你要自己去查、去做，最后交一个文件。】

任务：$task

## 你的工作区
$ws/
搜集的资料、草稿、中间产物，全部放这个目录里。这是**你自己的地盘**，别人不会动。

## 你的交付物
写到这个文件：$deliver

**交付物必须是这个文件本身**。只在对话里说一遍不算交付——
这套东西反复栽在同一个坑上：**说了 ≠ 交了，跑过 ≠ 跑成了**。

## 项目文档是只读的
\`docs/\` 下的文件是大家共同的事实基础，**你只能读，不许改**。
你觉得哪份文档写错了，写进交付物里说明理由，让 CEO 判断，别自己动手改。

## 交付物里必须有这几段
1. **结论先行**：一句话说清你做出了什么／得出了什么
2. **过程**：你查了什么、从哪查的（带链接和日期）
3. **不确定的地方**：哪些是查证的，哪些是推断的，哪些是猜的
4. **验收怎么验**：CEO 拿什么标准判断你这活干得行不行——你自己先说
5. **卡住的地方**：有就写，没有写"没卡住"

干完之后在群里说一句话汇报（三行以内：做完了什么／最要紧的一条发现／要 CEO 定什么）。
EOF
)"

  # 干活开全新会话：一件活 = 一个自包含任务包。
  # 十件活堆在同一个会话里会越干越贵，而且第一件活里的错误假设
  # 会一直粘着往后走。干活的持久化靠交付物，不靠"记住"。
  local rc=0
  ROLE_ISOLATED=1 ask_role "$role" "$instruction" "${ctx[@]+"${ctx[@]}"}" || rc=$?
  [ "$rc" -eq 3 ] && return 0
  if [ "$rc" -ne 0 ]; then report_failure "$rc" "「$role」干活的时候出错了"; return $?; fi

  group_say "$role" "$(tail -40 "$LAST_LOG" 2>/dev/null)"

  # 交付物在不在，决定这活算不算干完 —— 说了 ≠ 交了
  rule
  if [ -f "$deliver" ]; then
    task_set_state "$id" "干完了"
    ok "交了：${C_BOLD}${deliver#"$ROOT/"}${C_OFF}（$(wc -l < "$deliver") 行）"
    say "让 CEO 验收：${C_BOLD}./loop.sh 验收${C_OFF}"
  else
    task_set_state "$id" "没交东西"
    warn "他说完了，但 ${deliver#"$ROOT/"} 不在——按【没交】处理。"
    say  "看看他到底卡在哪：${LAST_LOG#"$ROOT/"}"
    say  "或者直接再派一次，把任务说得更具体。"
    return 1
  fi
}

# CEO 验收：把干完的活逐个看一遍，判行不行
cmd_review() {
  [ -f "$CMD_DIR/review.md" ] || die "缺少 .claude/commands/review.md"
  local pending; pending="$(tasks_pending_review)"
  if [ -z "$pending" ]; then
    title "没有等着验收的活"
    say "派活：${C_BOLD}./loop.sh 派活 <角色> \"任务\"${C_OFF}"
    say "看台账：${C_BOLD}./loop.sh 台账${C_OFF}"
    return 0
  fi

  title "CEO 验收"
  printf '%s\n' "$pending" | awk -F'\t' '{printf "  #%s  %-8s %s\n", $1, $2, substr($3,1,44)}'
  rule

  local ctx=() f
  while IFS= read -r f; do
    f="$(printf '%s' "$f" | cut -f5)"
    [ -n "$f" ] && [ -f "$ROOT/$f" ] && ctx+=("$ROOT/$f")
  done <<< "$pending"
  [ -f "$STANDARDS_FILE" ] && ctx+=("$STANDARDS_FILE")
  [ -f "$DOC_DIR/00-目标.md" ] && ctx+=("$DOC_DIR/00-目标.md")

  local rc=0
  claude_run "$CMD_DIR/review.md" "${ctx[@]+"${ctx[@]}"}" || rc=$?
  [ "$rc" -eq 3 ] && return 0
  if [ "$rc" -ne 0 ]; then report_failure "$rc" "验收的时候出错了"; return $?; fi

  group_say "CEO" "$(tail -50 "$LAST_LOG" 2>/dev/null)"
  rule
  say "验收结论已进群聊。${C_DIM}通过的自己去台账里改成「过了」，打回的重新派活。${C_OFF}"
  say "台账：${C_BOLD}./loop.sh 台账${C_OFF}"
}

# 看台账：谁手上有什么活、干完没有、验收没有
cmd_board() {
  if [ ! -f "$TASK_LOG" ]; then
    title "还没派过活"
    say "派活：${C_BOLD}./loop.sh 派活 <角色> \"任务\"${C_OFF}"
    return 0
  fi
  title "派活台账"
  awk -F'\t' 'NR>1 {printf "  #%-3s %-8s %-7s %s\n", $1, $2, $4, substr($3,1,46)}' "$TASK_LOG"
  say ""
  awk -F'\t' 'NR>1 {c[$4]++} END {for (k in c) printf "  %s %d 件\n", k, c[k]}' "$TASK_LOG"
}

# 设/看预算上限
cmd_budget() {
  local v="${1:-}"
  if [ -z "$v" ]; then
    local b; b="$(budget_get)"
    title "预算"
    if [ -z "$b" ]; then
      say "还没设上限。${C_DIM}没上限的话 ./loop.sh auto 不会启动——那等于装个不封顶的水龙头。${C_OFF}"
    else
      say "上限 \$$b，已经花了 \$$(cost_total)"
    fi
    say ""
    say "设上限：${C_BOLD}./loop.sh budget 50${C_OFF}（单位是美元）"
    return 0
  fi
  case "$v" in ''|*[!0-9.]*) die "预算要写数字，比如 ./loop.sh budget 50" ;; esac

  # 第 8 条：闸门数值只有老板能定。这里不加审批，只留痕——
  # 因为「能自己抬闸的闸门不是闸门」，而留痕之后你一眼就能看见谁抬过。
  # 出处：2026-08-18 执行 AI 自己把 $2 提到 $4，跑完才如实报。
  local before; before="$(budget_get)"
  local trail="$STATE_DIR/闸门记录.tsv"
  mkdir -p "$STATE_DIR"
  [ -f "$trail" ] || printf '时间\t从\t到\t当时已花\n' > "$trail"
  printf '%s\t%s\t%s\t%s\n' \
    "$(date '+%Y-%m-%d %H:%M')" "${before:-没设过}" "$v" "$(cost_total)" >> "$trail"

  state_set budget "$v"
  ok "预算上限设成 \$$v（已经花了 \$$(cost_total)）"
  if [ -n "$before" ] && [ "$before" != "$v" ]; then
    say "${C_DIM}闸门从 \$$before 改成了 \$$v，记在 .loop/闸门记录.tsv 里了。${C_OFF}"
    say "${C_DIM}这个数只有你能定——AI 装不下就该停下来问你，不许自己调门过车。${C_OFF}"
  fi
}

# 无人值守：自己一直往下跑，撞到闸门/预算/卡点就停。
#
# 为什么必须先有预算才让跑：实测一次调用 $0.68~$8.20。
# 没有上限的自动循环，是一个你睡着之后还在花钱的东西。
cmd_auto() {
  local b; b="$(budget_get)"
  if [ -z "$b" ]; then
    rule
    warn "还没设预算上限，不给跑自动。"
    say  "实测一次调用 \$0.68~\$8.20。没上限的无人值守，等于装了个不封顶的水龙头——"
    say  "你睡着了它还在花钱。"
    say  ""
    say  "先设一个你真能接受的数：${C_BOLD}./loop.sh budget 50${C_OFF}"
    rule
    return 1
  fi

  local start; start="$(cost_total)"
  title "无人值守开始"
  say "${C_DIM}预算上限 \$$b，已花 \$$start。撞到下面任何一条就停：${C_OFF}"
  say "${C_DIM}  预算到顶 ／ 轮到你拍板 ／ 轮到你干活 ／ 卡住了 ／ 全部做完${C_OFF}"
  rule

  local prev="" cur rc n=0
  while :; do
    n=$((n+1))
    [ "$n" -gt "${LOOP_AUTO_MAX:-40}" ] && { warn "跑了 $((n-1)) 轮，先停下喘口气。"; break; }

    budget_ok || break
    cur="$(state_get stage goal)"
    [ "$cur" = "done" ] && { ok "全部做完了。"; break; }

    rc=0; cmd_go || rc=$?
    local now; now="$(state_get stage goal)"

    case "$rc" in
      2) rule; info "停在这儿等你——上面写了要你做什么。"; break ;;
      3) break ;;
      0) : ;;
      *) rule; warn "卡住了，停下（退出码 $rc）。"; break ;;
    esac

    # 阶段没动、上一轮也没动 → 空转，别烧钱
    if [ "$now" = "$cur" ] && [ "$cur" = "$prev" ]; then
      warn "连着两轮卡在同一步没动，停下，不空转。"
      break
    fi
    prev="$cur"
  done

  rule
  local endc; endc="$(cost_total)"
  title "这一轮无人值守结束"
  say "  跑了 $n 轮，花了 \$$(awk -v a="$endc" -v s="$start" 'BEGIN{printf "%.2f", a-s}')（累计 \$$endc / 上限 \$$b）"
  say "  现在在：$(stage_label "$(state_get stage goal)")"
}

# 结项：这个项目到头了——不管是做成了，还是该停了。
#
# 为什么要有这个：止损线每次都在问「到了吗」，但「到了」之后没有出口。
# 没有出口的止损线，人会一直答"还没到"。
cmd_close() {
  local doc="$DOC_DIR/99-结项.md"
  [ -f "$doc" ] && { warn "已经结过项了：${doc#"$ROOT/"}"; return 0; }
  [ -f "$CMD_DIR/close.md" ] || die "缺少 .claude/commands/close.md"

  rule
  title "结项"
  say "这会把这个项目封存，并且写一份诚实的复盘："
  say "  ${C_BOLD}做成了没有 ／ 花了多少 ／ 为什么到这儿为止 ／ 下次不再犯的是什么${C_OFF}"
  say ""
  say "${C_DIM}封存之后 go / auto 都不会再往下跑。想重开就 ./loop.sh reset。${C_OFF}"
  rule

  local ctx=() s d
  for s in "${STAGES[@]}"; do
    d="$(stage_doc "$s")"; [ -n "$d" ] && [ -f "$d" ] && ctx+=("$d")
  done
  [ -f "$GROUP_CHAT" ] && ctx+=("$GROUP_CHAT")
  [ -f "$DOC_DIR/09-操盘记录.md" ] && ctx+=("$DOC_DIR/09-操盘记录.md")
  [ -f "$COST_LOG" ] && ctx+=("$COST_LOG")

  claude_run "$CMD_DIR/close.md" "${ctx[@]+"${ctx[@]}"}" || true

  if [ -f "$doc" ]; then
    state_set closed yes
    group_say "系统" "项目已结项。复盘写在 docs/99-结项.md。"
    rule
    ok "结项了。复盘在 ${C_BOLD}${doc#"$ROOT/"}${C_OFF}"
    say "${C_DIM}那份复盘值得过半年再看一遍——教训的保质期比结论长。${C_OFF}"
  else
    warn "没有产出 99-结项.md，按没结成处理，项目还开着。"
    return 1
  fi
}

# 从模板招一批人进来。不写名字就列出有哪些可招。
#
# 为什么是"按需招"而不是"一次全建"：实测一次调用 $0.68~$8.20，
# 十个专家各出一份意见书就是十几次调用。
# 全员开大会不是气派，是烧钱——CEO 该判断这件事问谁，而不是问所有人。
cmd_hire() {
  local pool="$ROOT/roles-模板"
  [ -d "$pool" ] || die "找不到角色模板目录：roles-模板/"

  if [ "$#" -eq 0 ] || [ -z "${1:-}" ]; then
    title "组织架构：你 → CEO → 两个分支"
    say ""
    say "  ${C_DIM}CEO（./loop.sh ceo）不用招，它一直在。${C_OFF}"
    say ""
    local layer f n desc
    for layer in 参谋 执行; do
      if [ "$layer" = "参谋" ]; then
        printf '  %s左分支 · 参谋层%s %s——CEO 咨询他们，只出意见书，不指挥执行%s\n' \
          "$C_BOLD" "$C_OFF" "$C_DIM" "$C_OFF"
      else
        printf '\n  %s右分支 · 执行层%s %s——CEO 派单给执行总监，总监再拆给下面的人%s\n' \
          "$C_BOLD" "$C_OFF" "$C_DIM" "$C_OFF"
      fi
      # 执行总监是右分支的头，排最前面；其余按名字排
      local files; files="$(ls "$pool"/*.md)"
      [ "$layer" = "执行" ] && files="$pool/执行总监.md
$(ls "$pool"/*.md | grep -v /执行总监.md)"
      # 参谋层里有几种类型（常驻／大师／镜子／审美），常驻的排前面。
      # 类型是已有的字段，看板也在用它——这里只是把它显示出来，没加新机制。
      local pass typ
      for pass in 常驻 大师 镜子 审美; do
        for f in $files; do
          n="$(basename "$f" .md)"
          grep -q "^层：$layer" "$f" 2>/dev/null || continue
          # || true 不能省：grep 没匹配到会返回 1，配上文件开头的
          # set -euo pipefail（pipefail 让整条管道也返回 1），整个脚本会当场退出。
          # 老角色文件没有「类型：」这一行，就是这么把 hire 整个打死的。
          typ="$(grep -m1 '^类型：' "$f" 2>/dev/null | sed 's/^类型：//' || true)"
          [ -z "$typ" ] && typ=常驻
          [ "$layer" = "参谋" ] && [ "$typ" != "$pass" ] && continue
          [ "$layer" = "执行" ] && [ "$pass" != "常驻" ] && continue
          desc="$(grep -m1 '^一句话：' "$f" | sed 's/^一句话：//' || true)"
          local tag=""
          [ "$typ" != "常驻" ] && tag="${C_BLUE}[$typ]${C_OFF} "
          if [ -f "$(role_file "$n")" ]; then
            printf '    %s%s%s %s%s %s在岗%s\n' \
              "$C_BOLD" "$(pad "$n" 14)" "$C_OFF" "$tag" "$desc" "$C_GREEN" "$C_OFF"
          else
            printf '    %s %s%s\n' "$(pad "$n" 14)" "$tag" "$desc"
          fi
        done
      done
    done
    say ""
    say "招人：${C_BOLD}./loop.sh hire 战略 财务 风控${C_OFF}"
    say "${C_DIM}别一次全招——一次会诊十几次调用，实测一次 \$0.68~\$8.20。让 CEO 判断该问谁。${C_OFF}"
    return 0
  fi

  mkdir -p "$ROLE_DIR"
  local n hired=0
  for n in "$@"; do
    [ -z "$n" ] && continue
    if [ ! -f "$pool/$n.md" ]; then warn "没有「$n」这个模板（跑 ./loop.sh hire 看有哪些）"; continue; fi
    if [ -f "$(role_file "$n")" ]; then say "  $n 已经在岗了，跳过"; continue; fi
    cp "$pool/$n.md" "$(role_file "$n")"
    ok "招了：$n"
    hired=$((hired+1))
  done
  [ "$hired" -eq 0 ] && return 0

  group_say "系统" "新来了 $hired 个人：$*。他们能看到这之后的群聊内容。"
  say ""
  say "问他们：${C_BOLD}./loop.sh ask <名字> \"问题\"${C_OFF}"
  say "看看都有谁：${C_BOLD}./loop.sh roles${C_OFF}"
}

# 你在群里说一句话。所有角色下次说话前都会看到。
cmd_say() {
  local text="${1:-}"
  [ -n "$text" ] || die "用法：./loop.sh say \"你想说的话\""
  group_say "你" "$text"
  ok "说了。所有角色下次开口前都会看到这句。"
  say "${C_DIM}群聊：docs/10-群聊.md${C_OFF}"
}

# 花了多少钱、哪一步最贵
#
# 这个命令存在的理由很具体：这套东西两次撞上额度上限、白烧 5 次重试，
# 而在此之前它对自己花了多少钱零可见性。撞上限那一刻才知道，已经晚了。
cmd_cost() {
  if [ ! -f "$COST_LOG" ]; then
    title "还没有花钱记录"
    if [ -z "$(json_parser)" ]; then
      warn "这台机器上没有 jq 也没有 python3，记不了账。"
      say  "不影响跑，只是看不到花了多少。装其中一个就能记。"
    else
      say "跑过 ./loop.sh go 之后就会有。"
    fi
    return 0
  fi

  title "花了多少钱"

  # 总账
  awk -F'\t' 'NR>1 && $3!="" { total += $3; secs += $4; n++ }
    END {
      if (n == 0) { print "  还没有有效记录"; exit }
      printf "  一共 %d 次调用，花了 $%.2f，用时 %d 分钟，平均一次 $%.2f\n", n, total, secs/60, total/n
    }' "$COST_LOG"

  # 分项，按花得多的排前面。排序只作用在数据行，别把表头也排进去。
  say ""
  printf '  %-22s %9s %6s %10s\n' "哪一步" "花了" "次数" "平均一次"
  awk -F'\t' 'NR>1 && $3!="" { cost[$2] += $3; cnt[$2]++ }
    END { for (k in cost) printf "%.4f\t%s\t%d\n", cost[k], k, cnt[k] }' "$COST_LOG" \
  | sort -rn \
  | awk -F'\t' '{ printf "  %-22s %8.2f %6d %10.2f\n", $2, $1, $3, $1/$3 }'

  # 走了别家接口的，这里的美元数是假的，必须当场说破。
  #
  # claude 报的 total_cost_usd 是按【Anthropic 价目表】算的。
  # 走 DeepSeek 时它照报一个数，但它不知道 DeepSeek 收多少钱。
  # 不标出来，账面上就是一笔看起来很正经的假账——那正是这套东西第2条不许干的事。
  local other; other="$(awk -F'\t' 'NR>1 && $5!="" && $5!="官方" { c[$5]++ } END { for (k in c) printf "%s(%d次) ", k, c[k] }' "$COST_LOG")"
  if [ -n "$other" ]; then
    say ""
    warn "上面有一部分不作数：$other"
    say  "  ${C_DIM}这些走的不是官方接口，美元数是按官方价目表折算的，不是你真付的钱。"
    say  "  真实花费去那家自己的后台看。哪几笔走的谁家，看 接口 那一列。${C_OFF}"
  fi

  say ""
  # 跟目标预算对一下——光看花了多少没用，要看占预算多少
  local budget; budget="$(grep -oE '¥?[0-9]+ *元?/ *月|每月[^0-9]*[0-9]+' "$DOC_DIR/00-目标.md" 2>/dev/null | head -1 || true)"
  [ -n "$budget" ] && say "${C_DIM}你在 00-目标.md 里写的预算：$budget${C_OFF}"
  say "${C_DIM}明细：${COST_LOG#"$ROOT/"}${C_OFF}"
}

# ---------- 接口：给每个员工换脑子 ----------
#
# 这条命令回答一个问题：这个员工，用谁家的 AI？
#
# 判断力省不得，体力活可以省。CEO 裁决、风控反证用最强的；
# 客服分拣、竞品巡查、内容初稿用便宜的——**便宜的差价是几十倍，不是几倍。**
provider_list_known() {
  say ""
  printf '  %s%s%s\n' "$(pad 代号 18)" "$(pad 是什么 26)" "查证日期"
  local c
  for c in 官方 deepseek deepseek-flash; do
    local row; row="$(provider_row "$c")"
    printf '  %s%s%s\n' \
      "$(pad "$(echo "$row" | cut -d'|' -f1)" 18)" \
      "$(pad "$(echo "$row" | cut -d'|' -f2)" 26)" \
      "$(echo "$row" | cut -d'|' -f6)"
  done
}

# 要钥匙。三个来源：命令行给的 → 环境变量里的 → 当场问。
provider_need_key() {
  local code="$1" given="${2:-}"
  local fam; fam="$(provider_family "$code")"
  [ -f "$(provider_keyfile "$code")" ] && [ -z "$given" ] && return 0

  local key="$given"
  if [ -z "$key" ]; then
    case "$fam" in
      deepseek) key="${DEEPSEEK_API_KEY:-}" ;;
    esac
  fi
  if [ -z "$key" ] && [ -t 0 ]; then
    say ""
    say "要一把 ${C_BOLD}$fam${C_OFF} 的钥匙（API Key）。"
    say "${C_DIM}去 platform.deepseek.com 后台自己建一把，形如 sk-xxxx。${C_OFF}"
    printf '  贴在这儿（打字不显示，贴完回车）：'
    read -r -s key; printf '\n'
  fi
  if [ -z "$key" ]; then
    warn "没拿到钥匙，没法切。"
    say  "两种给法："
    say  "  ${C_BOLD}./loop.sh 接口 <员工> $code sk-你的key${C_OFF}"
    say  "  ${C_BOLD}export DEEPSEEK_API_KEY=sk-你的key${C_OFF} 之后再跑一次"
    return 1
  fi
  provider_save_key "$code" "$key"
  ok "钥匙存好了：${C_DIM}$(provider_keyfile "$code" | sed "s|$ROOT/||")${C_OFF}（只有你能读，也不会进版本库）"
  return 0
}

cmd_provider() {
  local a1="${1:-}" a2="${2:-}" a3="${3:-}"

  # 不带参数：一览表
  if [ -z "$a1" ]; then
    local rs; rs="$(roles_list)"
    title "每个员工用谁家的脑子"
    if [ -z "$rs" ]; then
      warn "还一个员工都没招。先 ${C_BOLD}./loop.sh hire 客服 竞品${C_OFF}"
    else
      say ""
      printf '  %s%s%s%s\n' "$(pad 员工 14)" "$(pad 层 8)" "$(pad 用谁家的 22)" "钥匙"
      rule
      local r
      while IFS= read -r r; do
        [ -z "$r" ] && continue
        local p; p="$(role_provider "$r")"
        local nm="官方" col="$C_DIM" ky=""
        if [ "$p" != "官方" ]; then
          nm="$(provider_field "$p" 2)"; col="$C_GREEN"
          if [ -f "$(provider_keyfile "$p")" ]; then ky="有"
          else ky="${C_RED}丢了 → ./loop.sh 接口 $r $p sk-你的key${C_OFF}"; fi
        fi
        printf '  %s%s%s%s%s %s\n' \
          "$(pad "$r" 14)" "$(pad "$(role_layer "$r")" 8)" \
          "$col" "$(pad "$nm" 22)" "$C_OFF" "$ky"
      done <<< "$rs"
    fi
    provider_list_known
    say ""
    say "换一个人：      ${C_BOLD}./loop.sh 接口 客服 deepseek${C_OFF}"
    say "换一整层：      ${C_BOLD}./loop.sh 接口 执行层 deepseek${C_OFF}"
    say "换回官方：      ${C_BOLD}./loop.sh 接口 客服 官方${C_OFF}"
    say "先验一下通不通：${C_BOLD}./loop.sh 接口 测 客服${C_OFF}"
    say ""
    say "${C_DIM}判断力省不得，体力活可以省——CEO/风控/战略留官方，客服/竞品/内容切便宜的。${C_OFF}"
    return 0
  fi

  # 测：真打一次，看通不通、多久、多少钱
  if [ "$a1" = "测" ] || [ "$a1" = "test" ]; then
    local role="$a2"
    [ -z "$role" ] && die "要说测谁：./loop.sh 接口 测 客服"
    [ -f "$(role_file "$role")" ] || die "没有「$role」这个员工（./loop.sh roles 看都有谁）"
    local p; p="$(role_provider "$role")"
    title "测「$role」的接口：$(provider_field "$p" 2 2>/dev/null || echo "$p")"
    say "${C_DIM}问他一句最短的话，只看通不通。${C_OFF}"
    rule
    local t0; t0="$(date +%s)"
    local rc=0
    NO_GROUP_CHAT=1 ROLE_ISOLATED=1 \
      ask_role "$role" "只回四个字：接口通了。别的什么都不要说。" >/dev/null 2>&1 || rc=$?
    local t1; t1="$(date +%s)"
    rule
    if [ "$rc" -ne 0 ]; then
      warn "没通。"
      say ""
      say "它自己的原话："
      say "${C_DIM}$(tail -6 "$LAST_LOG" 2>/dev/null || tail -6 "$LAST_LOG.err" 2>/dev/null)${C_OFF}"
      say ""
      say "最常见的三个原因："
      say "  1. 钥匙不对或者过期了 → ${C_BOLD}./loop.sh 接口 $role $p sk-新的key${C_OFF}"
      say "  2. 那家接口地址变了 → 去他家文档确认一下，改 $(role_env "$role" | sed "s|$ROOT/||")"
      say "  3. 余额不够了 → 去他家后台看"
      say ""
      say "先切回官方把活干完：${C_BOLD}./loop.sh 接口 $role 官方${C_OFF}"
      return 1
    fi
    ok "通了，用了 $((t1-t0)) 秒。"
    say "  它回的：${C_DIM}$(tail -3 "$LAST_LOG" 2>/dev/null | tr -d '\n')${C_OFF}"
    if [ "$p" != "官方" ]; then
      say ""
      warn "钱这一项要说清楚：账单里这几笔的美元数【不作数】。"
      say  "  那个数是 claude 按 Anthropic 的价目表算的，它不知道 $p 收多少钱。"
      say  "  ${C_BOLD}真实花费去 $p 自己的后台看。${C_OFF}台账里已经标了是谁家的。"
    fi
    return 0
  fi

  # 换：./loop.sh 接口 <员工|层> <代号> [key]
  local who="$a1" code="$a2" key="$a3"
  [ -z "$code" ] && die "要说换成谁家的：./loop.sh 接口 $who deepseek（跑 ./loop.sh 接口 看有哪几家）"
  provider_row "$code" >/dev/null 2>&1 || {
    warn "不认识「$code」这家。"
    say "${C_DIM}这张表里只放查证过的——凭印象加一家进来，你照着配一次配不通，这功能就废了。${C_OFF}"
    provider_list_known
    say ""
    say "要接表上没有的，自己写 ${C_BOLD}.loop/roles/<员工>.env${C_OFF}，"
    say "格式看 ${C_BOLD}安装与落地.md${C_OFF} 第三节。"
    return 1
  }

  # 谁：一个人 / 一整层 / 全部
  local -a targets=()
  case "$who" in
    全部|all)
      while IFS= read -r r; do [ -n "$r" ] && targets+=("$r"); done <<< "$(roles_list)" ;;
    执行层|执行|右分支)
      while IFS= read -r r; do
        [ -n "$r" ] && [ "$(role_layer "$r")" = "执行" ] && targets+=("$r")
      done <<< "$(roles_list)" ;;
    参谋层|参谋|左分支)
      while IFS= read -r r; do
        [ -n "$r" ] && [ "$(role_layer "$r")" = "参谋" ] && targets+=("$r")
      done <<< "$(roles_list)" ;;
    *)
      [ -f "$(role_file "$who")" ] || die "没有「$who」这个员工（./loop.sh roles 看都有谁）"
      targets=("$who") ;;
  esac
  [ "${#targets[@]}" -eq 0 ] && die "「$who」这一层现在一个人都没有。先 ./loop.sh hire"

  # 切回官方不用钥匙；切别家要
  local url; url="$(provider_field "$code" 3)"
  if [ -n "$url" ]; then
    provider_need_key "$code" "$key" || return 1
  fi

  title "换脑子"
  local r n=0
  for r in "${targets[@]}"; do
    local before; before="$(role_provider "$r")"
    if provider_apply "$r" "$code"; then
      local after; after="$(role_provider "$r")"
      printf '  %s%s → %s%s%s\n' "$(pad "$r" 14)" "$before" "$C_GREEN" "$after" "$C_OFF"
      n=$((n+1))
    else
      warn "  $r 没换成"
    fi
  done
  say ""
  ok "换了 $n 个人。${C_DIM}其他人一点没动。${C_OFF}"

  if [ -n "$url" ]; then
    say ""
    say "${C_BOLD}下一步：先验一个，别一次全信。${C_OFF}"
    say "  ${C_BOLD}./loop.sh 接口 测 ${targets[0]}${C_OFF}"
    say ""
    warn "还有一件事必须先说清楚：${C_BOLD}账单会不准。${C_OFF}"
    say  "  ${C_DIM}claude 只会按 Anthropic 的价目表算钱，它不知道别家收多少。"
    say  "  台账第5列标了每一笔走的谁家，真实花费去那家后台看。${C_OFF}"
  fi
  return 0
}

# ---------- 上线评审 ＋ 运营期 ----------
#
# 结构照搬「启蒙」那一套：一人一块、各自落盘、产物不在就是没交、可重跑。
LAUNCH_FILE="$DOC_DIR/09-上线.md"
LAUNCH_PANEL="${LAUNCH_PANEL:-营销大师 MVP大师 商业专家}"
LEDGER="$STATE_DIR/账本.tsv"

cmd_launch() {
  [ -f "$BLUEPRINT_FILE" ] || die "先把蓝图画出来：./loop.sh 蓝图"
  local b; b="$(budget_get)"
  [ -z "$b" ] && { warn "先设个上限：./loop.sh budget 20"; return 1; }

  local who
  for who in $LAUNCH_PANEL; do
    [ -f "$(role_file "$who")" ] || { mkdir -p "$ROLE_DIR"; cp "$ROOT/roles-模板/$who.md" "$(role_file "$who")"; }
  done

  title "上线评审"
  say "${C_DIM}三个人各查一块，CEO 拍板能不能上。三道闸有一道不过就不许上。${C_OFF}"
  rule

  local ctx=("$BLUEPRINT_FILE")
  local f
  for f in "$DOC_DIR/00-目标.md" "$DOC_DIR/00-论证.md" "$LISTEN_FILE"; do
    [ -f "$f" ] && ctx+=("$f")
  done

  for who in $LAUNCH_PANEL; do
    local out; out="$WORK_DIR/$who/$( [ "$who" = 营销大师 ] && echo 方案 || { [ "$who" = MVP大师 ] && echo 砍完的 || echo 账; } ).md"
    if [ -f "$out" ]; then say "  ${C_DIM}$who 已经交过了，跳过${C_OFF}"; continue; fi
    mkdir -p "$(dirname "$out")"
    info "  $who …"
    local rc=0
    NO_GROUP_CHAT=1 ROLE_ISOLATED=1 ROLE_CWD="$WORK_DIR/$who" \
      ask_role "$who" "照你的规矩做一轮，写进 $out。每个数字标 [事实|推断|猜测]，能查的必须查。" \
      "${ctx[@]}" >/dev/null 2>&1 || rc=$?
    if [ -f "$out" ]; then ok "  $who 交了"; group_say "$who" "$(head -20 "$out")"
    else warn "  $who 没交东西（退出码 $rc）"; fi
  done

  rule
  title "CEO 拍板"
  local actx=("${ctx[@]}")
  for f in "$WORK_DIR"/营销大师/*.md "$WORK_DIR"/MVP大师/*.md "$WORK_DIR"/商业专家/*.md; do
    [ -f "$f" ] && actx+=("$f")
  done
  [ -f "$ROOT/references/判断标准.md" ] && actx+=("$ROOT/references/判断标准.md")
  local rc=0
  claude_run "$CMD_DIR/上线评审.md" "${actx[@]}" || rc=$?
  [ "$rc" -eq 3 ] && return 0
  if [ "$rc" -ne 0 ]; then report_failure "$rc" "上线评审出错了"; return $?; fi
  [ -f "$LAUNCH_FILE" ] || { rule; warn "没产出 09-上线.md，按没做成处理。"; return 1; }

  rule
  ok "评审结果在 ${C_BOLD}${LAUNCH_FILE#"$ROOT/"}${C_OFF}"
  awk '/^##[[:space:]]*上线前三道闸/ { on=1 } on && /^##[[:space:]]*需要你定/ { print; exit } on { print }' \
    "$LAUNCH_FILE" 2>/dev/null | head -14
  rule
  say "${C_DIM}定止损线和投入：./loop.sh 止损 \"到6月还没有10个付费用户就停\"${C_OFF}"
  say "${C_DIM}上线之后每天：./loop.sh 日报　　看仪表盘：./loop.sh 看板${C_OFF}"
  rule
}

# 止损线 ＋ 投入 —— 他只需要定这两个
cmd_stoploss() {
  local text="${1:-}"
  if [ -z "$text" ]; then
    title "止损线"
    say "现在：$(state_get 止损线 "${C_YELLOW}还没定${C_OFF}")"
    say "投入上限：\$$(budget_get)"
    say ""
    say "定一条：${C_BOLD}./loop.sh 止损 \"到6月底还没有10个付费用户就停，然后改方向\"${C_OFF}"
    say "${C_DIM}必须是【一个日期 ＋ 一个可数的事实】。没有出口的止损线，人会一直答"还没到"。${C_OFF}"
    return 0
  fi
  state_set 止损线 "$text"
  ok "记下了：$text"
  say "${C_DIM}每天的日报会拿这条对一次，快到了会提前叫你。${C_OFF}"
}

# 记账 —— 收入支出，日报和仪表盘都读它
cmd_ledger() {
  local kind="${1:-}" amt="${2:-}" note="${3:-}"
  if [ -z "$kind" ]; then
    title "账本"
    if [ -f "$LEDGER" ]; then
      awk -F'\t' 'NR>1 { if ($2=="收") inc+=$3; else exp+=$3 }
        END { printf "  收入 %.2f　支出 %.2f　净 %.2f\n", inc, exp, inc-exp }' "$LEDGER"
      say ""; tail -8 "$LEDGER" | awk -F'\t' '{printf "  %s  %s %8s  %s\n",$1,$2,$3,$4}'
    else say "  还没记过账"; fi
    say ""
    say "记一笔：${C_BOLD}./loop.sh 记账 收 500 \"第一单\"${C_OFF}　${C_BOLD}./loop.sh 记账 支 30 \"服务器\"${C_OFF}"
    return 0
  fi
  case "$kind" in 收|支) ;; *) die "第一个参数只能是 收 或 支" ;; esac
  [ -n "$amt" ] || die '用法：./loop.sh 记账 收 500 "第一单"'
  mkdir -p "$STATE_DIR"
  [ -f "$LEDGER" ] || printf '日期\t收支\t金额\t说明\n' > "$LEDGER"
  printf '%s\t%s\t%s\t%s\n' "$(date '+%Y-%m-%d')" "$kind" "$amt" "$note" >> "$LEDGER"
  ok "记下了：$kind $amt $note"
}

# 日报 —— 上线之后每天一份，他只看这个
cmd_daily_report() {
  [ -f "$LAUNCH_FILE" ] || die "还没上线。先跑 ./loop.sh 上线"
  title "日报"
  rule
  local ctx=("$LAUNCH_FILE")
  [ -f "$LEDGER" ] && ctx+=("$LEDGER")
  [ -f "$DOC_DIR/10-群聊.md" ] && ctx+=("$DOC_DIR/10-群聊.md")

  local tmp="$STATE_DIR/日报.md"
  { printf '你是 CEO。给老板写今天的日报。\n\n'
    printf '**他只看这一份，所以只写一页，写他能立刻做决定的东西。**\n'
    printf '说话见 references/怎么说话.md：不许出现商业术语。\n\n'
    printf '止损线：%s\n投入上限：$%s　已花：$%s\n\n' \
      "$(state_get 止损线 '（还没定）')" "$(budget_get)" "$(cost_total)"
    printf '格式：\n## 今天\n（一句话：好了还是坏了）\n\n'
    printf '## 数\n收入__ 支出__ 净__ ｜ 离止损线还有__\n\n'
    printf '## 要你拍板的\n（没有就写「没有，你不用管」）\n\n'
    printf '## 我们明天干什么\n（三条以内）\n'
  } > "$tmp"
  local rc=0
  claude_run "$tmp" "${ctx[@]}" || rc=$?
  [ "$rc" -eq 3 ] && return 0
  [ "$rc" -ne 0 ] && { report_failure "$rc" "写日报的时候出错了"; return $?; }
  rule
  say "${C_DIM}完整仪表盘：./loop.sh 看板${C_OFF}"
}

# ---------- 启蒙：四位大师各说一块，拧成几个能选的方向 ----------
#
# 结构照搬「论证」那一套（lz_one 那个路子）：一人一块不重叠、
# 各自落盘、产物不在就是没交、可重跑跳过已交的。不重造。
ENLIGHT_FILE="$DOC_DIR/00-启蒙.md"
MASTERS="${MASTERS:-美学大师 哲学大师 历史人文大师 精神意识大师}"

cmd_enlighten() {
  [ -f "$BLUEPRINT_FILE" ] || die "先把蓝图画出来：./loop.sh 蓝图"
  local b; b="$(budget_get)"
  [ -z "$b" ] && { warn "这一步要跑五次调用。先设个上限：./loop.sh budget 20"; return 1; }

  local who
  for who in $MASTERS; do
    if [ ! -f "$(role_file "$who")" ]; then
      [ -f "$ROOT/roles-模板/$who.md" ] || die "缺少 roles-模板/$who.md"
      mkdir -p "$ROLE_DIR"; cp "$ROOT/roles-模板/$who.md" "$(role_file "$who")"
    fi
  done

  title "启蒙 · 四位大师"
  say "${C_DIM}一人只管一块，不重叠。最后拧成几个你能选的方向，具体到按钮。${C_OFF}"
  rule

  local ctx=("$BLUEPRINT_FILE")
  local f
  for f in "$LISTEN_FILE" "$DOC_DIR/00-镜子.md" "$AESTHETIC_FILE" "$DOC_DIR/00-论证.md"; do
    [ -f "$f" ] && ctx+=("$f")
  done
  local kb; kb="$(kb_files)"
  [ -n "$kb" ] && while IFS= read -r f; do [ -n "$f" ] && ctx+=("$f"); done <<< "$kb"

  for who in $MASTERS; do
    local out="$WORK_DIR/$who/启蒙.md"
    if [ -f "$out" ]; then
      say "  ${C_DIM}$who 已经交过了，跳过（想重跑就删掉 ${out#"$ROOT/"}）${C_OFF}"; continue
    fi
    mkdir -p "$(dirname "$out")"
    info "  $who …"
    local q
    q="$(printf '%s\n' \
      "照你那一块，给这个产品的形式和细节提判断。" \
      "" \
      "**每一条必须落到一个能做的决定上**，落不到的删掉。" \
      "「要有人文关怀」不算，「删除不弹确认框，改成 5 秒撤销」才算。" \
      "" \
      "**每条判断挂出处**，能查的那种。查不到就说查不到，不许编。" \
      "" \
      "写进 $out：" \
      "## 我这一块看到的" \
      "## 具体到能做的决定（至少 3 条，每条带出处和代价）" \
      "## 我最没把握的一条" )"
    local rc=0
    NO_GROUP_CHAT=1 ROLE_ISOLATED=1 ROLE_CWD="$WORK_DIR/$who" \
      ask_role "$who" "$q" "${ctx[@]}" >/dev/null 2>&1 || rc=$?
    if [ -f "$out" ]; then ok "  $who 交了"; group_say "$who" "$(head -20 "$out")"
    else warn "  $who 没交东西（退出码 $rc）"; fi
  done

  rule
  title "拧成方向"
  local actx=("${ctx[@]}")
  for who in $MASTERS; do
    [ -f "$WORK_DIR/$who/启蒙.md" ] && actx+=("$WORK_DIR/$who/启蒙.md")
  done
  local rc=0
  claude_run "$CMD_DIR/启蒙.md" "${actx[@]}" || rc=$?
  [ "$rc" -eq 3 ] && return 0
  if [ "$rc" -ne 0 ]; then report_failure "$rc" "综合的时候出错了"; return $?; fi
  [ -f "$ENLIGHT_FILE" ] || { rule; warn "没产出 00-启蒙.md，按没做成处理。"; return 1; }

  rule
  ok "方向在 ${C_BOLD}${ENLIGHT_FILE#"$ROOT/"}${C_OFF}"
  say ""
  say "${C_DIM}选一个：./loop.sh 改 \"我选 B\"　它会把这个方向并进蓝图${C_OFF}"
  say "${C_DIM}四位大师的完整意见：work/<名字>/启蒙.md${C_OFF}"
  rule
}

# ---------- 审美：给他看真东西，从他的选择里反推他的审美 ----------
#
# 不许问「你喜欢什么风格」——他答不上来，没人答得上来。
# 他看到了能判断，闭着眼描述不出来，这是两回事。
AESTHETIC_FILE="$DOC_DIR/00-审美.md"

cmd_aesthetic() {
  [ -f "$BLUEPRINT_FILE" ] || die "先把蓝图画出来：./loop.sh 蓝图"
  if [ ! -f "$(role_file 前端审美)" ]; then
    [ -f "$ROOT/roles-模板/前端审美.md" ] || die "缺少 roles-模板/前端审美.md"
    mkdir -p "$ROLE_DIR"; cp "$ROOT/roles-模板/前端审美.md" "$(role_file 前端审美)"
    ok "把前端审美专家请进来了"
  fi

  title "审美"
  say "${C_DIM}不问你喜欢什么风格——给你看真东西，从你的选择里反推。${C_OFF}"
  rule

  local ctx=("$BLUEPRINT_FILE")
  [ -f "$DOC_DIR/00-镜子.md" ] && ctx+=("$DOC_DIR/00-镜子.md")
  [ -f "$AESTHETIC_FILE" ] && ctx+=("$AESTHETIC_FILE")
  local kb; kb="$(kb_files)"
  [ -n "$kb" ] && while IFS= read -r f; do [ -n "$f" ] && ctx+=("$f"); done <<< "$kb"

  local q
  q="$(printf '%s\n' \
    "照你的规矩来一轮，写进 $AESTHETIC_FILE。" \
    "" \
    "**参照物必须联网查证，是他能当场打开看的真东西，带链接和查证日期。**" \
    "凭印象说某个产品长什么样——你记忆里那一版可能是三年前的，人家早改了。" \
    "" \
    "三个方向，每个都要写到能想象出画面，而且都要有代价。" \
    "然后只问他一个场景题（不问偏好），再加那道「一年后他朋友会怎么说」。" )"

  local rc=0
  ROLE_ISOLATED=1 ask_role 前端审美 "$q" "${ctx[@]}" || rc=$?
  [ "$rc" -eq 3 ] && return 0
  if [ "$rc" -ne 0 ]; then report_failure "$rc" "挑审美的时候出错了"; return $?; fi
  [ -f "$AESTHETIC_FILE" ] || { rule; warn "没产出 $(basename "$AESTHETIC_FILE")，按没做成处理。"; return 1; }

  rule
  ok "三个方向在 ${C_BOLD}${AESTHETIC_FILE#"$ROOT/"}${C_OFF}"
  say ""
  say "${C_DIM}挑一个：./loop.sh ask 前端审美 \"我选 B\"${C_OFF}"
  say "${C_DIM}它会从你的选择里反推出一句你的审美标准，以后所有界面取舍都拿那句判。${C_OFF}"
  rule
}

# ---------- 落地手册：一步一步带他做出来，含所有要花钱的点 ----------
cmd_manual() {
  [ -f "$BLUEPRINT_FILE" ] || die "先把蓝图画出来：./loop.sh 蓝图"
  local b; b="$(budget_get)"
  [ -z "$b" ] && { warn "这一步要联网查一堆价格。先设个上限：./loop.sh budget 20"; return 1; }

  title "落地手册"
  say "${C_DIM}一步一步、含所有要花钱的点。写给一个完全不会写代码的人看。${C_OFF}"
  rule

  local ctx=("$BLUEPRINT_FILE")
  local f
  for f in "$AESTHETIC_FILE" "$DOC_DIR/06-技术与落地.md" "$DOC_DIR/00-论证.md"; do
    [ -f "$f" ] && ctx+=("$f")
  done

  local rc=0
  claude_run "$CMD_DIR/落地手册.md" "${ctx[@]}" || rc=$?
  [ "$rc" -eq 3 ] && return 0
  if [ "$rc" -ne 0 ]; then report_failure "$rc" "写手册的时候出错了"; return $?; fi
  local out="$DOC_DIR/08-落地手册.md"
  [ -f "$out" ] || { rule; warn "没产出 08-落地手册.md，按没做成处理。"; return 1; }

  rule
  ok "手册在 ${C_BOLD}${out#"$ROOT/"}${C_OFF}"
  say ""
  awk '/^##[[:space:]]*这事一共要花多少钱/ { on=1 } on && /^##[[:space:]]*上架/ { exit } on { print }' "$out" 2>/dev/null | head -24
  rule
  say "${C_DIM}里面有几条路可选，每条都写了代价和死法。选好了敲 ./loop.sh go${C_OFF}"
  rule
}

# ---------- 蓝图：一直改到他说「对，这就是我要做的」 ----------
#
# 这是个【收敛循环】，跟第1步「听懂」用的是同一套机制（round_* 那几个）：
#   它自己在文档里写「状态：还在改 / 就是它了」
#   还在改 → 停下来问你一个问题，不往下走
#   一次只问一个，同一轮的问题在本地走完，全答完了才回去重跑一轮
#
# 「就是它了」这四个字只有它听到你亲口说了那句话才准写。
# 你说"挺好的""行吧"不算——那是客气，不是拍板。
BLUEPRINT_FILE="$DOC_DIR/00-蓝图.md"
BP_PROGRESS="$STATE_DIR/蓝图答题进度"
BP_MAX_ROUNDS="${BP_MAX_ROUNDS:-12}"
BP_QA='^##[[:space:]]*我想确认一件事'
BP_QB='^##[[:space:]]*详细版'

bp_state()    { round_state "$BLUEPRINT_FILE" 就是它了; }
bp_round()    { round_num "$BLUEPRINT_FILE"; }
bp_q_count()  { round_q_count "$BLUEPRINT_FILE" "$BP_QA" "$BP_QB"; }
bp_q_nth()    { round_q_nth "$BLUEPRINT_FILE" "$BP_QA" "$BP_QB" "$1"; }
bp_answered() { round_answered "$BP_PROGRESS" "$(bp_round)"; }

# 老板自己的知识库/审美文档。有就喂进去，没有就跳过。
# 这是预留的口子：以后他往 references/我的知识库/ 里丢什么，蓝图就会读什么。
kb_files() {
  local d="$ROOT/references/我的知识库"
  [ -d "$d" ] || return 0
  find "$d" -maxdepth 2 -type f \( -name '*.md' -o -name '*.txt' \) 2>/dev/null | sort
}

cmd_blueprint() {
  [ -f "$LISTEN_FILE" ] || die "先跑第1步：./loop.sh start \"你想说的\""

  local round; round="$(bp_round)"
  if [ "$round" -ge "$BP_MAX_ROUNDS" ] && [ "$(bp_state)" != "到了" ]; then
    rule
    warn "改了 $round 轮还没定下来。"
    say  "${C_DIM}这通常不是蓝图的问题，是方向本身还没定。回头看看 docs/00-镜子.md，"
    say  "或者 ./loop.sh 照镜子 —— 有时候改不完，是因为要做的根本不是这个。${C_OFF}"
    rule
    return 2
  fi

  title "产品蓝图 · 第 $((round + 1)) 轮"
  say "${C_DIM}一直改到你说「对，这就是我要做的」为止。${C_OFF}"
  rule

  local ctx=("$LISTEN_FILE")
  local f
  for f in "$DOC_DIR/00-目标.md" "$DOC_DIR/00-论证.md" "$DOC_DIR/00-镜子.md" \
           "$DOC_DIR/03-什么算好.md" "$BLUEPRINT_FILE"; do
    [ -f "$f" ] && ctx+=("$f")
  done
  local kb; kb="$(kb_files)"
  if [ -n "$kb" ]; then
    while IFS= read -r f; do [ -n "$f" ] && ctx+=("$f"); done <<< "$kb"
    say "${C_DIM}读上了你自己的知识库（$(printf '%s\n' "$kb" | wc -l) 份）${C_OFF}"
  fi

  local rc=0
  claude_run "$CMD_DIR/蓝图.md" "${ctx[@]}" || rc=$?
  [ "$rc" -eq 3 ] && return 0
  if [ "$rc" -ne 0 ]; then report_failure "$rc" "画蓝图的时候出错了"; return $?; fi
  [ -f "$BLUEPRINT_FILE" ] || { rule; warn "没产出 $(basename "$BLUEPRINT_FILE")，按没做成处理。"; return 1; }

  bp_gate
  [ "$(bp_state)" = "到了" ] && return 0 || return 2
}

bp_gate() {
  rule
  if [ "$(bp_state)" = "到了" ]; then
    title "定了 🎉"
    say "你说了「就是它了」，蓝图锁定。"
    say ""
    say "完整的在 ${C_BOLD}${BLUEPRINT_FILE#"$ROOT/"}${C_OFF}"
    say "${C_DIM}想看细节：那份文档里「详细版」那一节——用户流程、技术路线、时间表、第一周每天做什么${C_OFF}"
    say ""
    say "接着往下：${C_BOLD}./loop.sh go${C_OFF}"
    rule
    return 0
  fi

  local total done_n idx
  total="$(bp_q_count)"; done_n="$(bp_answered)"; idx=$((done_n + 1))
  if [ "$total" -eq 0 ]; then
    title "这一版画好了"
    say "看看：${C_BOLD}${BLUEPRINT_FILE#"$ROOT/"}${C_OFF}"
    say ""
    say "${C_BOLD}对了就说一句：./loop.sh 定了${C_OFF}"
    say "${C_DIM}要改就说哪儿不对：./loop.sh 改 \"这个方向不对，我其实想…\"${C_OFF}"
    rule
    return 0
  fi

  title "这一版画好了，有一件事想跟你确认"
  [ "$total" -gt 1 ] && say "${C_DIM}第 $idx 个，共 $total 个。答完这个再给下一个。${C_OFF}"
  say ""
  printf '%s\n' "$(bp_q_nth "$idx")"
  rule
  say "回答：${C_BOLD}./loop.sh 改 \"A\"${C_OFF}　${C_DIM}或者直接说哪儿不对${C_OFF}"
  say "${C_BOLD}已经对了就说：./loop.sh 定了${C_OFF}"
  say ""
  say "${C_DIM}完整蓝图（含详细版）：${BLUEPRINT_FILE#"$ROOT/"}${C_OFF}"
  rule
}

# 回答蓝图的问题 / 说哪儿要改
cmd_blueprint_answer() {
  local text="${1:-}"
  [ -n "$text" ] || die '用法：./loop.sh 改 "A" 或 ./loop.sh 改 "这个方向不对，我其实想…"'
  [ -f "$BLUEPRINT_FILE" ] || die "还没有蓝图。先跑 ./loop.sh 蓝图"

  local round total done_n idx
  round="$(bp_round)"; total="$(bp_q_count)"
  done_n="$(bp_answered)"; idx=$((done_n + 1))

  {
    if [ "$total" -gt 0 ] && [ "$idx" -le "$total" ]; then
      printf '\n## 你的回答 · 第 %s 轮 · 问题 %s\n\n' "$round" "$idx"
    else
      printf '\n## 你说要改的（第 %s 轮）\n\n' "$round"
    fi
    printf '%s\n' "$text"
  } >> "$BLUEPRINT_FILE"
  round_answered_set "$BP_PROGRESS" "$round" "$idx"
  ok "记下了。"

  # 同一轮还有没答的，本地接着问，不重跑 AI（重跑一次就是多花一次钱）
  if [ "$total" -gt 0 ] && [ "$idx" -lt "$total" ]; then
    rule
    title "下一个 —— 第 $((idx+1)) 个，共 $total 个"
    say ""
    printf '%s\n' "$(bp_q_nth "$((idx+1))")"
    rule
    say "回答：${C_BOLD}./loop.sh 改 \"A\"${C_OFF}　${C_BOLD}已经对了：./loop.sh 定了${C_OFF}"
    rule
    return 0
  fi

  say "${C_DIM}照你说的重画一版。${C_OFF}"
  rule
  cmd_blueprint
}

# 「对，这就是我要做的」——只有你亲口说，才算数
cmd_blueprint_lock() {
  [ -f "$BLUEPRINT_FILE" ] || die "还没有蓝图。先跑 ./loop.sh 蓝图"
  {
    printf '\n## 你拍板了（%s）\n\n' "$(date '+%Y-%m-%d %H:%M')"
    printf '对，这就是我要做的。\n'
  } >> "$BLUEPRINT_FILE"
  # 状态行是它自己写的，这里只补一句机器读得到的，免得它下一轮又当没定
  printf '\n状态：就是它了\n' >> "$BLUEPRINT_FILE"
  rule
  title "定了 🎉"
  say "蓝图锁在 ${C_BOLD}${BLUEPRINT_FILE#"$ROOT/"}${C_OFF}"
  say ""
  say "${C_DIM}想看细节：那份文档里「详细版」那一节${C_OFF}"
  say "接着往下：${C_BOLD}./loop.sh go${C_OFF}"
  rule
}

# ---------- 照镜子：在动手之前，先看清他到底想要什么 ----------
#
# 为什么要有这一步：大多数项目不是死于做得不好，
# 是死于【做的根本不是他真正想要的那个东西】——
# 做到一半发现"我好像也没那么想要这个"，然后就停了。
#
# 这一步风险最高，因为心理层面的话最容易编、听起来最深刻、最没法核对。
# 所以人生导师那份角色定义里写死了一条：
# 每一句关于他的话，必须能指回他自己说过的原话。「你其实是……」一次都不许出现。
MIRROR_FILE="$DOC_DIR/00-镜子.md"

cmd_mirror() {
  [ -f "$LISTEN_FILE" ] || die "先跑第1步把你的话拆开：./loop.sh start \"你想说的\""

  if [ ! -f "$(role_file 人生导师)" ]; then
    if [ -f "$ROOT/roles-模板/人生导师.md" ]; then
      mkdir -p "$ROLE_DIR"
      cp "$ROOT/roles-模板/人生导师.md" "$(role_file 人生导师)"
      ok "把人生导师请进来了"
    else
      die "缺少 roles-模板/人生导师.md"
    fi
  fi

  title "照镜子"
  say "${C_DIM}不给建议，不下判断。只把你自己说过的话摆到你面前。${C_OFF}"
  rule

  local q
  q="$(printf '%s\n' \
    "读 docs/00-听到的.md 里他说的原话，还有他后面补充的回答。" \
    "" \
    "照你的规矩做一次镜子，写进 $MIRROR_FILE。" \
    "" \
    "**再说一遍那条死规矩**：每一句关于他的话，必须能指回他自己说过的原话。" \
    "「你其实是……」这五个字一次都不许出现。" \
    "" \
    "第二节【只问一个问题】，给具体场景，不问抽象动机。" )"

  local rc=0
  NO_GROUP_CHAT=1 ROLE_ISOLATED=1 ask_role 人生导师 "$q" "$LISTEN_FILE" || rc=$?
  [ "$rc" -eq 3 ] && return 0
  if [ "$rc" -ne 0 ]; then report_failure "$rc" "照镜子的时候出错了"; return $?; fi

  if [ ! -f "$MIRROR_FILE" ]; then
    rule
    warn "没产出 $(basename "$MIRROR_FILE")，按没做成处理。"
    return 1
  fi

  rule
  ok "写在 ${C_BOLD}${MIRROR_FILE#"$ROOT/"}${C_OFF}"
  say ""
  say "${C_DIM}想接着聊：./loop.sh ask 人生导师 \"你的话\"${C_OFF}"
  say "${C_DIM}聊完了回主线：./loop.sh go${C_OFF}"
  say ""
  say "${C_DIM}这一步是可选的，跳过不影响流程。${C_OFF}"
  return 0
}

# ---------- 论证：十个专家把「这事到底成不成」查一遍 ----------
#
# 分两轮，这是这条命令的核心设计：
#   先跑的四个【联网查】真实数据；后跑的六个【看着查回来的数据做判断】。
#
# 为什么不是十个人一起上：十个人各查各的，会得到十份互相打架的数字，
# 而且没有裁判。先查后判，判断的人是看着【同一份】真实数据在判断。
# 顺带还便宜——只有四个人要联网，联网那几次才是贵的。
LUN_ZHENG_FILE="$DOC_DIR/00-论证.md"
LZ_RESEARCH="${LZ_RESEARCH:-行研 增长 竞品 技术}"
LZ_JUDGE="${LZ_JUDGE:-财务 战略 产品 合规 运营 风控}"

lz_deliverable() { echo "$WORK_DIR/$1/论证.md"; }

# 跑一个专家。已经交过东西的跳过——预算中途用完了能接着跑，不用从头来。
lz_one() {
  local who="$1" round="$2"; shift 2
  local out; out="$(lz_deliverable "$who")"

  if [ -f "$out" ]; then
    say "  ${C_DIM}$who 已经交过了，跳过（想重跑就删掉 ${out#"$ROOT/"}）${C_OFF}"
    return 0
  fi
  if [ ! -f "$(role_file "$who")" ]; then
    warn "  「$who」不在岗，跳过。（招他：./loop.sh hire $who）"
    return 0
  fi

  mkdir -p "$(dirname "$out")"
  local q
  q="$(printf '%s\n' \
    "读 docs/00-论证.md 里的作业单，找到写着【$who】的那一节。" \
    "" \
    "**你只答那一个问题。别人的活不许碰**——十个人各答各的，重叠了就等于没分工。" \
    "" \
    "$( [ "$round" = 查 ] \
        && printf '%s' "你这一轮要【联网查真实数据】。查不到就写「查不到」，**绝对不许编**。每个数字必须带来源链接和日期。" \
        || printf '%s' "先跑的几个人已经把真实数据查回来了（在上面的上下文里）。你这一轮【不用联网】，看着他们查回来的数据做判断。" )" \
    "" \
    "把结果写进 **$out**，格式：" \
    "" \
    "## 我负责的问题" \
    "## 结论（一句话）" \
    "## 依据" \
    "　每条标 [事实|推断|猜测]。[事实] 必须有来源和日期，没有就降级成 [推断]。" \
    "## 对应哪几条承重条件" \
    "　写编号，并给出每条应该标成：已验证 / 未验证 / 已证伪" \
    "## 我这份里最靠不住的一点" \
    "　必写。一份看不出哪儿靠不住的意见书，是危险，不是专业。" )"

  info "  $who …"
  local rc=0
  NO_GROUP_CHAT=1 ROLE_ISOLATED=1 ROLE_CWD="$WORK_DIR/$who" \
    ask_role "$who" "$q" "$@" >/dev/null 2>&1 || rc=$?

  # 「跑过」不等于「交了东西」。文件不在就是没交，不许记成功。
  if [ -f "$out" ]; then
    ok "  $who 交了"
    group_say "$who" "$(head -25 "$out")"
  else
    warn "  $who 没交东西（退出码 $rc）"
    local b; b="$(blocker_reason "$LAST_LOG" || true)"
    [ -n "$b" ] && { say "  ${C_DIM}${b#*	}${C_OFF}"; return 2; }
  fi
  return 0
}

cmd_argue() {
  [ -f "$DOC_DIR/00-目标.md" ] || die "得先有目标草案。跑 ./loop.sh go 把第2步跑出来。"

  local missing=""
  local who
  for who in $LZ_RESEARCH $LZ_JUDGE; do
    [ -f "$(role_file "$who")" ] || missing="$missing $who"
  done
  if [ -n "$missing" ]; then
    rule
    warn "论证团还差人：$missing"
    say  "先招齐：${C_BOLD}./loop.sh hire$missing${C_OFF}"
    say  ""
    say  "${C_DIM}这一步是十个专家把「这事到底成不成」查一遍，人不齐就有盲区。${C_OFF}"
    rule
    return 1
  fi

  local b; b="$(budget_get)"
  if [ -z "$b" ]; then
    warn "这一步会调用十几次 AI，是这套东西里最贵的一步。"
    say  "先设个上限：${C_BOLD}./loop.sh budget 30${C_OFF}　${C_DIM}（到顶会自动停，已经交的不会白跑）${C_OFF}"
    return 1
  fi

  local start; start="$(cost_total)"

  # ── 一、CEO 出作业单 ────────────────────────────────
  if [ ! -f "$LUN_ZHENG_FILE" ]; then
    title "论证 · 第一步：CEO 把议题拆成十个不重叠的窄问题"
    rule
    local rc=0
    claude_run "$CMD_DIR/论证作业单.md" \
      "$DOC_DIR/00-听到的.md" "$DOC_DIR/00-目标.md" || rc=$?
    [ "$rc" -eq 3 ] && return 0
    [ "$rc" -ne 0 ] && { report_failure "$rc" "出作业单的时候出错了"; return $?; }
    [ -f "$LUN_ZHENG_FILE" ] || {
      warn "没产出 $(basename "$LUN_ZHENG_FILE")，按没做成处理。"; return 1; }
    ok "作业单出来了：${LUN_ZHENG_FILE#"$ROOT/"}"
  else
    say "${C_DIM}作业单已经有了，接着往下跑。${C_OFF}"
  fi

  local ctx=("$DOC_DIR/00-目标.md" "$LUN_ZHENG_FILE")
  [ -f "$DOC_DIR/00-听到的.md" ] && ctx=("$DOC_DIR/00-听到的.md" "${ctx[@]}")

  # ── 二、先跑：联网查真实数据 ────────────────────────
  rule
  title "论证 · 第二步：四个人去查真实数据（这几次要联网，是贵的那部分）"
  for who in $LZ_RESEARCH; do
    lz_one "$who" 查 "${ctx[@]}" || { warn "停在这儿了。恢复之后再跑一次 ./loop.sh 论证"; return 2; }
  done

  # ── 三、后跑：看着查回来的数据做判断 ────────────────
  rule
  title "论证 · 第三步：六个人看着这些数据做判断（不联网，便宜）"
  local jctx=("${ctx[@]}")
  for who in $LZ_RESEARCH; do
    local d; d="$(lz_deliverable "$who")"
    [ -f "$d" ] && jctx+=("$d")
  done
  for who in $LZ_JUDGE; do
    lz_one "$who" 判 "${jctx[@]}" || { warn "停在这儿了。恢复之后再跑一次 ./loop.sh 论证"; return 2; }
  done

  # ── 四、CEO 综合，算可行性 ──────────────────────────
  rule
  title "论证 · 第四步：CEO 综合十份意见，算可行性"
  local actx=("${jctx[@]}")
  for who in $LZ_JUDGE; do
    local d; d="$(lz_deliverable "$who")"
    [ -f "$d" ] && actx+=("$d")
  done
  local rc=0
  claude_run "$CMD_DIR/论证综合.md" "${actx[@]}" || rc=$?
  [ "$rc" -eq 3 ] && return 0
  [ "$rc" -ne 0 ] && { report_failure "$rc" "综合的时候出错了"; return $?; }

  # ── 五、把一页纸打给他看 ────────────────────────────
  rule
  local page; page="$(lz_onepager)"
  if [ -n "$page" ]; then
    printf '%s\n' "$page"
  else
    warn "没找到「给你的一页纸」那一节，完整的在 ${LUN_ZHENG_FILE#"$ROOT/"}"
  fi
  rule
  local endc; endc="$(cost_total)"
  say "这一轮花了 ${C_BOLD}\$$(awk -v a="$start" -v b="$endc" 'BEGIN{printf "%.2f", b-a}')${C_OFF}"
  say "完整的十份意见：${C_BOLD}work/<名字>/论证.md${C_OFF}　汇总：${C_BOLD}${LUN_ZHENG_FILE#"$ROOT/"}${C_OFF}"
  say ""
  say "${C_DIM}想重跑某个人：删掉他那份 work/<名字>/论证.md，再跑一次 ./loop.sh 论证${C_OFF}"
  return 0
}

# 把「给你的一页纸」那一节摘出来。问题和结论在文档中间，不摘的话人得自己翻。
lz_onepager() {
  [ -f "$LUN_ZHENG_FILE" ] || return 0
  awk '/^##[[:space:]]*给你的一页纸/ { on=1 }
       on && /^##[[:space:]]*承重条件核对表/ { exit }
       on { print }' "$LUN_ZHENG_FILE" 2>/dev/null
}

# 看看现在都有哪些角色，各自聊过几次
cmd_roles() {
  local rs; rs="$(roles_list)"
  if [ -z "$rs" ]; then
    title "还没有任何角色"
    say "角色是操盘手按项目需要招的。先跑 ${C_BOLD}./loop.sh ceo${C_OFF}，"
    say "它会看这个项目反复在哪儿出问题，然后决定需要哪几个专门盯那件事的人。"
    return 0
  fi
  title "现在有这些角色"
  local r n
  while IFS= read -r r; do
    [ -z "$r" ] && continue
    n="$(find "$LOG_DIR/roles/$r" -name '*.log' 2>/dev/null | wc -l | tr -d ' ')"
    printf '  %s%-16s%s 聊过 %s 次\n' "$C_BOLD" "$r" "$C_OFF" "${n:-0}"
    # 角色定义的第一行非空行，就是他管什么
    sed -n '/^[^#[:space:]]/{p;q}' "$(role_file "$r")" 2>/dev/null | sed 's/^/      /'
  done <<< "$rs"
  say ""
  say "问某个人：${C_BOLD}./loop.sh ask <名字> \"你的问题\"${C_OFF}"
  say "聊天记录：${C_BOLD}docs/10-会议记录.md${C_OFF}　完整日志：.loop/log/roles/<名字>/"
}

# 问某个角色一件事。每个角色有自己的对话线程，接着上次聊。
cmd_ask() {
  local role="${1:-}" question="${2:-}"
  [ -n "$role" ] || die "用法：./loop.sh ask <角色> \"问题\"（有哪些角色跑 ./loop.sh roles）"
  [ -f "$(role_file "$role")" ] || {
    warn "没有「$role」这个角色。"
    say  "现有的：$(roles_list | tr '\n' ' ')"
    say  "招人是操盘手的活：./loop.sh ceo"
    exit 1
  }
  [ -n "$question" ] || die "要问什么？用法：./loop.sh ask $role \"你的问题\""

  title "问「$role」"
  say "${C_DIM}$question${C_OFF}"
  rule

  # 只给这个角色该看的那几份，不是全塞。
  # 全塞的代价实测过：问一句话 $2.76，因为 8 份文档每次重新载入。
  local ctx=(); local d
  while IFS= read -r d; do [ -n "$d" ] && ctx+=("$d"); done < <(role_context "$role")

  # 问题先进群聊，再让角色跑。
  # 反过来的话有两个毛病：群聊里问答顺序是乱的；
  # 而且角色看不见"我正被问什么"，只能靠提示词里那一份。
  group_say "你 → @$role" "$question"

  local rc=0
  ask_role "$role" "$question" "${ctx[@]+"${ctx[@]}"}" || rc=$?
  [ "$rc" -eq 3 ] && return 0
  if [ "$rc" -ne 0 ]; then report_failure "$rc" "问「$role」的时候出错了"; return $?; fi

  # 回答进群聊——这样别的角色下次说话前就看得见
  group_say "$role" "$(tail -60 "$LAST_LOG" 2>/dev/null)"

  ok "已进群聊 ${C_BOLD}docs/10-群聊.md${C_OFF}（完整对话在 ${LAST_LOG#"$ROOT/"}）"
}

# 内置操盘手：看数、裁决、组队、问责
#
# 跟专家席是两个角色，别混：专家各自给判断、可以互相矛盾；
# 操盘手必须在矛盾之后拍板，并对数字负责。
# 把选择题原样丢回去是参谋的活——这个命令要先给决定，再让人点头或推翻。
cmd_ceo() {
  [ -f "$CMD_DIR/ceo.md" ] || die "缺少 .claude/commands/ceo.md"

  local ctx=() s d
  for s in "${STAGES[@]}"; do
    d="$(stage_doc "$s")"
    [ -n "$d" ] && [ -f "$d" ] && ctx+=("$d")
  done
  [ -f "$DOC_DIR/08-每天.md" ]     && ctx+=("$DOC_DIR/08-每天.md")
  [ -f "$DOC_DIR/09-操盘记录.md" ] && ctx+=("$DOC_DIR/09-操盘记录.md")

  if [ "${#ctx[@]}" -eq 0 ]; then
    die "还没有任何文档，操盘手没东西可看。先跑 ./loop.sh start \"你想做什么\""
  fi
  claude_run "$CMD_DIR/ceo.md" "${ctx[@]}" || true
}

# 每天用：今天做哪几件事，顺便看昨天到底动了没有
#
# 为什么要有这个命令：清单排完之后最常见的死法不是做错，是没做。
# 每天都很忙，一个月过去清单上一个钩都没多，而且这个死法从内部完全看不出来——
# 每天都在推进感里，只有把日子摊开数钩才看得见。
cmd_daily() {
  [ -f "$CMD_DIR/daily.md" ] || die "缺少 .claude/commands/daily.md"
  [ -f "$TASKS_FILE" ] || die "还没有任务清单，先把流程跑到第9步「任务清单」（./loop.sh go）"

  local ctx=()
  [ -f "$DOC_DIR/00-目标.md" ]    && ctx+=("$DOC_DIR/00-目标.md")
  [ -f "$STANDARDS_FILE" ]        && ctx+=("$STANDARDS_FILE")
  ctx+=("$TASKS_FILE")
  [ -f "$DOC_DIR/08-每天.md" ]    && ctx+=("$DOC_DIR/08-每天.md")

  claude_run "$CMD_DIR/daily.md" "${ctx[@]}" || true
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

# 上一次跑过东西没有？看状态和产出，不看有没有目录——
# 空目录到处都是（mkdir -p 建的），有目录不等于跑过。
had_run() {
  [ -f "$STATE_DIR/stage" ] && return 0
  [ -f "$STATE_DIR/原始想法.txt" ] && return 0
  ls "$DOC_DIR"/0*.md >/dev/null 2>&1 && return 0
  return 1
}

# 把上一次的东西整个挪走，一个文件都不删。
#
# 为什么必须【挪走】而不是留着：留在原地的旧文档会让后面的步骤
# 以为"这步已经做过了"直接跳过，而且 run_stage 会把它们当上下文
# 喂给 AI——于是你分析一个新想法，它手里拿着的是上一个项目的材料。
# 这个坑 2026-08-19 真出过：.loop/ran_giants=yes ＋ docs/ 里躺着
# MoneyLoop 自己的竞品调研，任何新想法一进来，第2、3步都是"已完成"。
#
# 【钥匙不许跟着挪走】：.loop/接口/ 里是 API key，
# 换个项目不该让你重配一次钥匙。
archive_run() {
  had_run || return 1
  local tag; tag="$(head -c 24 "$STATE_DIR/原始想法.txt" 2>/dev/null | tr -d '\n/' || true)"
  local bak="$ROOT/.loop-backup-$(date +%Y%m%d-%H%M%S)${tag:+-$tag}"
  mkdir -p "$bak"

  # 钥匙先端出来
  local keys=""
  if [ -d "$STATE_DIR/接口" ]; then
    keys="$(mktemp -d)"; cp -r "$STATE_DIR/接口" "$keys/" 2>/dev/null || true
  fi

  [ -d "$STATE_DIR" ] && mv "$STATE_DIR" "$bak/" 2>/dev/null || true
  [ -d "$DOC_DIR" ]   && mv "$DOC_DIR"   "$bak/" 2>/dev/null || true

  # 钥匙放回去
  if [ -n "$keys" ] && [ -d "$keys/接口" ]; then
    mkdir -p "$STATE_DIR"; cp -r "$keys/接口" "$STATE_DIR/" 2>/dev/null || true
    rm -rf "$keys"
    say "${C_DIM}接口钥匙留在原处，没跟着挪走。${C_OFF}"
  fi
  ARCHIVED_TO="$bak"
  return 0
}

cmd_reset() {
  if archive_run; then
    ok "旧的东西都挪到了 $ARCHIVED_TO（没删，随时能翻出来）"
  fi
  rm -rf "$STATE_DIR/stage" "$STATE_DIR"/ran_* "$STATE_DIR"/signoff_* 2>/dev/null || true
  ok "已重置。跑 ./loop.sh start \"你的想法\" 重新开始。"
}

cmd_help() {
  cat <<'EOF'
自动化流水线 —— 从一个模糊想法，到一个能用的东西

  ./loop.sh start "你想做什么"   开始（一句话说清就行，不用想得多完整）
  ./loop.sh 答 "1A 2C ..."       回答第1步问你的那几个问题
  ./loop.sh 听 "任何一段话"       单独用：只把一段话拆开听懂，不开项目
  ./loop.sh 面板                 打开那个能点的界面（浏览器里，只有你能开）
  ./loop.sh 试金石 "任何一段话"    三条腿(同模型跑两次量噪声底 + 换个模型)，
                                   报「它自己差几句 / 换脑子差几句」；
                                   净信号不为正、或全票一致，都会报警（各花 3 次调用）
  ./loop.sh go                   继续往下跑
  ./loop.sh status               看进度（终端）
  ./loop.sh 看板                 生成桌面看板：组织图＋群聊＋台账＋账单，双击就开
  ./loop.sh today                每天用：今天做哪 3 件事，顺便看这周到底动了没有
  ./loop.sh ceo                  内置操盘手：看数、拍板、组队、问一句还到不到得了目标
  ./loop.sh budget 50            设花钱上限（美元）。不设就不给跑自动
  ./loop.sh auto                 无人值守：自己往下跑，撞到闸门/预算/卡点就停
  ./loop.sh hire [名字...]       从模板招人（不写名字就看有哪些可招）
  ./loop.sh 专家团               CEO 定这个项目缺哪几块判断、要找什么样的专家
  ./loop.sh 行业报告 "议题"       行业专家照 CEO 的设计去找人，一人一份落盘
  ./loop.sh 蒸馏                 把报告里的真专家做成能单独提问的智能体
  ./loop.sh 专家群 "议题"        让蒸馏出来的专家依次发言，后面的能反驳前面的
  ./loop.sh 封存 <名字>          用完收起来（不删，随时 ./loop.sh 起复）
  ./loop.sh 蓝图                 画产品蓝图：形态/功能/技术/时间表，一直改到你说「就是它了」
  ./loop.sh 改 "A"               回答蓝图的问题，或者说哪儿不对
  ./loop.sh 定了                 对，这就是我要做的（蓝图锁定）
  ./loop.sh 启蒙                 四位大师（美学/哲学/历史人文/精神意识）拧出几个方向，细到按钮
  ./loop.sh 审美                 给你看真东西，从你的选择里反推出你的审美标准
  ./loop.sh 手册                 一步一步带你做出来，含所有要花钱的点
  ./loop.sh 上线                 上线前最后一关：三道闸 + CEO 拍板 + 接管运营
  ./loop.sh 止损 "到6月..."      定止损线（一个日期 + 一个可数的事实）
  ./loop.sh 记账 收 500 "第一单"  记收支，日报和仪表盘都读它
  ./loop.sh 日报                 上线之后每天一份，你只看这个
  ./loop.sh 照镜子               动手之前，先看清你到底想要什么（只用你自己的话当镜子）
  ./loop.sh 论证                 十个专家把「这事到底成不成」查一遍，给可行性判定
  ./loop.sh 会诊 "议题"          CEO 判断该问谁 → 逐个咨询 → 综合裁决
  ./loop.sh 派单                 执行总监把 CEO 的决策拆成每个人的活
  ./loop.sh 排班                 执行总监定今天每个员工做什么
  ./loop.sh 派活 <角色> "任务"    单独派一件活给某个人
  ./loop.sh 验收                 CEO 把干完的活逐个看一遍，判行不行
  ./loop.sh 台账                 谁手上有什么活、干完没有、验收没有
  ./loop.sh say "话"             在群里说一句，所有角色下次开口前都会看到
  ./loop.sh cost                 花了多少钱、哪一步最贵
  ./loop.sh 接口                 每个员工用谁家的 AI（可以一人一家，互不影响）
  ./loop.sh 接口 客服 deepseek    把某个员工换成 DeepSeek；换整层写「执行层」
  ./loop.sh 接口 测 客服          真打一次，验证这个员工的接口通不通
  ./loop.sh roles                看看现在有哪些角色，各自聊过几次
  ./loop.sh ask <角色> "问题"     单独问某个人。每个人有自己的对话线程，接着上次聊
  ./loop.sh explain              用大白话讲一遍现在什么情况

  ./loop.sh judge                它给了个东西，我不知道好不好 → 它逼问自己，给你选择题
  ./loop.sh correct              感觉哪儿不对 → 先查错在哪一层，再决定怎么改

  ./loop.sh back                 上一步方向就不对，退回去重做
  ./loop.sh close                结项：封存 + 写一份诚实的复盘
  ./loop.sh reset                全部清空重来（先自动备份）

流程：
   1 听懂   把你那段话拆开：哪句承重、真痛点是什么  ← 你拍板
   2 目标   把想法变成能落地的目标 ＋ 倒推算账
   3 巨人   把前人做到最好的全扒出来、找现成轮子、挖信息差
   4 独特   共性守什么、独特赌什么                  ← 你拍板
   5 标准   定义什么叫「做得好」                    ← 你拍板
   6 需求   拆成具体要做的东西                      ← 你拍板
   7 补课   找出你不知道的事并讲明白
   8 选型   在哪落地、用什么、多少钱                ← 你拍板
   9 计划   排成可勾选的任务清单
  10 开做   做→检查→修，自动循环到全部通过

只有标着「你拍板」的五步会停下来等你，其余全自动。
这四步都是生意问题，不是技术问题——只有你能定。

可调开关（环境变量）：
  MAX_BUILD_ROUNDS=30   第9步最多循环几轮
  MAX_FIX_TRIES=3       一个任务最多自动修几次
  CLAUDE_BIN=claude     claude 命令的路径
EOF
}

# ============================================================
# ============================================================
# 夜班 · 赛马
#
# 为什么是赛马而不是"一个项目往下推"：
# 这套东西真正的瓶颈不是 token，是老板早上的判断带宽。
# 一晚上烧一百块换二百页文档，那是作业不是产出。
# 所以夜里的活必须是【自己淘汰】——早上他只做一个动作：砍。
# 完整设计见 references/夜班.md
#
# 关键约束：夜里只做可逆的事（想、查、写、算）。
# 花生意的钱／对外发东西／不可逆操作，一条都不碰。
# ============================================================

RACE_DIR="$ROOT/赛马"
IDEA_BOX="$RACE_DIR/想法箱.tsv"
RACE_LOG="$RACE_DIR/台账.tsv"

race_init() {
  mkdir -p "$RACE_DIR"
  [ -f "$IDEA_BOX" ] || printf '编号\t一句话\t状态\t建于\n' > "$IDEA_BOX"
  [ -f "$RACE_LOG" ] || printf '时间\t编号\t干了什么\t退出码\t这一轮花了\t停在哪一步\n' > "$RACE_LOG"
}

# 想法箱里所有编号（不含表头）
race_ids() { [ -f "$IDEA_BOX" ] && awk -F'\t' 'NR>1 && $1!="" {print $1}' "$IDEA_BOX" || true; }

race_field() {  # race_field <编号> <第几列>
  [ -f "$IDEA_BOX" ] || return 0
  awk -F'\t' -v id="$1" -v c="$2" 'NR>1 && $1==id {print $c; exit}' "$IDEA_BOX"
}

race_set_status() {  # race_set_status <编号> <新状态>
  local tmp; tmp="$(mktemp)"
  awk -F'\t' -v OFS='\t' -v id="$1" -v st="$2" \
    'NR==1 {print; next} $1==id {$3=st} {print}' "$IDEA_BOX" > "$tmp"
  mv "$tmp" "$IDEA_BOX"
}

race_dir_of() { printf '%s/%s' "$RACE_DIR" "$1"; }

# 这个想法自己花了多少（各想法的账本是分开的）
race_cost() {
  local f; f="$(race_dir_of "$1")/.loop/cost.tsv"
  [ -f "$f" ] || { echo 0; return; }
  awk -F'\t' 'NR>1 && $3!="" { t += $3 } END { printf "%.2f", t+0 }' "$f"
}

race_stage() {
  local f; f="$(race_dir_of "$1")/.loop/stage"
  [ -f "$f" ] && cat "$f" || echo 听懂
}

# 可行性：从这个想法的文档里捞一个百分数。捞不到就是「还没算出来」。
# 这是个尽力而为的读数，不是断言——所以它在战报里标着「文档里写的」。
race_feasibility() {
  local d; d="$(race_dir_of "$1")/docs"
  [ -d "$d" ] || { echo "—"; return; }
  local v
  v="$(grep -rhoE '可行性[^0-9]{0,8}([0-9]{1,3})%' "$d" 2>/dev/null | grep -oE '[0-9]{1,3}%' | tail -1 || true)"
  [ -n "$v" ] && echo "$v" || echo "—"
}

race_rounds() { state_file_int "$(race_dir_of "$1")/.loop/夜班轮次"; }
state_file_int() { [ -f "$1" ] && cat "$1" || echo 0; }

cmd_idea() {   # 想法 "一句话"
  local one="${1:-}"
  [ -n "$one" ] || die '用法：./loop.sh 想法 "一句话说清楚你想做什么"'
  race_init

  local id n=1
  while :; do
    id="$(printf '%03d' "$n")"
    [ -d "$RACE_DIR/$id" ] || break
    n=$((n+1))
  done

  local d="$RACE_DIR/$id"
  mkdir -p "$d/docs" "$d/.loop"

  # 参考资料、规矩、提示词共用仓库那一份。
  # 【不许拷贝】——拷贝了就会各自漂，改一处忘一处，正是规矩三骂的那件事。
  ln -sfn "$ROOT/references" "$d/references"
  ln -sfn "$ROOT/.claude"    "$d/.claude"
  ln -sfn "$ROOT/CLAUDE.md"  "$d/CLAUDE.md"

  printf '%s\n' "$one" > "$d/.loop/原始想法.txt"
  printf '听懂'          > "$d/.loop/stage"
  printf '%s\t%s\t%s\t%s\n' "$id" "$one" 在跑 "$(date +%F)" >> "$IDEA_BOX"

  ok "收进想法箱：[$id] $one"
  say "${C_DIM}现在不花钱，它在队列里等着。夜里跑：${C_OFF}${C_BOLD}./loop.sh 夜班${C_OFF}"
}

# 挑下一个该跑谁：跑过轮数最少的那个「在跑」的想法。
# 为什么是最少的：赛马要公平——不能让第一个想法把整晚吃光，
# 那就退化成"一个项目挖到底"了。
race_pick() {
  local best="" bestn=999999 id st n
  for id in $(race_ids); do
    st="$(race_field "$id" 3)"
    [ "$st" = "在跑" ] || continue
    n="$(race_rounds "$id")"
    if [ "$n" -lt "$bestn" ]; then bestn="$n"; best="$id"; fi
  done
  printf '%s' "$best"
}

cmd_night() {   # 夜班 [跑几小时，默认 8]
  race_init
  local hours="${1:-8}"
  case "$hours" in ''|*[!0-9]*) die '用法：./loop.sh 夜班 [跑几小时，默认 8]' ;; esac

  local live; live="$(race_ids | wc -l | tr -d ' ')"
  if [ "$live" -eq 0 ]; then
    rule
    warn "想法箱是空的，没活可干。"
    say  "先丢几个想法进去：${C_BOLD}./loop.sh 想法 \"一句话\"${C_OFF}"
    say  "${C_DIM}赛马要 5~10 个才有意思——只有一个的话，那不叫赛马，叫深挖。${C_OFF}"
    rule
    return 1
  fi

  # 停机条件之一：地基是红的就不许生产。
  # 不拦的话，一整晚的产出全建立在一个坏掉的系统上，而且每一步看着都是 ✓。
  # LOOP_NIGHT_CHECK 存在的唯一理由是【让这道闸门本身可测】：
  # 自测要能同时验"绿了才放行"和"红了真的拦住"，就得能换一把假尺子进来。
  # 不许拿它当绕过闸门的开关——绕过去等于把这道闸门删了。
  if ! bash "${LOOP_NIGHT_CHECK:-$ROOT/scripts/check.sh}" >/dev/null 2>&1; then
    rule
    warn "自检没过，今晚不跑。"
    say  "先跑 ${C_BOLD}bash scripts/check.sh${C_OFF} 看哪儿红了。"
    say  "${C_DIM}在坏地基上生产一整晚，等于一整晚白烧。${C_OFF}"
    rule
    return 1
  fi

  local deadline=$(( $(date +%s) + hours * 3600 ))
  local maxr="${LOOP_NIGHT_MAX:-200}"
  local n=0 id rc cur now before after

  rule
  title "夜班开始 · $(date '+%m-%d %H:%M')"
  say "  想法箱里 $live 个，最多跑 $hours 小时 / $maxr 轮"
  say "${C_DIM}  撞到下面任何一条就停：到点 ／ 轮数到顶 ／ 预算到顶 ／ 所有想法都在等你${C_OFF}"
  rule

  while :; do
    [ "$(date +%s)" -ge "$deadline" ] && { info "到点了，收工。"; break; }
    [ "$n" -ge "$maxr" ] && { info "跑满 $maxr 轮，收工。"; break; }
    budget_ok || break

    id="$(race_pick)"
    [ -n "$id" ] || { info "所有想法都停下等你了，收工。"; break; }

    n=$((n+1))
    local d; d="$(race_dir_of "$id")"
    before="$(race_stage "$id")"
    local c0; c0="$(race_cost "$id")"

    printf '\n%s第 %d 轮 · [%s] %s（现在在：%s）%s\n' \
      "$C_DIM" "$n" "$id" "$(race_field "$id" 2)" "$(stage_label "$before")" "$C_OFF"

    rc=0
    ( cd "$d" && LOOP_HOME="$PWD" "$ROOT/loop.sh" go ) || rc=$?
    after="$(race_stage "$id")"

    local c1 spent
    c1="$(race_cost "$id")"
    spent="$(awk -v a="$c1" -v b="$c0" 'BEGIN{printf "%.2f", a-b}')"
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$(date '+%F %H:%M')" "$id" "推进" "$rc" "$spent" "$after" >> "$RACE_LOG"

    printf '%s' "$(( $(race_rounds "$id") + 1 ))" > "$d/.loop/夜班轮次"

    case "$rc" in
      2) race_set_status "$id" "等你"
         say "${C_DIM}  [$id] 停下等你拍板，先放一边，换下一个。${C_OFF}" ;;
      3) race_set_status "$id" "等你"
         say "${C_DIM}  [$id] 跑不动（没装 claude），先放一边。${C_OFF}" ;;
      0) if [ "$after" = "$before" ]; then
           # 阶段没动。跑了一轮却原地不动，再跑一轮多半还是一样，别空转。
           race_set_status "$id" "等你"
           say "${C_DIM}  [$id] 这一轮没往前动，先放一边。${C_OFF}"
         fi
         [ "$after" = "done" ] && race_set_status "$id" "跑完了" ;;
      4) break ;;   # 预算闸门
      *) race_set_status "$id" "卡住"
         say "${C_DIM}  [$id] 卡住了（退出码 $rc），先放一边。${C_OFF}" ;;
    esac
  done

  rule
  say "夜班结束，跑了 $n 轮。战报："
  cmd_morning
}

cmd_morning() {   # 战报 · 早上那一页
  race_init
  local ids; ids="$(race_ids)"
  if [ -z "$ids" ]; then warn "想法箱是空的。"; return 0; fi

  local total=0 id
  for id in $ids; do
    total="$(awk -v a="$total" -v b="$(race_cost "$id")" 'BEGIN{printf "%.2f", a+b}')"
  done

  local rounds=0
  [ -f "$RACE_LOG" ] && rounds="$(awk 'NR>1' "$RACE_LOG" | wc -l | tr -d ' ')"

  rule
  title "战报 · $(date '+%m-%d %H:%M')"
  say "  累计跑了 $rounds 轮，花了 \$$total"
  rule
  printf '%s  %s %s %s %s%s\n' "$C_DIM" \
    "$(pad 编号 6)" "$(pad 状态 10)" "$(pad 可行性 8)" "$(pad 跑到 8)" "$C_OFF"

  for id in $ids; do
    printf '  %s %s %s %s %s\n' \
      "$(pad "$id" 6)" \
      "$(pad "$(race_field "$id" 3)" 10)" \
      "$(pad "$(race_feasibility "$id")" 8)" \
      "$(pad "第$(stage_num "$(race_stage "$id")")步" 8)" \
      "$(race_field "$id" 2)"
  done

  rule
  # 注意这个 || true：for 循环最后一轮的 [ ] 判假会返回 1，
  # 配上 set -e 会把整个战报从这儿掐断——这个坑这项目栽过好几次了。
  local waiting; waiting="$(for id in $ids; do
    [ "$(race_field "$id" 3)" = "等你" ] && echo "$id"; done | tr '\n' ' ' || true)"

  if [ -n "$waiting" ]; then
    title "要你拍板的"
    for id in $waiting; do
      say "  ${C_BOLD}[$id]${C_OFF} $(race_field "$id" 2)"
      say "${C_DIM}     它停在「$(stage_label "$(race_stage "$id")")」。看它问了什么：${C_OFF}"
      say "${C_DIM}     cd 赛马/$id && LOOP_HOME=\"\$PWD\" $ROOT/loop.sh status${C_OFF}"
    done
    rule
  fi

  say "你早上只做一个动作：${C_BOLD}砍${C_OFF}。"
  say "${C_DIM}  砍掉：./loop.sh 砍 003      留下继续跑：./loop.sh 留 003${C_OFF}"
  say "${C_DIM}  砍比批准快十倍，而且砍错了看得出来，批准错了看不出来。${C_OFF}"
  rule
}

cmd_kill_idea() {
  local id="${1:-}"; [ -n "$id" ] || die '用法：./loop.sh 砍 <编号>'
  [ -d "$(race_dir_of "$id")" ] || die "没有这个编号：$id"
  race_set_status "$id" "淘汰"
  ok "[$id] 淘汰了。东西还在 赛马/$id/ 里，随时能翻，但夜班不再跑它。"
}

cmd_keep_idea() {
  local id="${1:-}"; [ -n "$id" ] || die '用法：./loop.sh 留 <编号>'
  [ -d "$(race_dir_of "$id")" ] || die "没有这个编号：$id"
  race_set_status "$id" "在跑"
  ok "[$id] 放回跑道，今晚接着跑。"
}

main() {
  local sub="${1:-help}"; shift || true
  case "$sub" in
    start)   cmd_start "${1:-}" ;;
    answer|答|回答) cmd_answer "${1:-}" ;;
    listen|听) cmd_listen_once "${1:-}" ;;
    touchstone|试金石) cmd_touchstone "${1:-}" ;;
    go|next|continue) cmd_go ;;
    status|st) cmd_status ;;
    ceo|操盘) cmd_ceo ;;
    industry|行业报告) cmd_industry "${1:-}" ;;
    board|看板) cmd_board_html ;;
    ui|面板|界面) cmd_panel ;;
    design|专家团) cmd_panel_design ;;
    distill|蒸馏) cmd_distill ;;
    panel|专家群) cmd_expert_panel "${1:-}" ;;
    archive|封存) cmd_archive_role "${1:-}" ;;
    unarchive|起复) cmd_unarchive_role "${1:-}" ;;
    council|会诊) cmd_council "${1:-}" ;;
    dispatch|派单) cmd_dispatch ;;
    roster|排班) cmd_roster ;;
    assign|派活) cmd_assign "${1:-}" "${2:-}" ;;
    review|验收) cmd_review ;;
    ledger|台账) cmd_board ;;
    launch|上线) cmd_launch ;;
    stoploss|止损) cmd_stoploss "${1:-}" ;;
    account|记账) cmd_ledger "${1:-}" "${2:-}" "${3:-}" ;;
    report|日报) cmd_daily_report ;;
    enlighten|启蒙) cmd_enlighten ;;
    aesthetic|审美) cmd_aesthetic ;;
    manual|手册|落地手册) cmd_manual ;;
    blueprint|蓝图) cmd_blueprint ;;
    revise|改) cmd_blueprint_answer "${1:-}" ;;
    lock|定了) cmd_blueprint_lock ;;
    mirror|照镜子) cmd_mirror ;;
    argue|论证) cmd_argue ;;
    provider|接口|换脑子) cmd_provider "${1:-}" "${2:-}" "${3:-}" ;;
    auto|自动) cmd_auto ;;
    idea|想法) cmd_idea "${1:-}" ;;
    night|夜班) cmd_night "${1:-}" ;;
    morning|战报) cmd_morning ;;
    kill|砍) cmd_kill_idea "${1:-}" ;;
    keep|留) cmd_keep_idea "${1:-}" ;;
    budget|预算) cmd_budget "${1:-}" ;;
    close|结项) cmd_close ;;
    hire|招人) shift 0; cmd_hire "$@" ;;
    say|说) cmd_say "${1:-}" ;;
    cost|花钱|账) cmd_cost ;;
    roles|角色) cmd_roles ;;
    ask|问)  cmd_ask "${1:-}" "${2:-}" ;;
    today|daily|今天) cmd_daily ;;
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
