#!/usr/bin/env python3
"""对分歧:把「听懂」产出的差异变成数出来的东西,不许说"大致相同"。

用法:
    python3 scripts/对分歧.py 一份产出.log            # 单份:句子守恒 + 标记计数
    python3 scripts/对分歧.py A份.log B份.log         # 两份:守恒 + 判级差异 + 标记计数
产出从哪来:./loop.sh 听 跑完,日志在 .loop/log/*-听一次.log

只做三个检查(2026-08-18 定死,不许扩):
  一 句子守恒:原话里连续 ≥门槛 个字没被判级表任何一行覆盖 → 报「漏判」+片段
  二 判级差异:两份表逐句(锚回原话对齐)比 ★,报 相同/不同/一方缺失,只出数字和清单
  三 标记计数:[事实][推断][猜测] 各几次,两边差额

为什么不拿"行"对"行":同一段原话,两个模型的切分不一样
(真机见过 8 行对 9 行,一边合并一边拆),行对行会全乱。
原话是两次跑里唯一逐字相同的东西,所以两边的行各自先锚回原话,
锚上同一段的才算同一句。

已知的粗(先要粗的,别想做全):
  - 覆盖门槛 6 个字是拍的:模型常修剪引文句头(真机见过掐掉 5 字的「有人想让我」),
    门槛再低会把正常修剪误报成漏判;整句吞掉(真机见过 10 字的)抓得住。
  - 工具分不清「换个说法」和「整句吞掉」,漏判清单要人过目。
  - 标记计数抓不到「该标没标」,只能抓「标得少」。

退出码:0 干净 / 1 有漏判 / 2 解析不了(没找到原话或判级表,或有行锚不回原话)。
解析不了必须响,不许静默——跳过不等于通过。
"""
import re
import sys
from difflib import SequenceMatcher

门槛 = 6          # 连续几个字没被覆盖才算漏判
锚合格线 = 0.5    # 一行引文至少一半的字要能在原话里找到位置,否则算锚失败


def 洗(s: str) -> str:
    """只留中文和字母数字,去掉引号、标点、空白——两边风格不一才有这道洗。"""
    return re.sub(r'[^\w\u4e00-\u9fff]', '', s)


def 读产出(path: str):
    text = open(path, encoding='utf-8').read()
    m = re.search(r'原话[:：]\s*(.+)', text)
    if not m:
        print(f'解析不了:{path} 里没找到「原话:」那一行(退出码 2)')
        sys.exit(2)
    原话 = 洗(m.group(1))

    行 = []   # (引文原样, 引文洗过, ★数)
    表内 = False
    for line in text.splitlines():
        if line.lstrip().startswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) >= 4 and '轻重' in line:
                表内 = True
                continue
            if 表内 and cells and set(cells[0]) <= set('-— :'):
                continue
            if 表内 and len(cells) >= 4:
                星 = cells[3].count('★')
                if 星 > 0:
                    行.append((cells[1], 洗(cells[1]), 星))
        else:
            表内 = False
    if not 行:
        print(f'解析不了:{path} 里没找到带 ★ 的判级表(退出码 2)')
        sys.exit(2)
    return text, 原话, 行


def 锚(原话: str, 引文洗: str):
    """引文在原话里占哪些字。返回 (覆盖到的下标集合, 匹配率, 跨度)。"""
    blocks = [b for b in SequenceMatcher(None, 原话, 引文洗).get_matching_blocks() if b.size >= 2]
    盖 = set()
    for b in blocks:
        盖.update(range(b.a, b.a + b.size))
    率 = len(盖) / len(引文洗) if 引文洗 else 0
    跨 = (min(盖), max(盖) + 1) if 盖 else (0, 0)
    return 盖, 率, 跨


def 守恒(原话: str, 行, 标签: str):
    盖全 = set()
    锚不上 = []
    行带跨 = []   # (引文原样, ★数, 跨度)
    for 原样, 洗过, 星 in 行:
        盖, 率, 跨 = 锚(原话, 洗过)
        if 率 < 锚合格线:
            锚不上.append(原样)
        else:
            盖全 |= 盖
            行带跨.append((原样, 星, 跨))
    if 锚不上:
        print(f'解析不了:{标签} 里这些行的引文锚不回原话(退出码 2):')
        for x in 锚不上:
            print(f'  · {x}')
        sys.exit(2)

    漏 = []
    i = 0
    while i < len(原话):
        if i not in 盖全:
            j = i
            while j < len(原话) and j not in 盖全:
                j += 1
            if j - i >= 门槛:
                漏.append(原话[i:j])
            i = j
        else:
            i += 1
    return 漏, 行带跨


def 数标记(text: str):
    return {k: len(re.findall(re.escape(f'[{k}]'), text)) for k in ('事实', '推断', '猜测')}


def 重叠(a, b):
    起 = max(a[0], b[0])
    止 = min(a[1], b[1])
    交 = max(0, 止 - 起)
    短 = min(a[1] - a[0], b[1] - b[0])
    return 交 / 短 if 短 else 0


def main():
    档 = sys.argv[1:]
    if not 档 or len(档) > 2:
        print(__doc__)
        sys.exit(2)

    有漏 = False
    结果 = []
    for p in 档:
        text, 原话, 行 = 读产出(p)
        漏, 行带跨 = 守恒(原话, 行, p)
        结果.append((p, text, 原话, 行带跨, 漏))

    print(f'=== 对分歧:{"  对  ".join(档)} ===')
    print(f'\n【一 · 句子守恒】(连续 ≥{门槛} 字没被任何行覆盖才算漏;'
          f'工具分不清「换个说法」和「整句吞掉」,清单要人过目)')
    for p, _t, 原话, _r, 漏 in 结果:
        print(f'{p}:漏判 {len(漏)} 处')
        for x in 漏:
            print(f'  · 「{x}」')
        if 漏:
            有漏 = True

    if len(结果) == 2:
        (_, _, 原A, 行A, _), (_, _, _, 行B, _) = 结果
        对上 = []          # (a原样, a星, b原样, b星)
        b配过 = set()
        for a原, a星, a跨 in 行A:
            候 = [(i, b) for i, b in enumerate(行B) if 重叠(a跨, b[2]) >= 0.3]
            for i, (b原, b星, _b跨) in 候:
                对上.append((a原, a星, b原, b星))
                b配过.add(i)
            if not 候:
                对上.append((a原, a星, None, None))
        只B有 = [b for i, b in enumerate(行B) if i not in b配过]

        相同 = [x for x in 对上 if x[3] is not None and x[1] == x[3]]
        不同 = [x for x in 对上 if x[3] is not None and x[1] != x[3]]
        只A有 = [x for x in 对上 if x[3] is None]
        print('\n【二 · 判级差异】(锚回原话对齐,跨度重叠 ≥30% 算同一句)')
        print(f'配上 {len(相同) + len(不同)} 对:相同 {len(相同)} 对,不同 {len(不同)} 对')
        for a原, a星, b原, b星 in 相同:
            print(f'  = 「{a原}」{"★" * a星}  ↔  「{b原}」{"★" * b星}')
        for a原, a星, b原, b星 in 不同:
            print(f'  ≠ 「{a原}」{"★" * a星}  ↔  「{b原}」{"★" * b星}')
        print(f'一方缺失:前一份独有 {len(只A有)} 句,后一份独有 {len(只B有)} 句')
        for a原, a星, _, _ in 只A有:
            print(f'  · 只有前一份有:「{a原}」({"★" * a星})')
        for b原, b星, _跨 in 只B有:
            print(f'  · 只有后一份有:「{b原}」({"★" * b星})')

    print('\n【三 · 标记计数】(只能抓「标得少」,抓不到「该标没标」)')
    各 = [数标记(t) for _p, t, _y, _r, _l in 结果]
    for (p, *_), n in zip(结果, 各):
        print(f'{p}: [事实]×{n["事实"]}  [推断]×{n["推断"]}  [猜测]×{n["猜测"]}')
    if len(各) == 2:
        print(f'差额:  [事实]×{abs(各[0]["事实"] - 各[1]["事实"])}'
              f'  [推断]×{abs(各[0]["推断"] - 各[1]["推断"])}'
              f'  [猜测]×{abs(各[0]["猜测"] - 各[1]["猜测"])}')

    sys.exit(1 if 有漏 else 0)


if __name__ == '__main__':
    main()
