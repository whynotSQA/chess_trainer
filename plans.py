# -*- coding: utf-8 -*-
"""从引擎的主变里**归纳**计划主题——不猜、不编。

输入是引擎给出的前 K 条主变（MultiPV）。每一条主题都必须满足：

* 是主变里**真实发生的事件**（某个子确实走到了某条线上、某个兵确实做了突破），
* 而且（对于统计类主题）在 **至少 2 条主变里都出现**——只在一条线里出现的
  巧合不报。

这样得到的不是「引擎的战略思想」（它没有），而是「引擎算出来的着法序列里
反复出现的东西」。区别很重要，README 和界面上都按后者措辞。

`python3 plans.py` 会跑自带的检查。
"""

from board import (WHITE, BLACK, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
                   opp, sq_name)


def file_of(s):
    return s & 7


def rank_of(s):
    return s >> 4

MAX_PLY = 12            # 往前看多少层（主变超过这个长度就截断）
MIN_LINES = 2           # 统计类主题至少要在几条主变里出现


# --------------------------------------------------------------- 小工具
def _pawn_attacks_sq(b, sq, color):
    """color 方是否有兵攻击 sq。"""
    deltas = (-15, -17) if color == WHITE else (15, 17)
    want = color | PAWN
    for d in deltas:
        t = sq + d
        if not (t & 0x88) and b.sq[t] == want:
            return True
    return False


def _pawn_attacks_a_pawn(b, sq, color):
    """站在 sq 的 color 方兵，是否正攻击着对方的兵。"""
    deltas = (15, 17) if color == WHITE else (-15, -17)
    want = opp(color) | PAWN
    for d in deltas:
        t = sq + d
        if not (t & 0x88) and b.sq[t] == want:
            return True
    return False


def file_status(b, f):
    """返回 (白方有没有兵, 黑方有没有兵)。"""
    w = bl = False
    for r in range(8):
        p = b.sq[r * 16 + f]
        if p and (p & 7) == PAWN:
            if (p & 24) == WHITE:
                w = True
            else:
                bl = True
    return w, bl


def _king_zone(b, color):
    """对方王周围两格的格子集合。"""
    k = b.kings[color]
    out = set()
    kf, kr = file_of(k), rank_of(k)
    for df in range(-2, 3):
        for dr in range(-2, 3):
            f, r = kf + df, kr + dr
            if 0 <= f < 8 and 0 <= r < 8:
                out.add(r * 16 + f)
    return out


# --------------------------------------------------------------- 事件提取
def _walk(root, moves):
    """把一条主变走一遍，返回事件列表。棋盘状态保证复原。"""
    ev, made = [], 0
    for m in moves[:MAX_PLY]:
        if not root.is_legal(m):
            break
        frm, to = m & 0xFF, (m >> 8) & 0xFF
        p = root.sq[frm]
        side, kind = p & 24, p & 7
        cap = bool(root.sq[to])
        san = root.san(m)
        root.make(m)
        made += 1
        # 突破 = 兵**推进**到与对方兵接触的位置。吃子不算：吃子是执行或者
        # 应招（比如对方 e5 之后我 fxe5），说成「计划」会误导。
        lever = False
        if kind == PAWN and not cap:
            lever = (_pawn_attacks_sq(root, to, opp(side))
                     or _pawn_attacks_a_pawn(root, to, side))
        ev.append({"side": side, "kind": kind, "frm": frm, "to": to,
                   "cap": cap, "san": san, "lever": lever})
    for _ in range(made):
        root.unmake()
    return ev


# --------------------------------------------------------------- 主题
def _heavy_files(events, side):
    """这条线里，side 的车/后落到了哪些直线上（去重）。"""
    return {file_of(e["to"]) for e in events
            if e["side"] == side and e["kind"] in (ROOK, QUEEN)
            and not e["cap"]}          # 吃子落到某条线上不叫「占线」


def _minor_squares(events, side):
    """side 的马/象落到对方半场的哪些格子（去重）。"""
    out = set()
    for e in events:
        if e["side"] != side or e["kind"] not in (KNIGHT, BISHOP):
            continue
        r = rank_of(e["to"])
        if (side == WHITE and r >= 4) or (side == BLACK and r <= 3):
            out.add(e["to"])
    return out


def _levers(events, side):
    return [e["san"] for e in events if e["side"] == side and e["lever"]]


def _king_pressure(root, events, side):
    """side 有几个不同的子走进了对方王的两格范围。"""
    zone = _king_zone(root, opp(side))
    return len({e["to"] for e in events
                if e["side"] == side and e["kind"] != PAWN and e["to"] in zone})


def _count_over_lines(per_line):
    """per_line 是 [set, set, ...]，返回 {元素: 出现在几条线里}。"""
    tally = {}
    for s in per_line:
        for x in s:
            tally[x] = tally.get(x, 0) + 1
    return tally


FILES = "abcdefgh"


def themes(root, lines, lang="zh"):
    """root: 当前局面; lines: [[着法,...], ...] 按好坏排序。

    返回 [(是我方还是对方, 主题文字), ...]；没有可靠主题就返回 []。
    """
    lines = [ln for ln in lines if ln][:3]
    if not lines:
        return []
    evs = [_walk(root, ln) for ln in lines]
    n = len(evs)
    need = MIN_LINES if n >= MIN_LINES else 1
    me, them = root.side, opp(root.side)
    out = []

    for side in (me, them):
        who = "us" if side == me else "them"
        bits = []

        # ① 重子上线：至少 need 条线里都有车/后走到同一条线，且该线是开放或半开放
        tally = _count_over_lines([_heavy_files(e, side) for e in evs])
        for f, c in sorted(tally.items(), key=lambda kv: (-kv[1], kv[0])):
            if c < need or n < MIN_LINES:
                continue
            w, bl = file_status(root, f)
            mine_has = w if side == WHITE else bl
            if mine_has:                       # 自己还有兵挡着，不算上线
                continue
            openfile = not w and not bl
            bits.append(T(lang, "file_open" if openfile else "file_half",
                          FILES[f]))
            break                              # 只报最突出的一条线

        # ② 兵的突破：主变里真实发生的事件，一条线也算数
        if n >= MIN_LINES:
            tally = _count_over_lines([set(_levers(e, side)) for e in evs])
            best = max(tally.items(), key=lambda kv: kv[1], default=None)
            if best and best[1] >= need:
                bits.append(T(lang, "lever", best[0])
                            + T(lang, "in_n", best[1], n))
        else:
            lv = _levers(evs[0], side)
            if lv:
                bits.append(T(lang, "lever", lv[0]))

        # ③ 马/象的固定落点
        tally = _count_over_lines([_minor_squares(e, side) for e in evs])
        for sq, c in sorted(tally.items(), key=lambda kv: -kv[1]):
            if c < need or n < MIN_LINES:
                continue
            outpost = not _pawn_attacks_sq(root, sq, opp(side))
            bits.append(T(lang, "outpost" if outpost else "square",
                          sq_name(sq)))
            break

        # ④ 压向对方王翼：主变里两个以上不同的子进了王区
        if _king_pressure(root, evs[0], side) >= 2:
            bits.append(T(lang, "king"))

        for bt in bits:
            out.append((who, bt))
    return out


MSG = {
    "file_open": ("重子上 %s 线（开放线）", "heavy pieces to the open %s-file"),
    "file_half": ("重子上 %s 线（半开放）", "heavy pieces to the half-open %s-file"),
    "lever":     ("准备 %s 突破", "pawn break %s"),
    "in_n":      ("（%d/%d 条主变）", " (%d of %d lines)"),
    "outpost":   ("把 %s 当据点", "%s as an outpost"),
    "square":    ("子力落到 %s", "piece to %s"),
    "king":      ("子力压向对方王翼", "pieces massing at the king"),
}


def T(lang, key, *args):
    s = MSG[key][1 if lang == "en" else 0]
    return s % args if args else s


def format_themes(root, lines, lang="zh"):
    """给界面用：返回一行字符串，没主题就返回 ''。"""
    ts = themes(root, lines, lang)
    if not ts:
        return ""
    mine = [t for w, t in ts if w == "us"]
    theirs = [t for w, t in ts if w == "them"]
    parts = []
    if mine:
        parts.append((T(lang, "you") if "you" in MSG else
                      ("你：" if lang == "zh" else "You: ")) + " · ".join(mine))
    if theirs:
        parts.append(("对方：" if lang == "zh" else "Them: ")
                     + " · ".join(theirs))
    return "   ".join(parts)


# --------------------------------------------------------------- 自检
def _selftest():
    from board import Board
    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        print("%-34s %s %s" % (name, "ok" if cond else "FAIL", extra))
        ok = ok and cond

    # 1) 开放 c 线上双车：主题应识别出 c 线
    b = Board("2r3k1/5ppp/p3p3/8/8/P4PPP/5K2/2R5 w - - 0 1")
    ln = [b.parse_move(s) for s in ("Rc4", "Rc5")]
    ts = themes(b, [ln, ln])
    check("开放 c 线", any("c 线" in t for _w, t in ts), str(ts))

    # 2) 兵的突破：b4-b5 打 a6/c6 的兵
    b = Board("6k1/2p2ppp/p7/8/1P6/P4PPP/6K1/8 w - - 0 1")
    ln = [b.parse_move("b5")]
    ts = themes(b, [ln])
    check("兵突破 b5", any("b5" in t for _w, t in ts), str(ts))

    # 3) 不该乱报：h3 这种不是突破
    b = Board("6k1/5ppp/8/8/8/5PP1/6KP/8 w - - 0 1")
    ln = [b.parse_move("h3")]
    ts = themes(b, [ln])
    check("h3 不算突破", not ts, str(ts))

    # 4) 据点：马到 d5，黑方 c/e 兵都没了
    b = Board("6k1/pp3ppp/8/8/8/2N3P1/PP3P1P/6K1 w - - 0 1")
    ln = [b.parse_move(s) for s in ("Nd5",)]
    ts = themes(b, [ln, ln])
    check("d5 据点", any("d5" in t for _w, t in ts), str(ts))

    # 5) 吃子不算突破：黑方 e5 之后白方 fxe5，不该说成白方的「计划」
    b = Board("6k1/8/8/4p3/5P2/8/6K1/8 w - - 0 1")
    ln = [b.parse_move("fxe5")]
    ts = themes(b, [ln])
    check("吃子不算突破", not any("突破" in t for _w, t in ts), str(ts))

    # 6) 吃子落到某条线上不叫占线
    b = Board("1q4k1/5ppp/8/8/8/5PPP/6K1/1R6 w - - 0 1")
    ln = [b.parse_move("Rxb8")]
    ts = themes(b, [ln, ln])
    check("吃子不算占线", not any("线" in t for _w, t in ts), str(ts))

    # 7) 三条主变里只有一条有突破 -> 不报
    b = Board("6k1/2p2ppp/p7/8/1P6/P4PPP/6K1/8 w - - 0 1")
    l1 = [b.parse_move("b5")]
    l2 = [b.parse_move("a4")]
    l3 = [b.parse_move("g4")]
    ts = themes(b, [l1, l2, l3])
    check("1/3 条主变不报突破", not any("突破" in t for _w, t in ts), str(ts))

    # 5) 棋盘状态必须复原
    b = Board("r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4")
    before = b.fen()
    themes(b, [[b.parse_move("O-O"), b.parse_move("Nf6")]])
    check("棋盘复原", b.fen() == before, b.fen())
    return ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if _selftest() else 1)
