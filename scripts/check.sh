#!/usr/bin/env bash
# 「这东西还能正常跑吗」检查器。
#
# 关键点：这个模板一开始不知道你要用什么技术（第8步才定），
# 所以这里靠看有没有对应的文件来猜项目类型，猜到什么跑什么。
# 全部通过返回 0，任何一项失败返回 1。loop.sh 靠这个返回值决定要不要自动修。
#
# 想加自己的检查？在项目根目录建一个 check.local.sh，会在最后自动执行。

set -uo pipefail   # 注意：故意不加 -e，我们要跑完所有检查再汇总

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAILED=0
RAN=0

run() {
  local label="$1"; shift
  RAN=$((RAN+1))
  printf '\n=== %s ===\n' "$label"
  printf '$ %s\n' "$*"
  if "$@"; then
    printf '[通过] %s\n' "$label"
  else
    printf '[失败] %s\n' "$label"
    FAILED=1
  fi
}

# 只在命令存在时才跑，避免因为没装某个工具就误判为"代码有问题"
has() { command -v "$1" >/dev/null 2>&1; }

# 「本来该检查、但没能检查」要记下来，最后一起说。
# 不记的话就会出现最坏的情况：什么都没验，屏幕上却写着"全部通过"。
SKIPPED=()
skip() { SKIPPED+=("$1"); }

# 「已知失败」：写测试时撞出的真 bug——测试照写、照跑，但先不修（先修哪个由人定）。
# 这类失败【不算进通过判定】，但必须在末尾单独报出来，绝不许当没看见、更不许改绿。
KNOWN_FAIL=0
KNOWN_FAIL_NAMES=()
run_known() {
  local label="$1"; shift
  printf '\n=== [已知失败区] %s ===\n' "$label"
  printf '$ %s\n' "$*"
  if "$@"; then
    printf '[意外通过] %s —— 这条已知 bug 可能被修好了，回去确认再从已知失败区挪出来\n' "$label"
  else
    printf '[已知失败] %s（真 bug，已记录，暂不计入通过判定）\n' "$label"
    KNOWN_FAIL=$((KNOWN_FAIL+1)); KNOWN_FAIL_NAMES+=("$label")
  fi
}

# ---------------- Python ----------------
# 找 .py 要往下翻子目录。只看根目录的话，代码放在 src/ 里就完全看不见——
# 真跑的时候就是这样：src/unread.py + tests/test_unread.py 都在，
# check.sh 一个 Python 检查都没跑，还报了"全部通过"。
has_py=0
[ -f pyproject.toml ] || [ -f requirements.txt ] && has_py=1
if [ "$has_py" = 0 ] && [ -n "$(find . -name '*.py' -not -path '*/.*' -not -path '*/node_modules/*' -print -quit 2>/dev/null)" ]; then
  has_py=1
fi

if [ "$has_py" = 1 ]; then
  if has uv && [ -f pyproject.toml ]; then
    if uv run python -c "import pytest" 2>/dev/null; then
      run "Python 测试 (pytest)" uv run pytest -q
    else
      skip "Python 测试：没装 pytest（uv 环境里），测试没跑"
    fi
    uv run ruff --version >/dev/null 2>&1 && run "Python 代码规范 (ruff)" uv run ruff check .
  elif has pytest; then
    # 让 pytest 自己去找测试，别写死只看 tests/ 目录。
    # 退出码 5 = 一个测试都没收集到，那是"没测试可跑"，不是"测试挂了"。
    pytest -q; rc=$?
    RAN=$((RAN+1))
    printf '\n=== %s ===\n$ %s\n' "Python 测试 (pytest)" "pytest -q"
    case "$rc" in
      0) printf '[通过] Python 测试 (pytest)\n' ;;
      5) printf '[跳过] 有 Python 代码，但一个测试都没找到\n'
         RAN=$((RAN-1)); skip "Python 测试：有 .py 文件但没有任何测试，等于没验" ;;
      *) printf '[失败] Python 测试 (pytest)\n'; FAILED=1 ;;
    esac
  else
    skip "Python 测试：这台机器上没有 pytest 命令，测试没跑"
  fi
  has ruff && run "Python 代码规范 (ruff)" ruff check .
fi

# ---------------- Node / TypeScript ----------------
if [ -f package.json ]; then
  PM=npm
  [ -f pnpm-lock.yaml ] && has pnpm && PM=pnpm
  [ -f yarn.lock ] && has yarn && PM=yarn

  # 只跑 package.json 里真的定义了的脚本
  has_script() { node -e "process.exit(require('./package.json').scripts?.['$1']?0:1)" 2>/dev/null; }

  if has node; then
    has_script typecheck && run "类型检查" $PM run typecheck
    has_script lint      && run "代码规范"   $PM run lint
    has_script test      && run "测试"       $PM run test
    has_script build     && run "能否打包"   $PM run build
  fi
fi

# ---------------- Go ----------------
if [ -f go.mod ] && has go; then
  run "Go 编译" go build ./...
  run "Go 测试" go test ./...
fi

# ---------------- Rust ----------------
if [ -f Cargo.toml ] && has cargo; then
  run "Rust 编译" cargo build --quiet
  run "Rust 测试" cargo test --quiet
fi

# ---------------- Shell 脚本 ----------------
# 注意：git ls-files 在文件还没提交时会「成功地返回空」，不能靠 || 兜底，
# 必须看结果是不是空的，否则新项目里这段检查会静默失效。
list_shell_files() {
  local -a f=()
  if git rev-parse --git-dir >/dev/null 2>&1; then
    mapfile -t f < <(git ls-files '*.sh' 2>/dev/null)
  fi
  if [ "${#f[@]}" -eq 0 ]; then
    mapfile -t f < <(find . -name '*.sh' -not -path './.git/*' -not -path './node_modules/*' 2>/dev/null)
  fi
  printf '%s\n' "${f[@]+"${f[@]}"}"
}

mapfile -t SH < <(list_shell_files)
# find 在没结果时会产生一个空行，过滤掉
SH=("${SH[@]+"${SH[@]}"}")
FILTERED=()
for f in "${SH[@]+"${SH[@]}"}"; do [ -n "$f" ] && [ -f "$f" ] && FILTERED+=("$f"); done
SH=("${FILTERED[@]+"${FILTERED[@]}"}")

if [ "${#SH[@]}" -gt 0 ]; then
  has shellcheck && run "Shell 脚本检查" shellcheck "${SH[@]}"

  # 语法检查：不依赖任何外部工具，bash 自带
  RAN=$((RAN+1))
  printf '\n=== Shell 语法 ===\n'
  syn_ok=1
  for f in "${SH[@]}"; do
    bash -n "$f" || { printf '[失败] %s 语法有问题\n' "$f"; syn_ok=0; }
  done
  if [ "$syn_ok" = 1 ]; then printf '[通过] Shell 语法\n'; else FAILED=1; fi
fi

# ---------------- MoneyLoop 自己的检查 ----------------
# 「每个员工是不是真的一个独立接口」。
# 这条必须每次都跑：换接口最坏的失败方式不是报错，是【看起来换了其实没换】——
# 你以为在用便宜的，其实一直在烧贵的，而且账面上看不出来。
if [ -f scripts/test-接口.sh ]; then
  run "接口隔离（每个员工一个独立接口）" bash scripts/test-接口.sh
fi

# 第1步「听懂」。两头都要守住：没听懂却往下走了，和问个没完出不来。
# 顺带守住十步清单那三份拷贝不漂移。
if [ -f scripts/test-听懂.sh ]; then
  run "第1步 听懂（引导式问答 ＋ 十步清单不漂移）" bash scripts/test-听懂.sh
fi

# 论证：十个专家把「这事到底成不成」查一遍。
# 里面第一条测的是「角色到底收没收到自己的身份和问题」——
# 那条曾经悄悄坏了，每个角色只收到了自己定义的第一行。
if [ -f scripts/test-论证.sh ]; then
  run "论证（十个专家 ＋ 角色真收到了提示词）" bash scripts/test-论证.sh
fi

# 蓝图的收敛循环。最要紧的一条：它不许自己说"定了"——
# 拍板必须是用户亲口说的。它替你拍板，等于这整个循环白做。
if [ -f scripts/test-蓝图.sh ]; then
  run "蓝图收敛循环（改到你说就是它了）" bash scripts/test-蓝图.sh
fi

# 记账：钱的静默失败——屏幕说"记下了"，账本.tsv 却没落。日报和看板都读它。
if [ -f scripts/test-记账.sh ]; then
  run "记账（账本.tsv 真的落盘了）" bash scripts/test-记账.sh
fi

# 止损：止损线写丢了 = 永远不会喊停。这套系统存在的头号意义就在这条上。
if [ -f scripts/test-止损.sh ]; then
  run "止损（止损线真的写进去了）" bash scripts/test-止损.sh
fi

# 数字漂移：文档里写死的命令数是断言，必须和 loop.sh 实数一致。
# 断言性数字漂了不该靠"谁记得"，该被一条测试守住。
if [ -f scripts/test-数字漂移.sh ]; then
  run "数字漂移（文档命令数 vs loop.sh 实数）" bash scripts/test-数字漂移.sh
fi

# 对分歧：把两次「听懂」产出的差异数出来（漏判/判级差异/标记计数）。
# 这工具是核心一「分歧要被量出来」的第一块，它自己坏了还绿着，分歧就又变回手感。
if [ -f scripts/test-对分歧.sh ]; then
  run "对分歧（漏判/判级差异/标记,数出来不许靠手感）" bash scripts/test-对分歧.sh
fi

# ---------------- 已知失败区（撞到的真 bug，先记录、不修） ----------------
if [ -d scripts/known-fail ]; then
  for kf in scripts/known-fail/test-*.sh; do
    [ -f "$kf" ] || continue
    run_known "$(basename "$kf")" bash "$kf"
  done
fi

# ---------------- 项目自定义检查 ----------------
if [ -f check.local.sh ]; then
  run "项目自定义检查" bash check.local.sh
fi

# ---------------- 汇总 ----------------
printf '\n────────────────────────────\n'

# 先说没验成的。「全部通过」如果底下压着一堆没跑的检查，
# 那是最坏的一种假象——比直接失败还危险，因为你会以为它验过了。
# 所以现在：只要有"没验成"的，末行就不许写"全部通过"，而且 exit 非 0。
# 跳过不等于通过——这就是第 6 条。（缺 pytest、有 .py 却没测试，都算没验。）
NOTV="${#SKIPPED[@]}"
if [ "$NOTV" -gt 0 ]; then
  printf '有 %s 项【没验成】（跳过不等于通过，见第 6 条）：\n' "$NOTV"
  for s in "${SKIPPED[@]}"; do printf '  · %s\n' "$s"; done
  printf '\n'
fi

# 已知失败单独报，绝不混进"通过/没通过"里，也绝不许当没看见。
if [ "$KNOWN_FAIL" -gt 0 ]; then
  printf '已知失败 %s 条（真 bug，已记录、先不修，不计入通过判定）：\n' "$KNOWN_FAIL"
  for n in "${KNOWN_FAIL_NAMES[@]}"; do printf '  · %s\n' "$n"; done
  printf '\n'
fi

if [ "$RAN" -eq 0 ] && [ "$NOTV" -eq 0 ]; then
  printf '还没有任何可跑的检查（项目里还没有测试）。\n'
  printf '这不算失败，但等有代码了就该补测试了——没有测试，自动循环就没法判断做对没有。\n'
  exit 0
fi

if [ "$FAILED" -ne 0 ]; then
  printf '有检查没通过（跑了 %s 项，上面标着 [失败] 的就是）。\n' "$RAN"
  [ "$KNOWN_FAIL" -gt 0 ] && printf '（另有已知失败 %s 条，见上。）\n' "$KNOWN_FAIL"
  exit 1
fi

if [ "$NOTV" -gt 0 ]; then
  # 有没验成的：跑过的都过了，但没验成的那几项没绿，就不算全绿。
  printf '有 %s 项没验（见上）——跑过的 %s 项都过了，但没验成的不算通过。\n' "$NOTV" "$RAN"
  [ "$KNOWN_FAIL" -gt 0 ] && printf '（另有已知失败 %s 条。）\n' "$KNOWN_FAIL"
  exit 1
fi

printf '全部通过（共 %s 项检查）' "$RAN"
[ "$KNOWN_FAIL" -gt 0 ] && printf '；另有已知失败 %s 条（真 bug，已记录）' "$KNOWN_FAIL"
printf '\n'
exit 0
