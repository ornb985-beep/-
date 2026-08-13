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

# 中英混排的表格对齐。
#
# printf 的 %-12s 是按【字节】补空格的，一个汉字 3 字节但只占 2 格，
# 所以只要一列里同时有中文和英文，表格必歪。这个函数按【显示宽度】补。
#
# 算法：设总字节 B、其中 ASCII 字节 A，则汉字个数 =(B-A)/3，
# 显示宽度 = A + 2*(B-A)/3。（表情符号是 4 字节，会略微算偏，
# 角色名里没有表情，够用。）
pad() {
  local s="$1" want="${2:-0}" b a w i
  b=$(printf '%s' "$s" | LC_ALL=C wc -c)
  a=$(printf '%s' "$s" | LC_ALL=C tr -cd '\000-\177' | LC_ALL=C wc -c)
  w=$(( a + 2 * (b - a) / 3 ))
  printf '%s' "$s"
  for ((i=w; i<want; i++)); do printf ' '; done
}

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

# 「什么算好」的文件。双回路转没转，看它末尾那张「标准修订记录」表。
STANDARDS_FILE="$DOC_DIR/03-什么算好.md"

# 标准修订记录里有几条真实记录（表头和分隔线不算，空行不算）。
#
# 为什么要数这个：「标准会随证据修订」是这套东西跟所有同类工具唯一的区别——
# 别人都在做「东西符不符合标准」，没人做「标准本身是不是定错了」。
# 说明书里写死了：每做完一个任务必须回头问一句「有没有哪条标准要改」，
# 改了记一笔，没改也记一笔「看过，没改」。
#
# 但真跑五轮下来，那张表一行都没有，连"看过没改"都没有，
# 而整个 loop.sh 里零处检查这件事。规矩写了 ≠ 规矩执行了。
# 它悄悄没执行，这套东西唯一的差异化就是空的——而且从外面完全看不出来。
revisions_count() {
  [ -f "$STANDARDS_FILE" ] || { echo 0; return; }
  awk '
    /^##[[:space:]]*标准修订记录/ { on=1; next }
    on && /^##[[:space:]]/ { exit }
    on && /^[[:space:]]*\|/ {
      rows++
      if (rows <= 2) next          # 第1行表头、第2行分隔线，都不算
      t=$0; gsub(/[|[:space:]-]/,"",t)
      if (t != "") n++
    }
    END { print n+0 }
  ' "$STANDARDS_FILE"
}

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

# ---------- 花了多少钱 ----------
#
# 为什么要记这个：这套东西两次撞上额度上限、白烧 5 次重试，
# 而在此之前它对自己花了多少钱【零可见性】。
# 更要命的是不均匀——实测一句"说好"就花了 $1.17，
# 因为整个项目上下文每次都要重新载进去。
# 不记账的话，你只会在撞上限的那一刻才知道，而那时候已经晚了。
COST_LOG="$STATE_DIR/cost.tsv"

# 解析 JSON 用什么。两个都没有就退回纯文本模式，不记账但照常能跑——
# 这是模板，不能因为别人机器上没装 jq 就不能用。
json_parser() {
  if command -v jq >/dev/null 2>&1; then echo jq
  elif command -v python3 >/dev/null 2>&1; then echo python3
  else echo ""; fi
}

# json_field <json文件> <字段名> —— 取一个顶层字段，取不到返回空
json_field() {
  local f="$1" k="$2"
  case "$(json_parser)" in
    jq)      jq -r --arg k "$k" '.[$k] // empty' < "$f" 2>/dev/null ;;
    python3) python3 -c "
import json,sys
try:
    v=json.load(open(sys.argv[1])).get(sys.argv[2])
    if v is not None: print(v)
except Exception: pass
" "$f" "$k" 2>/dev/null ;;
    *) : ;;
  esac
}

cost_total() {
  [ -f "$COST_LOG" ] || { echo 0; return; }
  awk -F'\t' 'NR>1 && $3!="" { t += $3 } END { printf "%.2f", t+0 }' "$COST_LOG"
}

# 预算闸门。
#
# 为什么必须有：实测一次调用 $0.68~$8.20。
# 没有闸门就开无人值守，等于装了个不封顶的水龙头——
# 一晚上能烧掉几百刀，而你睡着了。
#
# 闸门只拦「还没花的」，不会把已经花的退回来，所以要设在你真能接受的数上。
budget_get() { state_get budget "${LOOP_BUDGET:-}"; }

# 还能不能再花。能就返回 0，不能就打印原因并返回 1。
budget_ok() {
  local b; b="$(budget_get)"
  [ -z "$b" ] && return 0            # 没设预算就不拦，但 auto 模式会强制要求设
  local spent; spent="$(cost_total)"
  # 用 awk 比大小，bash 不会算小数
  if awk -v s="$spent" -v b="$b" 'BEGIN{exit !(s>=b)}'; then
    rule
    warn "到预算上限了，停下。"
    say  "  已经花了 \$$spent，你设的上限是 \$$b。"
    say  ""
    say  "想继续就调高上限：${C_BOLD}./loop.sh budget <新的数>${C_OFF}"
    say  "先看看钱花哪了：${C_BOLD}./loop.sh cost${C_OFF}"
    rule
    return 1
  fi
  return 0
}

cost_record() {
  local what="$1" cost="$2" ms="$3"
  mkdir -p "$STATE_DIR"
  [ -f "$COST_LOG" ] || printf '时间\t干什么\t花了(美元)\t用时(秒)\t接口\n' > "$COST_LOG"
  # 第5列记「这一笔走的谁家接口」。
  #
  # 为什么必须记：这个美元数是 claude 自己按【官方价目表】算出来的。
  # 走别家接口（比如 DeepSeek）时，它照样会报一个数，但那个数是错的——
  # 它不知道别家收多少钱。不标出来的话，账面上会凭空冒出一笔假账。
  printf '%s\t%s\t%s\t%s\t%s\n' \
    "$(date '+%Y-%m-%d %H:%M')" "$what" "${cost:-0}" "$(( ${ms:-0} / 1000 ))" \
    "${LOOP_PROVIDER:-官方}" >> "$COST_LOG"
}

# ---------- 角色（操盘手 / 专家 / CEO 招的人）----------
#
# 每个角色是一个独立的对话线程：自己的会话、自己的日志、自己的记录。
#
# 为什么要分开：一个脑子里同时装着获客、合规、成本，三件事都想得很浅。
# 分开之后每个角色只盯一件事，视角不互相污染。
#
# 两条是实测出来的，不是设想的：
#   1. --session-id 钉住会话，下次 -r 接着说，它确实记得上次说过什么。
#   2. 但 --append-system-prompt 立不住角色身份——CLAUDE.md 分量太重会盖过它。
#      所以角色身份必须写在提示词正文里，每次都带上。
ROLE_DIR="$STATE_DIR/roles"

# 群聊：所有角色都读、都写的那一个文件，你也在里面。
#
# 为什么必须有：没有它，21 个角色只是 21 个互不相干的对话——
# 每个人都只知道自己说过什么，不知道别人说了什么，
# 那不叫组织，叫二十一个独立顾问。
#
# 为什么是文件不是飞书：这套东西是你机器上的一个脚本，没有常驻服务。
# 接飞书要注册应用、拿凭证、开一个一直跑着的进程收 webhook——那是另一个项目。
# 而「他们能互相交流、我能看见并指挥」这件事，一个共享文件就能成立。
# 飞书只是把这个文件换个更好看的显示界面，不是换个机制。
GROUP_CHAT="$DOC_DIR/10-群聊.md"
MEETING_LOG="$GROUP_CHAT"     # 兼容旧名字

# 群聊最近的 N 行，喂给角色当上下文——这样他们才看得见别人说了什么
GROUP_CHAT_TAIL="${GROUP_CHAT_TAIL:-120}"

group_chat_init() {
  [ -f "$GROUP_CHAT" ] && return 0
  mkdir -p "$DOC_DIR"
  cat > "$GROUP_CHAT" <<'MD'
# 10 · 群聊

> 这里是所有角色和你共处的一个地方。
> **每个角色说话前都会先看这里最近的内容**，所以他们看得见彼此说了什么。
>
> - 你说话：`./loop.sh say "你的话"`，或者直接在这个文件末尾打字
> - 问某个人：`./loop.sh ask <名字> "问题"`，问和答都会出现在这里
> - **只追加，不改写**——改过的记录看不出当时到底怎么想的，就没有价值了

MD
}

# 把群聊最近的内容抠出来，给角色当上下文
group_chat_recent() {
  [ -f "$GROUP_CHAT" ] || return 0
  local tmp="$STATE_DIR/群聊-最近.md"
  { printf '# 群聊最近的内容（你说话前先看一眼，别人可能已经说过了）\n\n'
    tail -n "$GROUP_CHAT_TAIL" "$GROUP_CHAT"; } > "$tmp"
  printf '%s' "$tmp"
}

# 往群聊里说一句话
group_say() {
  local who="$1" text="$2"
  group_chat_init
  { printf '\n**%s · %s**\n\n%s\n' "$(date '+%m-%d %H:%M')" "$who" "$text"; } >> "$GROUP_CHAT"
}

new_uuid() {
  if [ -r /proc/sys/kernel/random/uuid ]; then cat /proc/sys/kernel/random/uuid
  elif command -v uuidgen >/dev/null 2>&1; then uuidgen | tr 'A-Z' 'a-z'
  else printf '%s-%s-4%s-8%s-%s' \
    "$(od -An -tx1 -N4 /dev/urandom | tr -d ' \n')" \
    "$(od -An -tx1 -N2 /dev/urandom | tr -d ' \n')" \
    "$(od -An -tx1 -N2 /dev/urandom | tr -d ' \n' | cut -c2-4)" \
    "$(od -An -tx1 -N2 /dev/urandom | tr -d ' \n' | cut -c2-4)" \
    "$(od -An -tx1 -N6 /dev/urandom | tr -d ' \n')"
  fi
}

roles_list() {
  [ -d "$ROLE_DIR" ] || return 0
  find "$ROLE_DIR" -maxdepth 1 -name '*.md' -exec basename {} .md \; 2>/dev/null | sort
}

role_file()    { echo "$ROLE_DIR/$1.md"; }
role_session() { echo "$ROLE_DIR/$1.session"; }

# 这个角色用哪个模型。
#
# 这就是「以后接便宜 AI」的接口：在角色定义里写一行
#   模型：sonnet
# 就行。客服分拣、竞品巡查这种活用便宜的；
# CEO 裁决、风控反证这种活用最强的——**判断力省不得，体力活可以省。**
#
# 要接非官方的便宜服务，在 .loop/roles/<名字>.env 里写 endpoint 和 key，
# 那个文件会在调用这个角色时被 source 进去，只影响他一个人。
# ---------- 派活台账 ----------
#
# 每个角色有自己的工作区 work/<角色>/，交付物落在那儿，互不踩。
# 项目文档 docs/ 所有人只读——那是共同的事实基础，谁都不许偷偷改。
#
# 为什么要台账：光有「问答」不够。真干活是
#   派活 → 他自己去搜、去做 → 交付一个文件 → CEO 验收行不行。
# 没有台账就看不出「谁手上有什么活、干完没有、验收过没有」。
WORK_DIR="$ROOT/work"
TASK_LOG="$STATE_DIR/tasks.tsv"

role_workspace() { echo "$WORK_DIR/$1"; }

task_log_init() {
  mkdir -p "$STATE_DIR"
  [ -f "$TASK_LOG" ] || printf '编号\t派给谁\t干什么\t状态\t交付物\t时间\n' > "$TASK_LOG"
}

# task_add <角色> <任务> <交付物路径> —— 返回编号
task_add() {
  task_log_init
  local n; n="$(( $(wc -l < "$TASK_LOG") ))"   # 表头占一行，所以这就是新编号
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$n" "$1" "$2" "派了" "$3" "$(date '+%m-%d %H:%M')" >> "$TASK_LOG"
  echo "$n"
}

task_set_state() {
  local id="$1" st="$2"
  [ -f "$TASK_LOG" ] || return 0
  awk -F'\t' -v OFS='\t' -v id="$id" -v st="$st" \
    'NR==1||$1!=id{print;next}{$4=st;print}' "$TASK_LOG" > "$TASK_LOG.tmp" \
    && mv "$TASK_LOG.tmp" "$TASK_LOG"
}

# 等着验收的活（干完了但还没验收）
tasks_pending_review() {
  [ -f "$TASK_LOG" ] || return 0
  awk -F'\t' 'NR>1 && $4=="干完了"' "$TASK_LOG"
}

role_model() {
  local rf; rf="$(role_file "$1")"
  grep -m1 -E '^模型(:|：)' "$rf" 2>/dev/null | sed -E 's/^模型(:|：)[[:space:]]*//' || true
}
role_env() { echo "$ROLE_DIR/$1.env"; }

# 这个角色在哪一层（参谋 / 执行）。模板第一行写着「层：参谋」。
role_layer() {
  local rf; rf="$(role_file "$1")"
  grep -m1 -E '^层(:|：)' "$rf" 2>/dev/null | sed -E 's/^层(:|：)[[:space:]]*//' || true
}

# ---------- 接口：每个员工用谁家的脑子 ----------
#
# 一个员工 = 一个独立智能体 = 自己的会话 + 自己的工作目录 + 【自己的接口】。
# 这三样分开，是"21 个角色"和"一个人格分裂的 AI"的区别。
#
# 换脑子只改一个文件：.loop/roles/<名字>.env，只影响他一个人。
# 调用他的时候在【子 shell 里】source 进去，跑完就没了，不污染别人。
PROVIDER_DIR="$STATE_DIR/接口"

# 供应商清单：代号|显示名|接口地址|主力模型|快模型|查证日期|来源
#
# 铁律：这张表里只许写【查证过】的。凭印象加一家进来，
# 用户照着配一次配不通，这个功能就废了。
provider_row() {
  case "$1" in
    官方|anthropic|claude)
      echo "官方|Anthropic 官方|||||" ;;
    deepseek|深度求索|ds|deepseek-pro)
      echo "deepseek|DeepSeek V4-Pro|https://api.deepseek.com/anthropic|deepseek-v4-pro|deepseek-v4-flash|2026-08-13|api-docs.deepseek.com" ;;
    deepseek-flash|ds-flash|flash)
      echo "deepseek-flash|DeepSeek V4-Flash|https://api.deepseek.com/anthropic|deepseek-v4-flash|deepseek-v4-flash|2026-08-13|api-docs.deepseek.com" ;;
    *) return 1 ;;
  esac
}
# 表里没有这家（比如用户自己手写的 .env），就把代号原样还回去，
# 别返回空——空会让一览表里凭空少一行，看起来像"这个人没配"。
provider_field() {
  local r; r="$(provider_row "$1")" || { echo "$1"; return 0; }
  echo "$r" | cut -d'|' -f"$2"
}

# 把整张供应商表倒出来（面板要用）。
# 只有这一张表是真的，面板不许自己再抄一份——抄一份就会有一天两边对不上。
PROVIDERS_ALL="官方 deepseek deepseek-flash"
provider_dump() {
  local c
  for c in $PROVIDERS_ALL; do provider_row "$c"; done
}

# 同一家的不同型号共用一把钥匙（v4-pro 和 v4-flash 都是 DeepSeek 的）
provider_family() {
  case "$1" in
    deepseek*|ds*|flash|深度求索) echo deepseek ;;
    *) echo "$1" ;;
  esac
}
provider_keyfile() { echo "$PROVIDER_DIR/$(provider_family "$1").key"; }

# 这个员工现在用谁家的。没有 .env 就是官方。
role_provider() {
  local ef; ef="$(role_env "$1")"
  [ -f "$ef" ] || { echo 官方; return; }
  local p; p="$(grep -m1 '^LOOP_PROVIDER=' "$ef" 2>/dev/null | cut -d= -f2-)"
  echo "${p:-自定义}"
}

# 把某个员工切到某一家。钥匙单独存一份，不重复写进每个人的文件。
provider_apply() {
  local role="$1" code="$2"
  local row; row="$(provider_row "$code")" || return 1
  local name url big small verified
  name="$(echo "$row" | cut -d'|' -f2)"
  url="$(echo "$row"  | cut -d'|' -f3)"
  big="$(echo "$row"  | cut -d'|' -f4)"
  small="$(echo "$row"| cut -d'|' -f5)"
  verified="$(echo "$row" | cut -d'|' -f6)"
  code="$(echo "$row" | cut -d'|' -f1)"

  # 切回官方 = 把这个人的接口文件删掉，回到默认
  if [ -z "$url" ]; then rm -f "$(role_env "$role")"; return 0; fi

  local kf; kf="$(provider_keyfile "$code")"
  [ -f "$kf" ] || return 2          # 还没给钥匙，让上层去要

  mkdir -p "$ROLE_DIR"
  cat > "$(role_env "$role")" <<EOF
# 「$role」这个员工用：$name
# 只影响他一个人。这个文件在调用他的时候被 source 进子 shell，跑完就没了。
# 接口地址查证日期：$verified
LOOP_PROVIDER=$code
. "\$PROVIDER_DIR/$(provider_family "$code").key"
ANTHROPIC_BASE_URL=$url
ANTHROPIC_MODEL=$big
ANTHROPIC_DEFAULT_OPUS_MODEL=$big
ANTHROPIC_DEFAULT_SONNET_MODEL=$big
ANTHROPIC_DEFAULT_HAIKU_MODEL=$small
EOF
  return 0
}

# 存钥匙。单独一个文件、只有自己能读，别人的 .env 引用它。
#
# 为什么不直接写进每个人的 .env：十个员工就是十份钥匙拷贝，
# 换钥匙要改十个地方，漏一个就有一个人在用旧的。
provider_save_key() {
  local code="$1" key="$2"
  local fam; fam="$(provider_family "$code")"
  mkdir -p "$PROVIDER_DIR"
  local kf="$PROVIDER_DIR/$fam.key"
  cat > "$kf" <<EOF
ANTHROPIC_AUTH_TOKEN=$key
# 官方的 key 如果也在环境里，会跟这把打架，明确清掉
unset ANTHROPIC_API_KEY
EOF
  chmod 600 "$kf" 2>/dev/null || true
}

# 这个角色要看哪几份文档。
#
# 为什么不能全塞：实测问一个只管获客的角色一句话，花了 $2.76、81 秒——
# 因为把全部 8 份文档都塞给它了，包括跟它完全无关的「技术与落地」。
# 角色分工的意义是各看各的那一块，全塞进去等于分工白分。
#
# 角色定义文件里可以写一行「上下文：00-目标.md 02-共性与独特.md」来指定；
# 不写就用默认的三份（要什么 / 凭什么是我们 / 什么算好），够绝大多数角色用。
role_context() {
  local rf; rf="$(role_file "$1")"
  local line; line="$(grep -m1 -E '^上下文(:|：)' "$rf" 2>/dev/null | sed -E 's/^上下文(:|：)[[:space:]]*//')"
  [ -z "$line" ] && line="00-目标.md 02-共性与独特.md 03-什么算好.md"
  local f
  for f in $line; do
    [ -f "$DOC_DIR/$f" ] && printf '%s\n' "$DOC_DIR/$f"
  done
}

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

  # 角色的日志各自归各自的目录，方便按人回看整条对话
  local dir="$LOG_DIR${LOG_SUBDIR:+/$LOG_SUBDIR}"
  mkdir -p "$dir"
  local ts; ts="$(date +%Y%m%d-%H%M%S)"
  local logf="$dir/$ts-$(basename "$prompt_file" .md).log"
  # 出事的时候要回头翻这个日志，见 blocker_reason。
  #
  # 为什么还要多写一个文件：接了别家接口的角色，claude_run 是在【子 shell】里跑的
  # （因为要 source 他自己的 .env 又不能污染别人）。子 shell 里的赋值出不来，
  # LAST_LOG 在外面就是空的——于是"没通"能报出来，但"为什么没通"整段是空白。
  # 落一个文件，外面再捡回去，见 ask_role 结尾。
  LAST_LOG="$logf"
  state_set last_log "$logf"

  # 花钱之前先过预算闸门
  budget_ok || return 4

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
  local what; what="${LOG_SUBDIR:-$(basename "$prompt_file" .md)}"

  # 能解析 JSON 就走 json 模式，顺手把花了多少钱记下来；
  # 解析不了就退回纯文本，照常能跑，只是没有账。
  if [ -n "$(json_parser)" ]; then
    local raw="$logf.json"
    # ROLE_CWD：在指定目录里跑，而不是项目根目录。
    #
    # 为什么需要：项目根目录有 CLAUDE.md，它的分量压过一切提示词——
    # 实测让「行业专家」去做一份跟本项目无关的行业报告，
    # 它读完项目的 CLAUDE.md 和任务清单，跑去汇报项目进度、
    # 甚至去做项目的开发任务，连着两次都没交该交的报告。
    # 提示词里写"别管项目"没用，得让它根本不在那个目录里。
    # 这也正是「每个角色独立环境」真正该有的样子。
    # shellcheck disable=SC2086
    printf '%s' "$prompt" | ( [ -n "${ROLE_CWD:-}" ] && cd "$ROLE_CWD"; "$CLAUDE_BIN" -p \
        ${CLAUDE_EXTRA_ARGS[@]+"${CLAUDE_EXTRA_ARGS[@]}"} \
        --output-format json \
        --permission-mode acceptEdits \
        --allowedTools $LOOP_ALLOWED_TOOLS ) > "$raw" 2>"$logf.err"
    local rc="$?"

    # 正文照样打出来给人看，别为了记账就把人能看的东西弄没了
    local text; text="$(json_field "$raw" result)"
    if [ -n "$text" ]; then printf '%s\n' "$text" | tee "$logf"
    else cat "$logf.err" 2>/dev/null | tee "$logf"; fi

    cost_record "$what" "$(json_field "$raw" total_cost_usd)" "$(json_field "$raw" duration_ms)"
    return "$rc"
  fi

  # shellcheck disable=SC2086
  printf '%s' "$prompt" | "$CLAUDE_BIN" -p \
      ${CLAUDE_EXTRA_ARGS[@]+"${CLAUDE_EXTRA_ARGS[@]}"} \
      --permission-mode acceptEdits \
      --allowedTools $LOOP_ALLOWED_TOOLS 2>&1 | tee "$logf"
  return "${PIPESTATUS[1]}"
}

# 问某个角色一个问题。每个角色有自己的会话，接着上次聊。
# 用法：ask_role <角色名> <问题> [附加上下文文件...]
ask_role() {
  local role="$1" question="$2"; shift 2
  local rf; rf="$(role_file "$role")"
  [ -f "$rf" ] || { warn "没有这个角色：$role"; return 1; }

  # 群聊最近的内容也带上——不带的话，每个角色都只知道自己说过什么，
  # 那就不是一个组织，是二十一个互不相干的顾问。
  # NO_GROUP_CHAT=1 的活不喂群聊：像行业报告这种议题跟当前项目无关的，
  # 群聊里别的项目的事会把它带跑偏——实测它读完就去汇报别的项目进度了。
  if [ "${NO_GROUP_CHAT:-0}" != "1" ]; then
    local gc; gc="$(group_chat_recent)"
    [ -n "$gc" ] && set -- "$@" "$gc"
  fi

  local sf; sf="$(role_session "$role")"
  local tmp; tmp="$STATE_DIR/ask-$role.md"
  local -a CLAUDE_EXTRA_ARGS

  # ROLE_ISOLATED=1 → 这一次开全新会话，不接上次。
  #
  # 为什么要分两种：
  #   问答（ask）需要连续性——不连续就每次从头解释一遍。
  #   干活（派活）需要隔离——一件活是一个自包含的任务包，
  #   十件活堆在同一个会话里，会越干越贵，而且第一件活里的
  #   错误假设会一直粘着往后走（判断漂移）。
  #
  # 干活的持久化靠【产物】，不靠"记住"——交付物在文件里，
  # 下次要用就把文件读进来，比让它记着可靠得多。
  if [ "${ROLE_ISOLATED:-0}" = "1" ]; then
    local uuid; uuid="$(new_uuid)"
    CLAUDE_EXTRA_ARGS=(--session-id "$uuid")
    { cat "$rf"; printf '\n\n---- 现在问你这件事 ----\n%s\n' "$question"; } > "$tmp"
  elif [ -s "$sf" ]; then
    # 接着上次的对话。
    #
    # 这里只发一句身份提醒，不重发完整角色定义——实测过：
    # 每次重发完整定义，它会把那当成一条全新指令，于是重新推导出
    # 跟上次一模一样的回答，而不是接着往下推进。
    # 身份靠对话历史带着走就够了（"47"那个测试证明历史是在的）。
    CLAUDE_EXTRA_ARGS=(-r "$(cat "$sf")")
    { printf '（还是你，%s。接着上次说，不用从头重复立场。）\n\n' "$role"
      printf '%s\n' "$question"; } > "$tmp"
  else
    # 第一次：钉住会话，发完整角色定义。
    # 身份必须写在正文里——实测 --append-system-prompt 压不过 CLAUDE.md。
    local uuid; uuid="$(new_uuid)"
    printf '%s' "$uuid" > "$sf"
    CLAUDE_EXTRA_ARGS=(--session-id "$uuid")
    { cat "$rf"; printf '\n\n---- 现在问你这件事 ----\n%s\n' "$question"; } > "$tmp"
  fi

  # 这个角色自己的环境变量（接别家服务就写这儿），只影响他一个人
  local ef; ef="$(role_env "$role")"

  # 这个角色自己的模型（写在角色定义里的「模型：xxx」）。
  #
  # 接口文件里指定了模型就以接口为准——角色定义里那行是给官方用的，
  # 强行传 --model sonnet 给别家接口，等于点了一道人家菜单上没有的菜。
  local m; m="$(role_model "$role")"
  if [ -n "$m" ] && ! { [ -f "$ef" ] && grep -q '^ANTHROPIC_MODEL=' "$ef"; }; then
    CLAUDE_EXTRA_ARGS+=(--model "$m")
  fi

  if [ -f "$ef" ]; then
    # 在子 shell 里 source，跑完就没了，不污染别人——这是"每人一个接口"的关键。
    # 代价是子 shell 里的赋值出不来，所以 LAST_LOG 要从文件里捡回来。
    # shellcheck disable=SC1090
    ( set -a; . "$ef"; set +a
      LOG_SUBDIR="roles/$role" claude_run "$tmp" "$@" )
    local rc=$?
    LAST_LOG="$(state_get last_log)"
    return "$rc"
  fi

  LOG_SUBDIR="roles/$role" claude_run "$tmp" "$@"
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
