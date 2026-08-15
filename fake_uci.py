#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一个用本项目引擎实现的 UCI 引擎，只为测试 uci.py 适配层。

这样即使机器上没装 Stockfish，也能把适配层的协议处理跑一遍真流程
（真子进程、真管道、真 info/bestmove 解析）。

    python3 fake_uci.py        # 手动玩：输入 uci / position startpos / go movetime 500
"""

import sys

from board import Board, START_FEN, move_uci
from engine import Engine, MATE, MATE_BOUND, mate_in


def out(s):
    sys.stdout.write(s + "\n")
    sys.stdout.flush()


def cp_to_uci(score):
    m = mate_in(score)
    if m is not None:
        return "mate %d" % m
    return "cp %d" % score


def main():
    board = Board(START_FEN)
    eng = Engine()
    multipv = 1
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        if line == "uci":
            out("id name FakeUCI (本项目引擎)")
            out("id author chess_trainer")
            out("option name Threads type spin default 1 min 1 max 1")
            out("option name Hash type spin default 16 min 1 max 128")
            out("option name MultiPV type spin default 1 min 1 max 32")
            out("option name UCI_LimitStrength type check default false")
            out("option name UCI_Elo type spin default 1500 min 800 max 2200")
            out("uciok")
        elif line == "isready":
            out("readyok")
        elif line == "ucinewgame":
            eng.new_game()
        elif line.startswith("setoption"):
            if "MultiPV" in line:
                try:
                    multipv = int(line.split("value")[1])
                except (IndexError, ValueError):
                    multipv = 1
        elif line.startswith("position"):
            rest = line[len("position"):].strip()
            moves = []
            if " moves " in rest:
                rest, mv = rest.split(" moves ", 1)
                moves = mv.split()
            rest = rest.strip()
            if rest.startswith("startpos"):
                board = Board(START_FEN)
            elif rest.startswith("fen"):
                board = Board(rest[3:].strip())
            for u in moves:
                m = board.parse_move(u)
                if m is None:
                    break
                board.make(m)
        elif line.startswith("go"):
            toks = line.split()
            depth, movetime = 64, 1.0
            for i, t in enumerate(toks):
                if t == "depth" and i + 1 < len(toks):
                    depth = int(toks[i + 1])
                elif t == "movetime" and i + 1 < len(toks):
                    movetime = int(toks[i + 1]) / 1000.0
            if multipv > 1:
                ranked = eng.rank_moves(board, min(depth, 6), movetime)
                for i, (m, s) in enumerate(ranked[:multipv], 1):
                    out("info depth %d multipv %d score %s nodes %d pv %s"
                        % (min(depth, 6), i, cp_to_uci(s), eng.nodes,
                           move_uci(m)))
                best = ranked[0][0] if ranked else 0
            else:
                r = eng.search(board, depth, movetime)
                if r.move:
                    out("info depth %d score %s nodes %d time %d pv %s"
                        % (r.depth, cp_to_uci(r.score), r.nodes,
                           int(r.elapsed * 1000),
                           " ".join(move_uci(m) for m in r.pv)))
                best = r.move
            out("bestmove %s" % (move_uci(best) if best else "(none)"))
        elif line == "quit":
            return
        elif line == "d":
            out(board.render())


if __name__ == "__main__":
    main()
