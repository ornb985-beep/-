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

# ---------------- 项目自定义检查 ----------------
if [ -f check.local.sh ]; then
  run "项目自定义检查" bash check.local.sh
fi

# ---------------- 汇总 ----------------
printf '\n────────────────────────────\n'

# 先说没检查成的。「全部通过」如果底下压着一堆没跑的检查，
# 那是最坏的一种假象——比直接失败还危险，因为你会以为它验过了。
if [ "${#SKIPPED[@]}" -gt 0 ]; then
  printf '注意，下面这些本来该检查、但没检查成：\n'
  for s in "${SKIPPED[@]}"; do printf '  · %s\n' "$s"; done
  printf '\n'
fi

if [ "$RAN" -eq 0 ]; then
  printf '还没有任何可跑的检查（项目里还没有测试）。\n'
  printf '这不算失败，但等有代码了就该补测试了——没有测试，自动循环就没法判断做对没有。\n'
  exit 0
fi
if [ "$FAILED" -eq 0 ]; then
  printf '全部通过（共 %s 项检查）\n' "$RAN"
  exit 0
else
  printf '有检查没通过（共 %s 项）。上面标着 [失败] 的就是。\n' "$RAN"
  exit 1
fi
