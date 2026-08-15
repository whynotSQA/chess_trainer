# -*- coding: utf-8 -*-
"""局面的结构特征——全是数出来的，没有一条靠判断。

复盘报告里「Bb7 丢了 0.95 分」这种话，事后看没什么用；有用的是**当时**就
能看见的东西：你的哪个子快不能动了、你把哪条线让出去了、你的象是不是跑到
了自己兵的颜色上。这些都是可以直接数的。

只统计马、象、车、后——兵和王的活动格数说明不了问题。
数的是**伪合法**着法（不排除被牵制的情况），因为它不依赖轮到谁走，
在复盘里对任何一方、任何时刻都能算，而且不需要动棋盘。

`python3 structure.py` 会跑自带的检查。
"""

from board import (WHITE, BLACK, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
                   opp, sq_name, START_FEN)

PIECES = (KNIGHT, BISHOP, ROOK, QUEEN)
NAME = {KNIGHT: "N", BISHOP: "B", ROOK: "R", QUEEN: "Q"}

# 一个子活动格数低到这个数，就算「快不能动了」
CRAMPED = 3
# 一步之内活动格数掉这么多，就单独点出来
DROP = 2
# 「持续走低」至少要横跨这么多步，否则只是收官时的正常波动
MIN_SPAN = 3


def sq_color(s):
    """0 = 深色格，1 = 浅色格。"""
    return ((s & 7) + (s >> 4)) & 1


def mobility(b, color):
    """{格子: 该子的伪合法落点数}，只算马象车后。一个都走不了的子也会列出来。"""
    save = b.side
    b.side = color
    try:
        counts = {}
        for m in b.gen_moves():
            frm = m & 0xFF
            p = b.sq[frm]
            if p and (p & 7) in PIECES:
                counts[frm] = counts.get(frm, 0) + 1
    finally:
        b.side = save
    for s in range(128):
        if s & 0x88:
            continue
        p = b.sq[s]
        if p and (p & 24) == color and (p & 7) in PIECES:
            counts.setdefault(s, 0)
    return counts


def worst_piece(b, color, only=None):
    """活动格数最少的那个子：(格子, 类型, 格数)。没有子就返回 None。

    only 给定时只看这些格子上的子。复盘里传「已经出动过的子」——
    开局没出动的车当然是 0 个落点，那是常态，不是毛病。
    """
    mob = mobility(b, color)
    if only is not None:
        mob = {s: v for s, v in mob.items() if s in only}
    if not mob:
        return None
    sq = min(mob, key=lambda s: (mob[s], s))
    return sq, b.sq[sq] & 7, mob[sq]


def piece_label(b, sq):
    p = b.sq[sq]
    return NAME.get(p & 7, "?") + sq_name(sq)


def pawns_on_color(b, color, want):
    """color 方有几个兵站在 want（0 深 / 1 浅）颜色的格子上。"""
    n = 0
    for s in range(128):
        if s & 0x88:
            continue
        p = b.sq[s]
        if p == (color | PAWN) and sq_color(s) == want:
            n += 1
    return n


def blocked_bishops(b, color):
    """[(格子, 同色格上自己的兵数)]，兵数多说明这个象被自己人挡着。"""
    out = []
    for s in range(128):
        if s & 0x88:
            continue
        if b.sq[s] == (color | BISHOP):
            out.append((s, pawns_on_color(b, color, sq_color(s))))
    return out


def files_held(b, color):
    """color 方的车/后占着、而且自己没有兵挡路的直线。"""
    out = set()
    for f in range(8):
        heavy = own_pawn = False
        for r in range(8):
            p = b.sq[r * 16 + f]
            if not p:
                continue
            if (p & 24) == color:
                if (p & 7) in (ROOK, QUEEN):
                    heavy = True
                elif (p & 7) == PAWN:
                    own_pawn = True
        if heavy and not own_pawn:
            out.add(f)
    return out


def snapshot(b, color, only=None):
    """一个局面里跟「子力好不好用」有关的全部数字。"""
    w = worst_piece(b, color, only)
    return {"worst": w,
            "worst_label": piece_label(b, w[0]) if w else "",
            "files": files_held(b, color),
            "bishops": {s: n for s, n in blocked_bishops(b, color)},
            "total": sum(mobility(b, color).values())}


FILES = "abcdefgh"


def notes(before, after, lang="zh"):
    """两个 snapshot 之间发生了什么。返回 [说明]，没什么可说就返回 []。"""
    out = []
    zh = lang != "en"
    bw, aw = before["worst"], after["worst"]
    if bw and aw:
        # 同一个子变得更差
        if bw[0] == aw[0] and aw[2] <= bw[2] - DROP:
            out.append(("最差的子 %s 的活动格数 %d → %d"
                        if zh else "your worst piece %s: %d → %d moves")
                       % (after["worst_label"], bw[2], aw[2]))
        elif aw[2] <= CRAMPED and aw[2] < bw[2]:
            out.append(("现在最差的子是 %s，只剩 %d 个落点"
                        if zh else "worst piece is now %s with only %d moves")
                       % (after["worst_label"], aw[2]))
        if aw[2] == 0 and bw[2] != 0:      # 只在刚被封死的那一步报
            out.append(("%s 一步都走不了" if zh else "%s cannot move at all")
                       % after["worst_label"])
    lost = before["files"] - after["files"]
    for f in sorted(lost):
        out.append(("让出了 %s 线" if zh else "gave up the %s-file") % FILES[f])
    for s, n in after["bishops"].items():
        old = before["bishops"].get(s)
        if old is None and n >= 4:          # 象刚走到自己兵的颜色上
            out.append(("象走到了 %s——自己有 %d 个兵在同色格上"
                        if zh else "bishop to %s — %d own pawns on that colour")
                       % (sq_name(s), n))
    return out


def trend(series):
    """series 是 [(回合, 标签, 格数)]。找出「一路走低且没回升」的一段。

    返回 (起点索引, 终点索引) 或 None。判据：终点 <= CRAMPED，
    且从起点到终点单调不升，且至少跌了 DROP。
    """
    if len(series) < 3:
        return None
    j = len(series) - 1
    if series[j][2] > CRAMPED:
        return None
    i = j
    while i > 0 and series[i - 1][2] >= series[i][2]:
        i -= 1
    if series[i][2] - series[j][2] < DROP or j - i < MIN_SPAN:
        return None
    return i, j


class Developed(object):
    """跟踪「哪些子已经动过了」——按棋子走，不是按格子。

    必须真的跟踪：那盘 QGD 里黑象最后停在 a8，而 a8 本来就是车的出发格，
    光看「在不在原位」会把它漏掉。
    """

    def __init__(self):
        self.moved = set()             # 当前所在格子的集合

    def apply(self, b, m):
        """在 b.make(m) **之前**调用。"""
        frm, to = m & 0xFF, (m >> 8) & 0xFF
        p = b.sq[frm]
        if b.sq[to]:                   # 被吃掉的子不再算数
            self.moved.discard(to)
        self.moved.discard(frm)
        if (p & 7) in PIECES:
            self.moved.add(to)
        if (p & 7) == KING and abs((frm & 7) - (to & 7)) == 2:
            rank = frm & 0xF0          # 王车易位时车也动了
            if (to & 7) == 6:
                self.moved.discard(rank | 7)
                self.moved.add(rank | 5)
            else:
                self.moved.discard(rank)
                self.moved.add(rank | 3)

    def squares(self):
        return set(self.moved)


# --------------------------------------------------------------- 自检
def _selftest():
    from board import Board
    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        print("%-36s %s %s" % (name, "ok" if cond else "FAIL", extra))
        ok = ok and cond

    # 1) a8 的象被自己 b7 的兵挡死：0 个落点
    b = Board("b5k1/1p3ppp/8/8/8/8/5PPP/6K1 b - - 0 1")
    w = worst_piece(b, BLACK)
    check("被挡死的象 = 0 个落点", w and w[2] == 0 and sq_name(w[0]) == "a8",
          str(w))

    # 2) 开局局面：不该有子完全走不了以外的怪结果
    b = Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    m = mobility(b, WHITE)
    # 马象车后一共 7 个（2 马 2 象 2 车 1 后），开局只有两个马能动
    check("开局白方 7 个马象车后", len(m) == 7, str(len(m)))
    check("开局只有两个马能动，各 2 个落点",
          sorted(m.values()) == [0, 0, 0, 0, 0, 2, 2], str(sorted(m.values())))

    # 3) 数格子颜色
    from board import name_sq
    check("a1 是深色格", sq_color(name_sq("a1")) == 0)
    check("h1 是浅色格", sq_color(name_sq("h1")) == 1)

    # 4) 占线：车在开放的 c 线上
    b = Board("2r3k1/5ppp/8/8/8/8/5PPP/2R3K1 w - - 0 1")
    check("双方都占着 c 线",
          files_held(b, WHITE) == {2} and files_held(b, BLACK) == {2},
          "%s %s" % (files_held(b, WHITE), files_held(b, BLACK)))

    # 5) 自己有兵挡着就不算占线
    b = Board("2r3k1/2p2ppp/8/8/8/8/2P2PPP/2R3K1 w - - 0 1")
    check("有兵挡着不算占线",
          not files_held(b, WHITE) and not files_held(b, BLACK))

    # 6) 不动棋盘
    b = Board("r1bq1rk1/pp1nbppp/2p1pn2/3p4/2PP1B2/2N1PN2/PPQ2PPP/R3KB1R w KQ - 0 1")
    fen = b.fen()
    snapshot(b, WHITE), snapshot(b, BLACK)
    check("算完不改棋盘", b.fen() == fen, b.fen())

    # 7) 出动追踪：象走到 a8（车的出发格）之后仍然算「出动过」
    b = Board(START_FEN)
    dev = Developed()
    for san in "d4 d5 c4 e6 Nc3 Nf6 Bg5 Be7 e3 O-O".split():
        m = b.parse_move(san)
        dev.apply(b, m)
        b.make(m)
    from board import name_sq
    sq = dev.squares()
    check("易位后黑车记在 f8", name_sq("f8") in sq, sorted(sq_name(x) for x in sq))
    check("没动过的 a8 车不算出动", name_sq("a8") not in sq)

    # 8) trend：一路从 6 掉到 0
    t = trend([(1, "Bb7", 6), (2, "Bb7", 4), (3, "Ba8", 2), (4, "Ba8", 0)])
    check("识别出持续走低", t == (0, 3), str(t))
    # 中途回升就不算
    t2 = trend([(1, "B", 6), (2, "B", 1), (3, "B", 5), (4, "B", 2)])
    check("回升过就不报", t2 is None, str(t2))
    # 只跌两步不算——收官时的正常波动
    t3 = trend([(1, "B", 8), (2, "B", 5), (3, "B", 2)])
    check("跨度太短不报", t3 is None, str(t3))
    return ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if _selftest() else 1)
