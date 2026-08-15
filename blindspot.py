# -*- coding: utf-8 -*-
"""盲区训练的底层计算：静态兑子(SEE)、白吃清单、将军吃子清单、对手威胁。

这几样东西的共同点是：答案能由程序算准，所以可以当作训练的判卷标准。
"""

import random

from board import (Board, WHITE, BLACK, PAWN, KNIGHT, BISHOP, ROOK, QUEEN,
                   KING, F_EP, KNIGHT_DIRS, BISHOP_DIRS, ROOK_DIRS, KING_DIRS,
                   opp, ptype, pcolor, sq_name, START_FEN)
from engine import VALUE

SEE_VALUE = {PAWN: 100, KNIGHT: 320, BISHOP: 330, ROOK: 500, QUEEN: 900,
             KING: 10000}


def _least_valuable_attacker(b, sq, color, removed):
    """找出 color 方攻击 sq 的最便宜的子；removed 里的格子当成空的。

    滑动子每次重新扫描，所以「后面藏着的车」这类透视攻击会被自动算进来。
    """
    sqs = b.sq
    best = None

    def consider(frm):
        if frm in removed:
            return
        p = sqs[frm]
        if not p or (p & 24) != color:
            return
        t = p & 7
        nonlocal best
        if best is None or SEE_VALUE[t] < SEE_VALUE[best[1]]:
            best = (frm, t)

    # 兵
    if color == WHITE:
        for d in (-15, -17):
            t = sq + d
            if not (t & 0x88) and t not in removed and sqs[t] == (WHITE | PAWN):
                consider(t)
    else:
        for d in (15, 17):
            t = sq + d
            if not (t & 0x88) and t not in removed and sqs[t] == (BLACK | PAWN):
                consider(t)
    # 马
    for d in KNIGHT_DIRS:
        t = sq + d
        if not (t & 0x88) and sqs[t] == (color | KNIGHT):
            consider(t)
    # 王
    for d in KING_DIRS:
        t = sq + d
        if not (t & 0x88) and sqs[t] == (color | KING):
            consider(t)
    # 象 / 后（斜线）
    for d in BISHOP_DIRS:
        t = sq + d
        while not (t & 0x88):
            if t in removed:
                t += d
                continue
            p = sqs[t]
            if p:
                if (p & 24) == color and (p & 7) in (BISHOP, QUEEN):
                    consider(t)
                break
            t += d
    # 车 / 后（直线）
    for d in ROOK_DIRS:
        t = sq + d
        while not (t & 0x88):
            if t in removed:
                t += d
                continue
            p = sqs[t]
            if p:
                if (p & 24) == color and (p & 7) in (ROOK, QUEEN):
                    consider(t)
                break
            t += d
    return best


def see(b, move):
    """静态兑子评估：在 move 的目标格上把兑子过程走完，净赚多少（百分之一兵）。"""
    frm = move & 0xFF
    to = (move >> 8) & 0xFF
    flag = (move >> 20) & 0xF
    piece = b.sq[frm]
    if not piece:
        return 0
    me = piece & 24
    removed = {frm}
    if flag == F_EP:
        cap_sq = to - 16 if me == WHITE else to + 16
        removed.add(cap_sq)
        captured_value = SEE_VALUE[PAWN]
    else:
        target = b.sq[to]
        captured_value = SEE_VALUE[target & 7] if target else 0

    gain = [captured_value]
    attacker_type = piece & 7
    promo = (move >> 16) & 0xF
    if promo:
        gain[0] += SEE_VALUE[promo] - SEE_VALUE[PAWN]
        attacker_type = promo
    side = opp(me)
    d = 0
    while True:
        d += 1
        gain.append(SEE_VALUE[attacker_type] - gain[d - 1])
        if max(-gain[d - 1], gain[d]) < 0:      # 两边都不愿意继续
            break
        nxt = _least_valuable_attacker(b, to, side, removed)
        if nxt is None:
            break
        if nxt[1] == KING:
            # 王只有在对方再没有子能吃回来时才能吃
            probe = set(removed)
            probe.add(nxt[0])
            if _least_valuable_attacker(b, to, opp(side), probe) is not None:
                break
        removed.add(nxt[0])
        attacker_type = nxt[1]
        side = opp(side)
        if d > 30:
            break
    # 逐层回推：每一层都可以选择「不再吃」
    while d > 1:
        d -= 1
        gain[d - 1] = -max(-gain[d - 1], gain[d])
    return gain[0]


def attackers_of(b, sq, color, removed=None):
    """color 方所有攻击 sq 的子，返回 [(格子, 子力类型)]，按子力从小到大。"""
    out, seen = [], set(removed or ())
    while True:
        got = _least_valuable_attacker(b, sq, color, seen)
        if got is None:
            return out
        out.append(got)
        seen.add(got[0])


def explain_square(b, sq):
    """这个格子上的子被谁攻击、被谁保护——用来讲清楚「为什么是白送」。"""
    from board import PIECE_LETTER
    p = b.sq[sq]
    if not p:
        return None
    owner = p & 24
    att = attackers_of(b, sq, opp(owner))
    dfd = attackers_of(b, sq, owner)

    def fmt(lst):
        return [PIECE_LETTER[t] + sq_name(f) for f, t in lst] or []
    return {"piece": PIECE_LETTER[p & 7], "owner": owner,
            "attackers": fmt(att), "defenders": fmt(dfd)}


def hanging(b, color):
    """color 方哪些子正被攻击且吃了不亏（对方能白赚）。

    返回 [(格子, 子力类型, 对方能赚多少)]，按赚得多的排前面。
    """
    out = []
    them = opp(color)
    for s in range(128):
        if s & 0x88:
            continue
        p = b.sq[s]
        if not p or (p & 24) != color or (p & 7) == KING:
            continue
        att = _least_valuable_attacker(b, s, them, set())
        if att is None:
            continue
        # 构造一步「对方吃这个子」的着法，用 SEE 判断值不值
        from board import mk_move
        m = mk_move(att[0], s)
        save = b.side
        b.side = them
        try:
            val = see(b, m)
        finally:
            b.side = save
        if val > 0:
            out.append((s, p & 7, val))
    out.sort(key=lambda x: -x[2])
    return out


def checks_and_captures(b):
    """当前走子方所有的将军和吃子（含吃过路兵、升变）。"""
    out = []
    me = b.side
    for m in b.gen_moves():
        frm = m & 0xFF
        to = (m >> 8) & 0xFF
        is_cap = bool(b.sq[to]) or ((m >> 20) & 0xF) == F_EP
        b.make(m)
        if b.is_attacked(b.kings[me], b.side):
            b.unmake()
            continue
        gives_check = b.in_check()
        b.unmake()
        if is_cap or gives_check:
            out.append((m, is_cap, gives_check))
    return out


def threat(eng, b, secs=1.0):
    """对方如果能白走一步，最想走什么（空着搜索）。

    返回 (着法, 这步之后的分数, 当前分数)，都是从对方视角看。
    在被将军时没有意义，返回 None。
    """
    if b.in_check():
        return None
    now = eng.search(b, 64, secs).score        # 当前走子方视角
    b.make_null()
    try:
        r = eng.search(b, 64, secs)            # 对方视角
        if not r.move:
            return None
        return r.move, r.score, -now
    finally:
        b.unmake_null()


# ------------------------------------------------------- 找练习用的局面
def random_position(eng, rnd, min_ply=12, max_ply=44, level=4):
    """自对弈到随机一步，得到一个像样的中局局面。"""
    from engine import choose_move
    import book
    b = Board(START_FEN)
    target = rnd.randint(min_ply, max_ply)
    for _ in range(target):
        if b.outcome():
            break
        m, _n = book.probe(b, rnd)
        if m is None:
            if rnd.random() < 0.25:
                legal = b.legal_moves()
                m = rnd.choice(legal) if legal else None
            else:
                m = choose_move(eng, b, level).move
        if not m:
            break
        b.make(m)
    return b


def positions_from_pgn(path, rnd, want=20, why=None):
    """从 PGN 里挑局面（你自己的对局最有针对性）。

    一个都取不到的时候，把原因写进 why（一个单元素列表）——静悄悄返回 0
    最难查，用户只会看见「Loaded 0 positions」。
    """
    from board import pgn_moves, pgn_headers

    def note(msg):
        if why is not None:
            why.append(msg)

    try:
        raw = open(path, encoding="utf-8", errors="ignore").read()
    except OSError as exc:
        note("读不了这个文件：%s" % exc)
        return []
    if not raw.strip():
        note("文件是空的（0 字节）")
        return []
    fen = pgn_headers(raw).get("FEN", START_FEN)
    sans = pgn_moves(raw)
    if not sans:
        note("文件里没找到任何着法——是不是只有标签、没有棋谱正文？")
        return []
    b = Board(fen)
    out = []
    for i, san in enumerate(sans, 1):
        m = b.parse_move(san)
        if m is None:
            note("第 %d 个着法 %r 解析不了，只读到这里（共 %d 个）"
                 % (i, san, len(sans)))
            break
        b.make(m)
        if len(b.history) >= 8:
            out.append(b.fen())
    if not out:
        note("棋谱只有 %d 手，不到 8 手，取不出中局局面" % len(sans))
    rnd.shuffle(out)
    return [Board(f) for f in out[:want]]


def positions_from_dir(dirpath, rnd, want=20, why=None, match=None,
                       seen=None):
    """把一个目录里所有 PGN 的局面汇总起来（默认用法：games/ 整个目录）。

    * 跳过 `_` 开头的文件（_autosave 之类的内部文件）
    * match 给定时只要文件名里含这个字串的（不分大小写），用来按学生筛
    * 按 FEN 去重——同一盘棋存了两份不会让某些局面出现两次
    * seen 给定时（一堆练过的 FEN），**没练过的排前面**，练过的垫底；
      两组各自打乱。这样不会连着出同一批题，练完一轮才开始重复
    * 返回 (局面表, [(文件名, 取到几个), ...], 还有几个没练过)
    """
    import os

    def note(msg):
        if why is not None:
            why.append(msg)

    try:
        names = sorted(f for f in os.listdir(dirpath) if f.lower().endswith(".pgn"))
    except OSError as exc:
        note("读不了目录 %s：%s" % (dirpath, exc))
        return [], [], 0
    names = [f for f in names if not f.startswith("_")]
    if match:
        low = match.lower()
        names = [f for f in names if low in f.lower()]
        if not names:
            note("%s 里没有名字含「%s」的棋谱" % (dirpath, match))
            return [], [], 0
    if not names:
        note("%s 里没有棋谱文件" % dirpath)
        return [], [], 0

    # 注意：去重用的集合不能也叫 seen——那会把参数覆盖掉（踩过一次）
    dedupe, out, per_file = set(), [], []
    for f in names:
        sub = []
        got = positions_from_pgn(os.path.join(dirpath, f), rnd, want=10 ** 6)
        for board in got:
            key = board.fen()
            if key in dedupe:
                continue
            dedupe.add(key)
            sub.append(board)
        if sub:
            per_file.append((f, len(sub)))
            out.extend(sub)
    if not out:
        note("%d 个棋谱都没取到局面" % len(names))
    seen = seen or set()
    fresh = [b for b in out if b.fen() not in seen]
    used = [b for b in out if b.fen() in seen]
    rnd.shuffle(fresh)
    rnd.shuffle(used)
    return (fresh + used)[:want], per_file, len(fresh)
