# scripts/状态.py 的自测（这个文件此前覆盖为零，这次补上）。
#
# 状态.py 把 .loop/ 读成一个字典，看板（静态 HTML）和面板都靠它。
# 它的失败方式是静默的：net 算错、少读一步、清单跟 lib.sh 漂了——
# 屏幕上照样出数，你不知道那是错的。所以这里喂造好的状态，断言它算出来的数。
#
# 想亲眼看它会红：BREAK=1 python -m pytest tests/test_状态.py
#   会加载一个被做了手脚的 状态.py 副本（把 net=收-支 改成 收+支），
#   证明这套测试真的会因为"算错"而变红——不是只会绿。
#   （做手脚只发生在临时副本上，仓库里的 scripts/状态.py 一个字都不动。）

import importlib.util
import os
import pathlib
import subprocess
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
SRC = REPO / "scripts" / "状态.py"


def load_status():
    """加载被测的 状态.py。BREAK 时加载一个故意算错 net 的副本。"""
    src = SRC.read_text(encoding="utf-8")
    if os.environ.get("BREAK"):
        broken = src.replace("net=round(inc - exp, 2)", "net=round(inc + exp, 2)")
        assert broken != src, "BREAK 没生效：没找到 net 那一行，源码结构变了？"
        src = broken
    d = tempfile.mkdtemp()
    p = os.path.join(d, "status_under_test.py")
    pathlib.Path(p).write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("status_under_test", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _loop(tmp):
    L = os.path.join(tmp, ".loop")
    os.makedirs(os.path.join(L, "roles"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "docs"), exist_ok=True)
    return L


def _w(path, text):
    pathlib.Path(path).write_text(text, encoding="utf-8")


def test_账本_收支净额():
    # 账本.tsv 的收/支要被正确加总，净额 = 收 - 支。
    ST = load_status()
    tmp = tempfile.mkdtemp()
    L = _loop(tmp)
    _w(os.path.join(L, "stage"), "goal")
    _w(os.path.join(L, "账本.tsv"),
       "日期\t收支\t金额\t说明\n"
       "2026-08-01\t收\t500\t第一单\n"
       "2026-08-02\t支\t30\t服务器\n")
    s = ST.read_all(tmp)
    assert s["income"] == 500.0
    assert s["outgo"] == 30.0
    assert s["net"] == 470.0   # BREAK 时会算成 530.0 → 这条变红


def test_止损线_读得出():
    ST = load_status()
    tmp = tempfile.mkdtemp()
    L = _loop(tmp)
    txt = "到6月底还没有10个付费用户就停"
    _w(os.path.join(L, "止损线"), txt)
    s = ST.read_all(tmp)
    assert s["stoploss"] == txt


def test_进度_stage_index():
    # 听懂=0, goal=1, giants=2, edge=3, taste=4
    ST = load_status()
    tmp = tempfile.mkdtemp()
    L = _loop(tmp)
    _w(os.path.join(L, "stage"), "taste")
    s = ST.read_all(tmp)
    assert s["stage"] == "taste"
    assert s["stage_index"] == 4


def test_十步清单不跟_libsh_漂移():
    # 状态.py 的 STAGES 是从 lib.sh 抄来的，抄的会漂。逐项对着 lib.sh 比。
    ST = load_status()
    r = subprocess.run(
        ["bash", "-c", '. "$1/scripts/lib.sh"; printf "%s\\n" "${STAGES[@]}"', "_", str(REPO)],
        capture_output=True, text=True, cwd=str(REPO))
    want = r.stdout.split()
    got = [k for k, _ in ST.STAGES]
    assert want, "没能从 lib.sh 读到 STAGES"
    assert want == got, "十步清单漂了：lib.sh=%s 状态.py=%s" % (want, got)
