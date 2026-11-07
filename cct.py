# -*- coding: utf-8 -*-
"""CCT 扫描：把当前局面里「我所有的将军、吃子、威胁」列出来。

这不是让引擎替你想，而是**对答案**用的：落子前你先自己口报一遍——
「我有哪些将军？哪些吃子？哪些威胁？」——再敲 cct 看漏了没有。

* 将军(checks)：走完给对方王将军的着法。
* 吃子(captures)：所有吃子，并用静态兑子(SEE)标出「白赚 / 均等 / 亏」。
* 威胁(threats)：走完之后，下一步能白赚对方一个子的**安静着法**
  （即这一步造出了一个新的「对方白送的子」）。

全部是数出来的，不用引擎。`python3 cct.py` 跑自带检查。
"""

from board import opp, KING
import blindspot as bs

WIN, EVEN, LOSE = "赚", "均", "亏"


def _tag(val):
    return WIN if val > 0 else (EVEN if val == 0 else LOSE)


def checks(b):
    """给对方将军的着法（SAN），去重保序。"""
    out = []
    for m in b.gen_moves():
        if not b.is_legal(m):
            continue
        s = b.san(m)
        if s.endswith("+") or s.endswith("#"):
            out.append(s)
    return out


def captures(b):
    """所有吃子：[(SAN, SEE 值, 赚/均/亏)]，按赚得多的排前面。"""
    out = []
    for m in b.gen_moves():
        if not b.is_legal(m):
            continue
        to = (m >> 8) & 0xFF
        # 吃子 = 目标格有对方子（含吃过路兵：目标格空但沿途…这里只认普通吃子）
        if b.sq[to]:
            out.append((b.san(m), bs.see(b, m)))
    out.sort(key=lambda x: -x[1])
    return [(s, v, _tag(v)) for s, v in out]


def threats(b):
    """安静着法里，走完能白赚对方一个子的：[(SAN, [目标格名])]。

    做法：先记下现在对方有哪些子是白送的；对每一步安静着法，走完再看
    对方是不是**多**出了白送的子——多出来的就是这步棋威胁到的。
    """
    from board import sq_name
    them = opp(b.side)
    before = {sq for sq, _t, _v in bs.hanging(b, them)}
    out = []
    for m in b.gen_moves():
        if not b.is_legal(m):
            continue
        to = (m >> 8) & 0xFF
        s = b.san(m)
        if b.sq[to] or s.endswith("+") or s.endswith("#"):
            continue                       # 吃子/将军已经单独列了
        b.make(m)
        after = {sq for sq, _t, _v in bs.hanging(b, them)}
        b.unmake()
        gained = after - before
        if gained:
            out.append((s, sorted(sq_name(x) for x in gained)))
    return out


def report(b, lang="zh"):
    """一段可直接打印的 CCT 清单。"""
    zh = lang != "en"
    ck = checks(b)
    cp = captures(b)
    th = threats(b)
    L = []
    who = ("白方" if b.side == 8 else "黑方") if zh else \
          ("White" if b.side == 8 else "Black")
    L.append("———— CCT 扫描（轮到%s）————" % who if zh
             else "———— CCT scan (%s to move) ————" % who)
    L.append(("将军 Checks (%d)：" % len(ck)) + ("、".join(ck) if ck else
             ("无" if zh else "none")))
    if cp:
        parts = ["%s[%s%+d]" % (s, t, v) for s, v, t in cp]
        L.append(("吃子 Captures (%d)：" % len(cp)) + "、".join(parts))
    else:
        L.append("吃子 Captures (0)：" + ("无" if zh else "none"))
    if th:
        # 按「威胁到哪个子」归类：同一个目标常有好几步都能打，别一条条铺开。
        by_target = {}
        for s, tgs in th:
            for t in tgs:
                by_target.setdefault(t, []).append(s)
        L.append("威胁 Threats（能白赚的子 ← 可以这样打）：")
        for t in sorted(by_target, key=lambda x: -len(by_target[x])):
            mv = by_target[t]
            shown = "、".join(mv[:3]) + ("…" if len(mv) > 3 else "")
            L.append("    %s  ←  %s" % (t, shown))
    else:
        L.append("威胁 Threats (0)：" + ("无" if zh else "none"))
    if zh:
        L.append("（吃子里的 赚/均/亏 是静态兑子判的；先自己报一遍再看这个。）")
    return "\n".join(L)


# --------------------------------------------------------------- 自检
def _selftest():
    from board import Board
    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        print("%-40s %s %s" % (name, "ok" if cond else "FAIL", extra))
        ok = ok and cond

    # 1) 「困死角落的马」局面：黑方有一步将军 Re8+
    b = Board("N1bk3r/pp1p1ppp/2n5/8/8/2n5/PPP2PPP/R3KB1R b KQ - 0 12")
    ck = checks(b)
    check("Re8+ 在将军列表里", "Re8+" in ck, str(ck))

    # 2) 白吃一子局面：Qxb3 是白赚的吃子
    b = Board("6k1/5ppp/8/8/8/1p6/5PPP/3Q2K1 w - - 0 1")
    cp = captures(b)
    sans = [s for s, _v, _t in cp]
    check("Qxb3 在吃子列表里", "Qxb3" in sans, str(sans))
    check("Qxb3 判为白赚", any(s == "Qxb3" and t == WIN for s, _v, t in cp))

    # 3) 起始局面：没有将军、没有吃子、没有威胁
    b = Board()
    check("开局无将军", checks(b) == [], str(checks(b)))
    check("开局无吃子", captures(b) == [])

    # 4) 威胁：车走到对方白送的子那条线上
    #    白车 d1，黑方 d7 有个没保护的象 —— Rd1 已经在盯着，走 e 兵不算
    b = Board("3b2k1/3p2pp/8/8/8/8/6PP/3R2K1 w - - 0 1")
    #    这里 d7 是兵挡着，象 d8 被 d1 车透过 d7? 不透。换个直接的：
    b = Board("6k1/6pp/8/8/8/8/6PP/1R4K1 w - - 0 1")
    #    白车 b1，黑方无子可威胁 —— 威胁应为空
    check("无威胁时 threats 为空", threats(b) == [], str(threats(b)))
    return ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if _selftest() else 1)
