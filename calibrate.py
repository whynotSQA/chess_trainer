# -*- coding: utf-8 -*-
"""用 Stockfish 的 UCI_Elo 当尺子，量一量本项目引擎每个等级值多少分。

    python3 calibrate.py --level 5 --elo 1500 --games 20
    python3 calibrate.py --level 5 --auto            # 自动上下找
    python3 calibrate.py --all                       # 把 1-8 级都量一遍（很慢）

原理：让本引擎的 L 级和限定到 E 分的 Stockfish 下 N 盘（轮流执先），
按得分率 p 反推分差 d = -400·log10(1/p - 1)，本级的分 ≈ E + d。

必须知道的四件事：

1. **量出来的是 CCRL 40/4 尺度的分，不是 USCF，也不是 FIDE。**
   Stockfish 官方文档原话：UCI_Elo "has been calibrated at a time control of
   120s+1s and anchored to CCRL 40/4"。CCRL 是引擎之间对下形成的分数池，
   跟人类等级分之间没有官方换算关系。
2. 它是按 **120秒+1秒** 标定的。给的时间越少，Stockfish 越弱于它的标称分，
   结果就越偏向被测方。所以 --sf-time 别设太小（默认 1 秒已经偏少了，
   想准就设 2 秒以上，代价是很慢）。
3. 20 盘棋的统计误差 ±100 分起步，别把结果当精确值。
4. 换台电脑、换时间控制，结果都会变。
"""

import argparse
import math
import random
import sys
import time

import book
from board import Board, START_FEN, WHITE, BLACK
from engine import Engine, choose_move, LEVELS
import uci

MAX_PLIES = 160
ADJUDICATE_CP = 900          # 一方优势超过这么多且持续几步就判负
ADJUDICATE_HOLD = 4


def elo_diff(score_rate):
    """得分率 → 分差。0/1 会被夹住，避免无穷大。"""
    p = min(max(score_rate, 0.005), 0.995)
    return -400.0 * math.log10(1.0 / p - 1.0)


def confidence(score_rate, n):
    """粗略的 95% 置信区间（正态近似），返回 (低, 高) 分差。"""
    p = min(max(score_rate, 0.005), 0.995)
    se = math.sqrt(max(p * (1 - p), 0.0025) / max(n, 1))
    return elo_diff(p - 1.96 * se), elo_diff(p + 1.96 * se)


def opening_plies(rnd, plies=8):
    """从开局库随机走开头几步，保证每盘棋不一样。"""
    b = Board(START_FEN)
    for _ in range(plies):
        m, _n = book.probe(b, rnd)
        if m is None:
            break
        b.make(m)
    return b


def play_game(mine, level, sf, sf_movetime, my_color, rnd, verbose=False):
    """下一盘。返回本引擎的得分 1 / 0.5 / 0。"""
    b = opening_plies(rnd)
    mine.new_game()
    sf.new_game()
    hold = 0
    while True:
        out = b.outcome()
        if out:
            res = out[0]
            if res == "1/2-1/2":
                return 0.5
            winner = WHITE if res == "1-0" else BLACK
            return 1.0 if winner == my_color else 0.0
        if len(b.history) > MAX_PLIES:
            return 0.5
        if b.side == my_color:
            r = choose_move(mine, b, level)
        else:
            r = sf.search(b, 64, sf_movetime)
        if not r.move:
            return 0.5
        b.make(r.move)
        # 用 Stockfish 的评估做裁决，免得赢定的棋还要磨几十步（裁决不用想太久）
        judge = sf.search(b, 64, min(0.3, max(0.1, sf_movetime / 4)))
        cp = judge.score if b.side == WHITE else -judge.score   # 白方视角
        mine_cp = cp if my_color == WHITE else -cp
        if abs(mine_cp) > ADJUDICATE_CP:
            hold += 1
            if hold >= ADJUDICATE_HOLD:
                return 1.0 if mine_cp > 0 else 0.0
        else:
            hold = 0
        if verbose:
            sys.stdout.write(".")
            sys.stdout.flush()


def run_match(level, elo, games, sf_movetime, seed=0, verbose=True):
    sf = uci.UciEngine(elo=elo)
    mine = Engine(seed=seed)
    rnd = random.Random(seed)
    pts = 0.0
    w = d = l = 0
    t0 = time.time()
    for i in range(games):
        my_color = WHITE if i % 2 == 0 else BLACK
        s = play_game(mine, level, sf, sf_movetime, my_color, rnd)
        pts += s
        w += s == 1.0
        d += s == 0.5
        l += s == 0.0
        if verbose:
            print("  第 %2d 盘 本引擎执%s → %s   （累计 %.1f/%d）"
                  % (i + 1, "白" if my_color == WHITE else "黑",
                     {1.0: "胜", 0.5: "和", 0.0: "负"}[s], pts, i + 1))
    sf.close()
    rate = pts / games
    d_elo = elo_diff(rate)
    lo, hi = confidence(rate, games)
    return {"level": level, "sf_elo": elo, "games": games, "points": pts,
            "sf_time": sf_movetime,
            "rate": rate, "w": w, "d": d, "l": l, "elo": elo + d_elo,
            "lo": elo + lo, "hi": elo + hi, "secs": time.time() - t0}


def report(res):
    print("\nL%d  vs  Stockfish@%d（CCRL 40/4 尺度）：%.1f/%d"
          "（%d胜 %d和 %d负，得分率 %.0f%%）"
          % (res["level"], res["sf_elo"], res["points"], res["games"],
             res["w"], res["d"], res["l"], res["rate"] * 100))
    print("推算强度 ≈ %d 分（CCRL 40/4 尺度，不是 USCF/FIDE）"
          "   95%% 区间 %d ~ %d   （用时 %.0f 秒）"
          % (round(res["elo"]), round(res["lo"]), round(res["hi"]),
             res["secs"]))
    if res["sf_time"] < 1.0:
        print("警告：只给了 Stockfish 每步 %.2f 秒，远低于它标定用的 120s+1s，"
              "它会比标称分弱，这个结果偏高。" % res["sf_time"])
    if res["w"] + res["d"] == 0 or res["l"] + res["d"] == 0:
        print("注意：一边倒的结果说明尺子选得不合适，换个 --elo 再测一次更准。")


def auto(level, games, sf_movetime, start=1500, rounds=3, seed=0):
    """粗略二分：结果一边倒就调整对手强度再来一轮。"""
    elo = start
    res = None
    for k in range(rounds):
        step = max(120, 400 >> k)
        print("\n=== 第 %d 轮：对手设为 %d 分 ===" % (k + 1, elo))
        res = run_match(level, elo, games, sf_movetime, seed + k)
        report(res)
        if 0.25 <= res["rate"] <= 0.75:
            break
        elo = int(max(1320, min(2800, elo + (step if res["rate"] > 0.75
                                             else -step))))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=5, help="要测本引擎的哪一级")
    ap.add_argument("--elo", type=int, default=1500, help="Stockfish 限到多少分")
    ap.add_argument("--games", type=int, default=20)
    ap.add_argument("--sf-time", type=float, default=1.0,
                    help="Stockfish 每步用时（秒）。它的等级分是按 120s+1s 标定的，"
                         "给得越少结果越偏高；想准就设 2 以上")
    ap.add_argument("--auto", action="store_true", help="自动找合适的对手强度")
    ap.add_argument("--all", action="store_true", help="1-8 级全测（很慢）")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    info = uci.describe()
    if not info:
        print("没找到 Stockfish。先装：brew install stockfish")
        return 1
    print("对手：%s\n" % info)

    if a.all:
        rows = []
        for lv in range(1, 9):
            print("\n########## L%d ##########" % lv)
            rows.append(auto(lv, max(8, a.games // 2), a.sf_time, seed=a.seed))
        print("\n\n========== 汇总 ==========")
        for r in rows:
            print("L%-2d  ≈ %4d 分   (95%% 区间 %d~%d，%d 盘)"
                  % (r["level"], round(r["elo"]), round(r["lo"]),
                     round(r["hi"]), r["games"]))
        print("\n以上是 CCRL 40/4 尺度的实测值，不是 USCF/FIDE。"
              "样本小，误差大，但至少不是编的。")
        return 0

    if a.auto:
        auto(a.level, a.games, a.sf_time, a.elo, seed=a.seed)
    else:
        report(run_match(a.level, a.elo, a.games, a.sf_time, a.seed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
