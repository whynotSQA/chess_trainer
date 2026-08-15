# -*- coding: utf-8 -*-
"""开局库：主流开局的主变，走出理论线之后再交给引擎自己算。

每条线都是标准主变，`python3 test_book.py` 会逐步验证合法性并让引擎
检查每条线的终局面是否在合理范围内（防止手误写错一步）。
"""

import random

from board import Board, START_FEN, pgn_moves

# (开局名, 主变)
LINES = [
    # ---------------------------------------------------------- 1.e4 e5
    ("意大利开局",
     "e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3 d6 O-O O-O"),
    ("两马防御",
     "e4 e5 Nf3 Nc6 Bc4 Nf6 Ng5 d5 exd5 Na5 Bb5+ c6 dxc6 bxc6 Be2 h6 Nf3 e4"),
    ("西班牙开局（封闭变例）",
     "e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Be7 Re1 b5 Bb3 d6 c3 O-O h3 Na5 Bc2 c5"),
    ("西班牙开局（交换变例）",
     "e4 e5 Nf3 Nc6 Bb5 a6 Bxc6 dxc6 O-O f6 d4 exd4 Nxd4 c5"),
    ("西班牙开局（柏林防御）",
     "e4 e5 Nf3 Nc6 Bb5 Nf6 O-O Nxe4 d4 Nd6 Bxc6 dxc6 dxe5 Nf5 Qxd8+ Kxd8"),
    ("苏格兰开局",
     "e4 e5 Nf3 Nc6 d4 exd4 Nxd4 Bc5 Be3 Qf6 c3 Nge7 Bc4 Ne5"),
    ("四马开局",
     "e4 e5 Nf3 Nc6 Nc3 Nf6 Bb5 Bb4 O-O O-O d3 d6 Bg5 Bxc3 bxc3 Qe7"),
    ("俄罗斯防御（彼得洛夫）",
     "e4 e5 Nf3 Nf6 Nxe5 d6 Nf3 Nxe4 d4 d5 Bd3 Be7 O-O Nc6 Re1 Bg4"),
    ("菲利多尔防御",
     "e4 e5 Nf3 d6 d4 Nf6 Nc3 Nbd7 Bc4 Be7 O-O O-O"),
    ("维也纳开局",
     "e4 e5 Nc3 Nf6 f4 d5 fxe5 Nxe4 Nf3 Be7"),
    ("王翼弃兵",
     "e4 e5 f4 exf4 Nf3 g5 h4 g4 Ne5 Nf6 d4 d6 Nd3 Nxe4"),

    # ---------------------------------------------------------- 1.e4 c5
    ("西西里防御（那道夫变例）",
     "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6 Be3 e5 Nb3 Be6 f3 Be7"),
    ("西西里防御（龙式变例）",
     "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 g6 Be3 Bg7 f3 O-O Qd2 Nc6 Bc4 Bd7"),
    ("西西里防御（斯维什尼科夫）",
     "e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 Nf6 Nc3 e5 Ndb5 d6 Bg5 a6 Na3 b5"),
    ("西西里防御（加速龙）",
     "e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 g6 c4 Bg7 Be3 Nf6 Nc3 O-O Be2 d6"),
    ("西西里防御（泰马诺夫）",
     "e4 c5 Nf3 e6 d4 cxd4 Nxd4 Nc6 Nc3 Qc7 Be2 a6 O-O Nf6"),
    ("西西里防御（罗索里莫）",
     "e4 c5 Nf3 Nc6 Bb5 g6 Bxc6 dxc6 d3 Bg7 h3 Nf6 Nc3 O-O"),
    ("西西里防御（阿拉平）",
     "e4 c5 c3 d5 exd5 Qxd5 d4 Nf6 Nf3 e6 Be2 Be7"),

    # ------------------------------------------------------ 1.e4 其他应法
    ("法兰西防御（古典变例）",
     "e4 e6 d4 d5 Nc3 Nf6 Bg5 Be7 e5 Nfd7 Bxe7 Qxe7 f4 O-O"),
    ("法兰西防御（维纳维尔）",
     "e4 e6 d4 d5 Nc3 Bb4 e5 c5 a3 Bxc3+ bxc3 Ne7 Qg4 Qc7"),
    ("法兰西防御（塔拉什）",
     "e4 e6 d4 d5 Nd2 c5 exd5 exd5 Ngf3 Nc6 Bb5 Bd6 O-O Ne7"),
    ("法兰西防御（进兵变例）",
     "e4 e6 d4 d5 e5 c5 c3 Nc6 Nf3 Qb6 a3 Bd7"),
    ("卡罗-卡恩防御（古典变例）",
     "e4 c6 d4 d5 Nc3 dxe4 Nxe4 Bf5 Ng3 Bg6 h4 h6 Nf3 Nd7 h5 Bh7 Bd3 Bxd3"),
    ("卡罗-卡恩防御（进兵变例）",
     "e4 c6 d4 d5 e5 Bf5 Nf3 e6 Be2 c5 Be3 Nd7"),
    ("卡罗-卡恩防御（交换变例）",
     "e4 c6 d4 d5 exd5 cxd5 Bd3 Nc6 c3 Nf6 Bf4 Bg4"),
    ("中心反击（斯堪的纳维亚）",
     "e4 d5 exd5 Qxd5 Nc3 Qa5 d4 Nf6 Nf3 c6 Bc4 Bf5 Bd2 e6"),
    ("皮尔茨防御",
     "e4 d6 d4 Nf6 Nc3 g6 Nf3 Bg7 Be2 O-O O-O c6 a4 Nbd7"),
    ("现代防御",
     "e4 g6 d4 Bg7 Nc3 d6 Nf3 a6 a4 Nf6"),
    ("阿廖欣防御",
     "e4 Nf6 e5 Nd5 d4 d6 Nf3 dxe5 Nxe5 c6 Be2 Bf5 O-O e6"),

    # ---------------------------------------------------------- 1.d4 d5
    ("后翼弃兵（拒后翼弃兵）",
     "d4 d5 c4 e6 Nc3 Nf6 Bg5 Be7 e3 O-O Nf3 h6 Bh4 b6"),
    ("后翼弃兵（接受）",
     "d4 d5 c4 dxc4 Nf3 Nf6 e3 e6 Bxc4 c5 O-O a6 dxc5 Qxd1"),
    ("斯拉夫防御",
     "d4 d5 c4 c6 Nf3 Nf6 Nc3 dxc4 a4 Bf5 e3 e6 Bxc4 Bb4"),
    ("半斯拉夫（梅兰变例）",
     "d4 d5 c4 c6 Nf3 Nf6 Nc3 e6 e3 Nbd7 Bd3 dxc4 Bxc4 b5 Bd3 Bb7"),
    ("伦敦体系",
     "d4 d5 Bf4 Nf6 e3 e6 Nf3 c5 c3 Nc6 Nbd2 Bd6 Bg3 O-O"),

    # ------------------------------------------------------ 1.d4 Nf6 印度
    ("尼姆佐维奇印度防御",
     "d4 Nf6 c4 e6 Nc3 Bb4 e3 O-O Bd3 d5 Nf3 c5 O-O Nc6"),
    ("后翼印度防御",
     "d4 Nf6 c4 e6 Nf3 b6 g3 Ba6 b3 Bb4+ Bd2 Be7 Bg2 c6 O-O d5"),
    ("加泰罗尼亚开局",
     "d4 Nf6 c4 e6 g3 d5 Bg2 Be7 Nf3 O-O O-O dxc4 Qc2 a6"),
    ("王翼印度防御（古典变例）",
     "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7"),
    ("格林菲尔德防御（交换变例）",
     "d4 Nf6 c4 g6 Nc3 d5 cxd5 Nxd5 e4 Nxc3 bxc3 Bg7 Nf3 c5 Rb1 O-O"),
    ("现代贝诺尼",
     "d4 Nf6 c4 c5 d5 e6 Nc3 exd5 cxd5 d6 e4 g6 Nf3 Bg7 Be2 O-O"),
    ("特朗波夫斯基",
     "d4 Nf6 Bg5 Ne4 Bf4 d5 e3 c5 Bd3 Nc6"),

    # -------------------------------------------------------------- 其他
    ("荷兰防御",
     "d4 f5 g3 Nf6 Bg2 e6 Nf3 Be7 O-O O-O c4 d6"),
    ("英国式开局（反西西里）",
     "c4 e5 Nc3 Nf6 Nf3 Nc6 g3 d5 cxd5 Nxd5 Bg2 Nb6 O-O Be7"),
    ("英国式开局（对称变例）",
     "c4 c5 Nf3 Nf6 d4 cxd4 Nxd4 e6 Nc3 Bb4 Ndb5 O-O"),
    ("列蒂开局",
     "Nf3 d5 c4 e6 g3 Nf6 Bg2 Be7 O-O O-O b3 c5"),
]


def _build():
    """展开成 {局面: {着法: 权重}} 和 {局面: 经过这里的所有开局名}。"""
    moves_by_key = {}
    names = {}
    problems = []
    for name, line in LINES:
        b = Board(START_FEN)
        for i, san in enumerate(pgn_moves(line)):
            m = b.parse_move(san)
            if m is None:
                problems.append((name, i + 1, san, b.fen()))
                break
            slot = moves_by_key.setdefault(b.key, {})
            slot[m] = slot.get(m, 0) + 1
            b.make(m)
            names.setdefault(b.key, set()).add(name)
    return moves_by_key, names, problems


BOOK, NAMES, PROBLEMS = _build()


def probe(board, rnd=None):
    """返回 (着法, 开局名) —— 局面不在库里就返回 (None, None)。"""
    slot = BOOK.get(board.key)
    if not slot:
        return None, None
    moves = list(slot.items())
    total = sum(w for _m, w in moves)
    pick = (rnd or random).uniform(0, total)
    acc = 0
    chosen = moves[0][0]
    for m, w in moves:
        acc += w
        if pick <= acc:
            chosen = m
            break
    board.make(chosen)
    name = current_name(board)
    board.unmake()
    return chosen, name


def current_name(board):
    """当前局面能确定是什么开局就返回名字，还看不出来就返回 None。

    很多条主变会经过同一个早期局面（1.e4 之后有二十来条），这时候报任何
    一个具体名字都是误导；只有收敛到一个开局、或者至少收敛到同一个大类
    （如「西西里防御」）时才给名字。
    """
    got = NAMES.get(board.key)
    if not got:
        return None
    if len(got) == 1:
        return next(iter(got))
    bases = set(n.split("（")[0] for n in got)
    return next(iter(bases)) if len(bases) == 1 else None


def stats():
    return {"lines": len(LINES), "positions": len(BOOK),
            "moves": sum(len(v) for v in BOOK.values()),
            "problems": PROBLEMS}
