# -*- coding: utf-8 -*-
"""给失误自动分类——只用能算出来的判据，不做主观判断。

复盘报告说「严重失误(-578)」，但没说**是哪一类**失误。对教练来说，
「这个学生每 8 步崩一次，其中 70% 是同一类」比任何准确率百分比都有用。

五类，每一类都有明确的机械判据：

* `hang`      走完之后自己多了一个白送的子（静态兑子 SEE 判定）
* `defender`  被移动的那个子，原来正守着现在白送的那个子
* `line`      被移动的那个子，原来挡在对方远程子和自己大子之间
* `miss`      引擎的最佳着法是一步白赚的吃子，实战没吃
* `grab`      这一步吃了个兵（配合评分下降才有意义）

一步棋可以同时属于多类——6.Ne5?? 就同时是 `line` 和 `hang`。

`python3 errors.py` 会拿三个真实对局里的着法验证。
"""

from board import (Board, WHITE, BLACK, PAWN, KNIGHT, BISHOP, ROOK, QUEEN,
                   KING, opp, sq_name, mk_move)
import blindspot as bs

# 白送多少分才算数（一个兵以上）
HANG_MIN = 150
# 漏掉的吃子要白赚多少才算数
MISS_MIN = 200

LABELS = {
    "hang":     ("白送子", "hung a piece"),
    "defender": ("走开的子原来在守它", "moved the only defender"),
    "line":     ("挪开挡线的子", "opened a line to your own piece"),
    "miss":     ("漏掉一步白吃", "missed a free capture"),
    "grab":     ("贪兵", "pawn grab"),
}


def _hanging_map(b, color):
    """{格子: 亏多少}，只算亏得超过 HANG_MIN 的。"""
    return {sq: val for sq, _t, val in bs.hanging(b, color) if val >= HANG_MIN}


def _between(a, b_sq, c):
    """b_sq 是否严格在 a 和 c 之间（同一直线/斜线上）。"""
    da, dc = b_sq - a, c - b_sq
    for step in (1, -1, 16, -16, 15, -15, 17, -17):
        s = a + step
        seen = False
        while not (s & 0x88):
            if s == b_sq:
                seen = True
            elif s == c:
                return seen
            s += step
    return False


def _slider_attackers(b, sq, color):
    """攻击 sq 的对方远程子（象/车/后），返回格子列表。"""
    out = []
    for frm, t in bs.attackers_of(b, sq, color):
        if t in (BISHOP, ROOK, QUEEN):
            out.append(frm)
    return out


def classify(before, move, after, best_move=None):
    """before/after 是走这一步前后的棋盘，move 是实战着法。

    返回标签列表（可能为空）。两个棋盘都不会被修改。
    """
    frm = move & 0xFF
    to = (move >> 8) & 0xFF
    piece = before.sq[frm]
    mover = piece & 24
    captured = before.sq[to]
    tags = []

    was = _hanging_map(before, mover)
    now = _hanging_map(after, mover)
    new_hangs = {sq: v for sq, v in now.items() if sq not in was}

    if new_hangs:
        tags.append("hang")
        worst = max(new_hangs, key=lambda s: new_hangs[s])

        # 被移动的子原来是不是 worst 的保护者？
        for f, _t in bs.attackers_of(before, worst, mover):
            if f == frm:
                tags.append("defender")
                break

        # 被移动的子原来是不是挡在对方远程子和 worst 之间？
        for a in _slider_attackers(after, worst, opp(mover)):
            if _between(a, frm, worst):
                tags.append("line")
                break

    if best_move is not None and best_move != move:
        bt = (best_move >> 8) & 0xFF
        if before.sq[bt] and bs.see(before, best_move) >= MISS_MIN:
            tags.append("miss")

    if captured and (captured & 7) == PAWN and (piece & 7) != PAWN:
        tags.append("grab")

    return tags


def label(tag, lang="zh"):
    return LABELS[tag][1 if lang == "en" else 0]


# --------------------------------------------------------------- 自检
def _replay(sans):
    b = Board()
    for s in sans[:-1]:
        b.make(b.parse_move(s))
    return b, b.parse_move(sans[-1])


def _selftest():
    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        print("%-40s %s %s" % (name, "ok" if cond else "FAIL", extra))
        ok = ok and cond

    # 1) Jeremy vs Peter, 6.Ne5?? —— 自己的马原来挡着黑象打 d1 的后
    b, m = _replay("e4 c6 Nf3 d5 exd5 cxd5 d4 Bg4 Bb5+ Nc6 Ne5".split())
    a = Board(b.fen())
    a.make(a.parse_move("Ne5"))
    t = classify(b, m, a)
    check("6.Ne5?? = 挪开挡线的子 + 白送", "line" in t and "hang" in t, str(t))

    # 2) Jeremy vs Paul, 28.Qxe4?? —— 后走了，e2 的车没人守了；
    #    而且 Rxb2 是一步白吃（吃对方的后）
    fen = "3rr1k1/p1b2pp1/1p2p2p/8/3PpP2/P1PQB1P1/1q2R2P/2R3K1 w - - 0 28"
    b = Board(fen)
    m = b.parse_move("Qxe4")
    best = b.parse_move("Rxb2")
    a = Board(fen)
    a.make(a.parse_move("Qxe4"))
    t = classify(b, m, a, best)
    check("28.Qxe4?? = 走开的子原来在守它", "defender" in t, str(t))
    check("28.Qxe4?? = 漏掉一步白吃", "miss" in t, str(t))

    # 3) 正常的好棋不该被打标签
    b = Board()
    m = b.parse_move("e4")
    a = Board()
    a.make(a.parse_move("e4"))
    check("1.e4 不该有标签", classify(b, m, a) == [], str(classify(b, m, a)))

    # 4) 贪兵：后跑去吃一个兵
    fen = "6k1/5ppp/8/8/8/1p6/5PPP/3Q2K1 w - - 0 1"
    b = Board(fen)
    m = b.parse_move("Qxb3")
    a = Board(fen)
    a.make(a.parse_move("Qxb3"))
    check("Qxb3 = 贪兵", "grab" in classify(b, m, a), str(classify(b, m, a)))

    # 5) 不改棋盘
    fen = "3rr1k1/p1b2pp1/1p2p2p/8/3PpP2/P1PQB1P1/1q2R2P/2R3K1 w - - 0 28"
    b = Board(fen)
    a = Board(fen)
    a.make(a.parse_move("Qxe4"))
    classify(b, b.parse_move("Qxe4"), a, b.parse_move("Rxb2"))
    check("算完不改棋盘", b.fen() == fen, b.fen())
    return ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if _selftest() else 1)
