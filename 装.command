#!/bin/bash
# MoneyLoop 安装（macOS）· 双击这个文件就行
#
# 它干六件事，每一步都在屏幕上说人话：
#   1. 看 git / python3 在不在        4. 存 DeepSeek 钥匙（只存在你机器上）
#   2. 装 claude 命令（官方安装器）    5. 在桌面生成 MoneyLoop.app
#   3. 把代码拉到 ~/MoneyLoop         6. 跑一次自检，绿了才算装好
#
# 装好之后你就不用再管这个文件了，以后天天双击桌面那个 MoneyLoop.app。

set -uo pipefail
cd "$(dirname "$0")" 2>/dev/null || true

B=$'\033[1m'; D=$'\033[2m'; G=$'\033[32m'; R=$'\033[31m'; Y=$'\033[33m'; O=$'\033[0m'
say()  { printf '%s\n' "$*"; }
step() { printf '\n%s▸ %s%s\n' "$B" "$*" "$O"; }
ok()   { printf '%s  ✓ %s%s\n' "$G" "$*" "$O"; }
bad()  { printf '%s  ✗ %s%s\n' "$R" "$*" "$O"; }
warn() { printf '%s  ! %s%s\n' "$Y" "$*" "$O"; }
die()  { bad "$*"; say ""; say "装到这儿卡住了。把上面这些字截个图发给我，我看得出卡在哪。"; say ""; read -r -p "按回车关掉这个窗口。" _; exit 1; }

REPO_URL="https://github.com/ornb985-beep/-.git"
HOME_DIR="$HOME/MoneyLoop"
APP="$HOME/Desktop/MoneyLoop.app"

clear
say "${B}MoneyLoop 安装${O}"
say "${D}一路装完大概三五分钟。中途要你做的事只有一件：贴一次钥匙。${O}"

# ── 1. 基础工具 ──────────────────────────────────────────────
step "1/6　看看这台机器上有什么"

if ! command -v git >/dev/null 2>&1; then
  warn "没有 git。"
  say  "  这是苹果自带的开发工具，装一次就好。现在会弹一个框，点「安装」，装完再双击我一次。"
  xcode-select --install 2>/dev/null || true
  die "等那个框装完，再双击一次这个文件。"
fi
ok "git 有了"

if ! command -v python3 >/dev/null 2>&1; then
  warn "没有 python3。"
  say  "  跟上面一样，是苹果的开发工具带的。现在会弹框，点「安装」，装完再双击我一次。"
  xcode-select --install 2>/dev/null || true
  die "等那个框装完，再双击一次这个文件。"
fi
ok "python3 有了（$(python3 -V 2>&1)）"

# ── 2. claude 命令 ───────────────────────────────────────────
step "2/6　装 claude 命令（这套东西全靠它去思考）"

export PATH="$HOME/.local/bin:$PATH"
if command -v claude >/dev/null 2>&1; then
  ok "claude 已经装过了（$(command -v claude)）"
else
  say "  用官方安装器装。查证日期 2026-08-19，来源 code.claude.com/docs/en/setup"
  say "  ${D}Mac 上的这个程序由 Anthropic PBC 签名、经苹果公证，不是野路子。${O}"
  say ""
  if curl -fsSL https://claude.ai/install.sh | bash; then
    export PATH="$HOME/.local/bin:$PATH"
    command -v claude >/dev/null 2>&1 || die "装完了却找不到 claude 命令。把上面的输出发给我。"
    ok "claude 装好了（$(command -v claude)）"
  else
    die "claude 没装成。多半是网络问题，过一会儿再双击一次。"
  fi
fi

# 让以后开的终端也找得到它
for rc in "$HOME/.zshrc" "$HOME/.bash_profile"; do
  [ -f "$rc" ] || continue
  grep -q '.local/bin' "$rc" 2>/dev/null && continue
  printf '\n# MoneyLoop 装的时候加的\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$rc"
done

# ── 3. 代码 ──────────────────────────────────────────────────
step "3/6　把代码放到 $HOME_DIR"

if [ -d "$HOME_DIR/.git" ]; then
  say "  已经有了，拉一下最新的。"
  ( cd "$HOME_DIR" && git fetch --all --quiet && git checkout --quiet claude/project-template-automation-ea9utn 2>/dev/null && git pull --quiet ) \
    && ok "更新到最新" || warn "拉不下来（可能你本地改过东西），先用现有的往下走"
else
  # 仓库名就是一个减号。必须指定目标目录，否则会得到一个叫 - 的文件夹，
  # 而 cd - 在 shell 里是「回到上一个目录」——踩过这个坑。
  git clone --quiet "$REPO_URL" "$HOME_DIR" || die "代码拉不下来。看看网络。"
  ( cd "$HOME_DIR" && git checkout --quiet claude/project-template-automation-ea9utn ) \
    || die "切分支失败。"
  ok "拉下来了"
fi

# 认门：三条对不上就是拿错东西了
[ -f "$HOME_DIR/loop.sh" ] || die "拉下来的东西不对，没有 loop.sh。"
[ -f "$HOME_DIR/scripts/面板.py" ] || die "拉下来的东西不对，没有面板。"
chmod +x "$HOME_DIR/loop.sh" 2>/dev/null || true
ok "认门通过"

# ── 4. 钥匙 ──────────────────────────────────────────────────
step "4/6　DeepSeek 钥匙"

KEYDIR="$HOME_DIR/.loop/接口"
KEYFILE="$KEYDIR/deepseek.key"
mkdir -p "$KEYDIR"

if [ -s "$KEYFILE" ]; then
  ok "已经存过了（$KEYFILE）"
  say "  ${D}想换的话，删掉那个文件再双击我一次。${O}"
else
  say "  去 DeepSeek 后台新开一把钥匙，${B}给它设一个消费上限${O}，然后贴在下面。"
  say "  ${D}它只写在你这台电脑上，权限 600（只有你能读），而且 .loop/ 在忽略名单里，永远传不上去。${O}"
  say "  ${D}不想现在配就直接回车跳过——跳过的话「试金石」跑不了，别的照常。${O}"
  say ""
  printf "  钥匙（贴进来，看不见字是正常的）："
  read -r -s KEY
  say ""
  if [ -n "$KEY" ]; then
    printf 'ANTHROPIC_AUTH_TOKEN=%s\nunset ANTHROPIC_API_KEY\n' "$KEY" > "$KEYFILE"
    chmod 600 "$KEYFILE"
    unset KEY
    ok "存好了，权限 600"
  else
    warn "跳过了。以后想配，再双击一次这个文件。"
  fi
fi

# ── 5. 桌面那个 App ──────────────────────────────────────────
step "5/6　在桌面生成 MoneyLoop.app"

mkdir -p "$APP/Contents/MacOS"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>MoneyLoop</string>
  <key>CFBundleDisplayName</key><string>MoneyLoop</string>
  <key>CFBundleIdentifier</key><string>com.orbis.moneyloop</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>MoneyLoop</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>LSUIElement</key><true/>
</dict></plist>
PLIST

cat > "$APP/Contents/MacOS/MoneyLoop" <<'LAUNCH'
#!/bin/bash
# 双击桌面那个图标，跑的就是这个。
# 它只做三件事：进到代码目录、把面板起起来、打开浏览器。
# 面板挂了也不影响命令行——这是故意的。
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"
ROOT="$HOME/MoneyLoop"
LOG="$ROOT/.loop/面板.log"
PORT="${LOOP_PANEL_PORT:-7788}"

cd "$ROOT" 2>/dev/null || {
  osascript -e 'display alert "找不到 MoneyLoop" message "~/MoneyLoop 不见了。重新双击一次「装.command」就好。" as critical'
  exit 1
}
mkdir -p "$ROOT/.loop"

# 已经开着就不开第二个——直接把浏览器叫起来
if [ -f "$ROOT/.loop/面板.url" ] && lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  open "$(cat "$ROOT/.loop/面板.url")"
  exit 0
fi

# 起面板，把它打出来的第一行（带令牌的地址）捞出来
nohup python3 "$ROOT/scripts/面板.py" > "$LOG" 2>&1 &
for _ in $(seq 1 40); do
  URL="$(head -1 "$LOG" 2>/dev/null)"
  case "$URL" in http*) break ;; esac
  sleep 0.25
done

case "${URL:-}" in
  http*) printf '%s' "$URL" > "$ROOT/.loop/面板.url"; open "$URL" ;;
  *) osascript -e 'display alert "面板没起来" message "打开 ~/MoneyLoop/.loop/面板.log 看看，或者把它发给我。" as critical' ;;
esac
LAUNCH

chmod +x "$APP/Contents/MacOS/MoneyLoop"
# 这个 App 是在你机器上现生成的、不是从网上下载的，所以没有隔离标记——
# 不会弹「来自身份不明的开发者」那个框。保险起见再抹一次。
xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true
ok "桌面上有了：MoneyLoop.app"

# ── 6. 自检 ──────────────────────────────────────────────────
step "6/6　跑一次自检（没验成就不许说装好了）"

if ( cd "$HOME_DIR" && bash scripts/check.sh > /tmp/moneyloop-check.log 2>&1 ); then
  ok "$(tail -1 /tmp/moneyloop-check.log)"
  say ""
  say "${G}${B}装好了。${O}"
  say ""
  say "  以后每天：${B}双击桌面上的 MoneyLoop${O}"
  say "  代码在：  $HOME_DIR"
  say "  命令行也照样能用：${D}cd ~/MoneyLoop && ./loop.sh help${O}"
else
  bad "自检没过。"
  say ""
  tail -20 /tmp/moneyloop-check.log
  say ""
  say "${Y}东西装上了，但自检是红的——按第 2 条，跳过不等于通过，我不说它装好了。${O}"
  say "把上面这些发给我，我看得出是哪儿。"
fi

say ""
read -r -p "按回车关掉这个窗口。" _
