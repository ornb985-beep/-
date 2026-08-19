#!/usr/bin/env python3
# MoneyLoop 面板：一个能点的界面，跑在你自己电脑上。
#
# 为什么是"本地网页"而不是真正的桌面软件：
#   桌面软件要给 Mac / Windows 各打一个包、要签名、要装。
#   本地网页零安装、零依赖（Python 自带的库就够）、断网能用，
#   而且你手机连同一个 Wi-Fi 也能看（如果你自己开了那个开关）。
#
# 它不是新做了一套东西——**所有活还是 loop.sh 干的**。
# 这层只做两件事：把状态显示出来、把你点的按钮翻译成一条 loop.sh 命令。
# 面板挂了，命令行照样能用；这是故意的。
#
# 安全上就三条（默认只听本机，等于只有你能碰）：
#   1. 只绑 127.0.0.1
#   2. 每次启动生成一把随机令牌，页面里带着，接口验它
#   3. 能跑哪些命令是【白名单】写死的，不是你传什么就跑什么

import os
import re
import sys
import json
import time
import uuid
import signal
import threading
import subprocess
import http.server
import socketserver
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import 状态 as ST  # noqa: E402

TOKEN = uuid.uuid4().hex
PAGE = os.path.join(HERE, "面板.html")

# ---------------------------------------------------------------
# 能跑哪些命令：白名单。
#
# 为什么写死：面板是个网页，网页上来的东西一律不可信。
# 允许"你传什么我跑什么"，等于在你电脑上开了一个远程执行的口子。
#
# reset 故意【不在】名单里——那条会清掉所有东西。
# 这种不可逆的事，值得你专门去终端敲一次，而不是手滑点到。
# ---------------------------------------------------------------
ALLOWED = {
    # 主流程
    "start":      1, "go": 0, "back": 0, "auto": 0,
    # 【最要紧的一条】答题。系统出一道选择题，你回一个 A——
    # 这是老板每天做得最多的动作，以前面板不认识它，只能找 AI 转手敲命令。
    "答":         1, "听": 1,
    # 蓝图这条线：画→改→定了
    "蓝图":       0, "改": 1, "定了": 0,
    # 看和想
    "status":     0, "explain": 0, "judge": 0, "correct": 0, "today": 0,
    "cost":       0, "roles": 0, "看板": 0, "日报": 0, "台账": 0,
    # CEO 和组织
    "ceo":        0, "hire": -1, "say": 1, "ask": 2, "会诊": 1,
    # 派活
    "派单":       0, "排班": 0, "派活": 2, "验收": 0,
    # 专家
    "专家团":     0, "行业报告": 1, "蒸馏": 0, "专家群": 1,
    "封存":       1, "起复": 1, "论证": 0,
    # 想清楚这一路
    "照镜子":     0, "启蒙": 0, "审美": 0, "手册": 0,
    # 试金石：两个脑子对跑，先量噪声底
    "试金石":     1,
    # 钱和接口
    "budget":     1, "接口": -1, "记账": 3, "止损": 1,
    # 夜班这一路
    "想法":       1, "夜班": 1, "战报": 0, "砍": 1, "留": 1,
}

# ---------------------------------------------------------------
# 故意【不在】名单里的，一条条都有理由：
#
#   reset  —— 清掉所有东西。不可逆的事值得你专门去终端敲一次，不是手滑点到
#   上线   —— 对外发布 ＝ 红线，永不下放
#   close  —— 结项，一个项目的句号，同上
#   help   —— 界面本身就是 help
#
# 加命令的时候先想一遍：这条会不会花生意的钱 / 对外发东西 / 不可逆？
# 三个里占一个，就不许上面板。
# ---------------------------------------------------------------

# 花钱的命令，界面上要把估价印在按钮上（第 8 条：钱永远可见）。
# 数字是 [推断]，按 2026-08-19 实测的 token 量推的，真数以 ./loop.sh cost 为准。
COST_HINT = {
    "start": "~$0.1–0.4", "go": "~$0.1–0.5", "听": "~$0.1–0.4",
    "答": "答完最后一题会重跑一轮 ~$0.1–0.4",
    "蓝图": "~$0.2–0.5", "改": "~$0.2–0.5",
    "试金石": "~$0.6–1.2（三条腿）",
    "论证": "~$3–8（十个专家，四个要联网）",
    "auto": "看预算闸门，撞线自动停",
    "夜班": "看预算闸门，撞线自动停",
}

# ---------------------------------------------------------------
# 一次只跑一件活。
#
# loop.sh 靠 .loop/ 下的文件记状态，两条命令同时跑会互相盖。
# 所以这里排队：正在跑就不让开第二个，界面上也会灰掉按钮。
# ---------------------------------------------------------------
class Job:
    def __init__(self):
        self.lock = threading.Lock()
        self.proc = None
        self.id = None
        self.cmd = ""
        self.buf = ""
        self.rc = None
        self.started = 0

    def busy(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self, argv):
        with self.lock:
            if self.busy():
                return None, "上一件还在跑（%s）。等它跑完，或者点「停」。" % self.cmd
            self.id = uuid.uuid4().hex[:12]
            self.cmd = " ".join(argv)
            self.buf = ""
            self.rc = None
            self.started = time.time()
            env = dict(os.environ)
            env["NO_COLOR"] = "1"
            env["TERM"] = "dumb"
            self.proc = subprocess.Popen(
                [os.path.join(ROOT, "loop.sh")] + argv,
                cwd=ROOT, env=env,
                stdin=subprocess.DEVNULL,      # 千万不能留 stdin：
                                               # 留着的话，命令里那句"贴 key"会一直等，界面就死在那儿
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, bufsize=1, errors="replace")
            threading.Thread(target=self._pump, daemon=True).start()
            return self.id, None

    def _pump(self):
        p = self.proc
        try:
            for line in p.stdout:
                self.buf += line
        except Exception:
            pass
        p.wait()
        self.rc = p.returncode

    def stop(self):
        if self.busy():
            try:
                self.proc.send_signal(signal.SIGINT)
                time.sleep(0.4)
                if self.busy():
                    self.proc.kill()
            except Exception:
                pass
            return True
        return False

    def snapshot(self, frm=0):
        return dict(id=self.id, cmd=self.cmd, running=self.busy(), rc=self.rc,
                    text=self.buf[frm:], total=len(self.buf),
                    secs=int(time.time() - self.started) if self.started else 0)

JOB = Job()

# 终端的颜色码在网页里是乱码，去掉
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

def clean(s):
    return ANSI.sub("", s)

def ask_now():
    """现在轮到答第几题、题面是什么、有哪几个选项。

    全部走 lib.sh，面板不自己解析文档——这条很重要：
    命令行和界面必须是同一套读法，否则两边会对同一份文档给出不同的答案。
    """
    def sh(script):
        try:
            r = subprocess.run(["bash", "-c",
                                'set -euo pipefail; ROOT=%s; . "$ROOT/scripts/lib.sh"; %s'
                                % (json.dumps(ROOT), script)],
                               cwd=ROOT, capture_output=True, text=True, timeout=10)
            return r.stdout.strip() if r.returncode == 0 else ""
        except Exception:
            return ""

    total = sh("listen_q_count") or "0"
    try:
        total = int(total)
    except ValueError:
        total = 0
    if total <= 0:
        return {"有题": False}

    done = sh("listen_answered") or "0"
    try:
        done = int(done)
    except ValueError:
        done = 0
    idx = done + 1
    if idx > total:
        return {"有题": False, "已答完": True, "共": total}

    raw = sh('listen_q_nth %d' % idx)
    lines = [ln.rstrip() for ln in raw.splitlines()]

    # 题面 = 「### 问题 N：____」那一行去掉前缀；选项 = 「- **A** ____」那些行
    title, opts = "", []
    for ln in lines:
        m = re.match(r"^###\s*问题\s*\d+\s*[：:]\s*(.*)$", ln)
        if m and not title:
            title = m.group(1).strip()
            continue
        m = re.match(r"^\s*-\s*\*\*([A-Z])\*\*\s*(.*)$", ln)
        if m:
            opts.append({"字母": m.group(1), "说的是": m.group(2).strip()})

    return {"有题": True, "第几题": idx, "共": total,
            "轮次": sh("listen_round") or "1",
            "题面": title, "选项": opts, "原文": raw}


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass          # 别把每个请求都打到终端上，吵

    # ---------- 小工具 ----------
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        # 网页上来的东西一律不可信，别让别的站点嵌进去
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def _auth(self):
        """令牌对不上就不给。防的是：你开着面板的时候，
        随便一个网页在后台偷偷调你本机的接口。"""
        t = self.headers.get("X-Token", "")
        if not t:
            q = urllib.parse.urlparse(self.path).query
            t = urllib.parse.parse_qs(q).get("token", [""])[0]
        if t != TOKEN:
            self._send(403, {"error": "令牌不对。把面板关了重开一次。"})
            return False
        return True

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        if n <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    # ---------- 路由 ----------
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        p = u.path

        if p == "/":
            try:
                with open(PAGE, encoding="utf-8") as f:
                    html = f.read()
            except OSError:
                return self._send(500, "找不到 scripts/面板.html", "text/plain; charset=utf-8")
            html = html.replace("__TOKEN__", TOKEN)
            return self._send(200, html, "text/html; charset=utf-8")

        if p == "/api/state":
            if not self._auth():
                return
            try:
                d = ST.read_all(ROOT)
            except Exception as ex:
                return self._send(500, {"error": "读状态出错：%s" % ex})
            d["job"] = JOB.snapshot(0) if JOB.id else None
            if d["job"]:
                d["job"]["text"] = clean(d["job"]["text"])[-4000:]
            return self._send(200, d)

        if p == "/api/job":
            if not self._auth():
                return
            q = urllib.parse.parse_qs(u.query)
            frm = int(q.get("from", ["0"])[0] or 0)
            s = JOB.snapshot(frm)
            s["text"] = clean(s["text"])
            return self._send(200, s)

        if p == "/api/ask":
            # 现在轮到你答哪一道题。只读，不花钱。
            #
            # 解析不自己写——lib.sh 里那三个函数(listen_q_count / listen_q_nth /
            # listen_answered)就是干这件事的，命令行和面板必须用同一套，
            # 不然哪天题目格式变了，两边会给出不同的答案，而且没人发现。
            if not self._auth():
                return
            return self._send(200, ask_now())

        if p == "/api/doc":
            if not self._auth():
                return
            q = urllib.parse.parse_qs(u.query)
            name = q.get("name", [""])[0]
            return self._send(200, {"name": name, "text": ST.doc_text(ROOT, name)})

        return self._send(404, {"error": "没有这个地址"})

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if not self._auth():
            return
        b = self._body()

        if u.path == "/api/run":
            cmd = str(b.get("cmd", ""))
            args = [str(x) for x in (b.get("args") or [])]
            if cmd not in ALLOWED:
                return self._send(400, {"error": "不认识的命令：%s" % cmd})
            want = ALLOWED[cmd]
            if want >= 0 and len(args) != want:
                return self._send(400, {"error": "「%s」要 %d 个参数，收到 %d 个"
                                                 % (cmd, want, len(args))})
            if any(a == "" for a in args):
                return self._send(400, {"error": "有一项没填"})
            jid, err = JOB.start([cmd] + args)
            if err:
                return self._send(409, {"error": err})
            return self._send(200, {"id": jid})

        if u.path == "/api/stop":
            return self._send(200, {"stopped": JOB.stop()})

        return self._send(404, {"error": "没有这个地址"})

class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

def main():
    port = int(os.environ.get("LOOP_PANEL_PORT", "7788"))
    # 默认只听本机 = 只有坐在这台电脑前的人能用。
    # 想让同一个 Wi-Fi 下的手机也能开，设 LOOP_PANEL_HOST=0.0.0.0，
    # 但那意味着同网段的人都能操作它，自己掂量。
    host = os.environ.get("LOOP_PANEL_HOST", "127.0.0.1")

    for attempt in range(20):
        try:
            srv = Server((host, port + attempt), Handler)
            port = port + attempt
            break
        except OSError:
            continue
    else:
        print("端口都被占着，换一个：LOOP_PANEL_PORT=8899 ./loop.sh 面板")
        return 1

    url = "http://%s:%d/?token=%s" % ("127.0.0.1" if host == "127.0.0.1" else host, port, TOKEN)
    print(url)
    sys.stdout.flush()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n面板关了。")
    return 0

if __name__ == "__main__":
    sys.exit(main())
