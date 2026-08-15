"""Tactics puzzles and endgame drills.

Every entry here is verified by `python3 puzzles.py` (see validate()):
tactics must have a forced mate or a decisive material gain that is clearly
better than the second-best move; drills must actually be won/drawn.
"""

# (fen, theme, hint, kind)  kind: 'mate' | 'win'
TACTICS = [
    ("6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
     "底线杀", "黑王被自己的兵闷住了，第 8 横线是空的。", "mate"),
    ("3r2k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
     "底线杀", "对方的车挡在 d8，把它吃掉。", "mate"),
    ("6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1",
     "底线杀", "车走到第 8 线。", "mate"),
    ("7k/R7/8/8/8/8/8/1R6 w - - 0 1",
     "双车梯子杀", "一个车已经封住第 7 横线了。", "mate"),
    ("r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 4 4",
     "学者杀", "f7 只有王在守。", "mate"),
    ("rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq - 0 2",
     "傻瓜杀", "白方把王前面的斜线全打开了。", "mate"),
    ("r2q1bnr/ppp1kBpp/2np4/4N3/4P3/2N5/PPPP1PPP/R1BbK2R w KQ - 1 7",
     "勒加尔杀", "黑王在 e7 无处可逃，再来一个子将军。", "mate"),
    ("6rk/6pp/8/6N1/8/8/8/6K1 w - - 0 1",
     "闷杀", "黑王被自己的车和兵堵死了。", "mate"),
    ("6k1/5ppp/8/8/8/8/5PPP/Q5K1 w - - 0 1",
     "后的底线杀", "后能同时控制第 8 横线。", "mate"),
    ("6k1/8/8/3q4/4N3/8/8/6K1 w - - 0 1",
     "马的双叉", "找一个既将军又攻击后的马位。", "win"),
    ("r5k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1",
     "抢占直线", "先兑掉对方唯一的重子。", "mate"),
    ("2k5/8/8/8/8/8/1q6/1R2K3 w - - 0 1",
     "白吃一子", "对方的后没人保护。", "win"),
    ("6k1/6pp/8/8/8/3b4/6PP/3R2K1 w - - 0 1",
     "白吃一子", "象站在了车的直线上。", "win"),
    ("7k/8/1B6/8/8/8/7K/r7 w - - 0 1",
     "串击", "先将军，把王和车串在同一条斜线上。", "win"),
    # —— 来自 Jeremy 2026-08 实战（icea aug vs paul，第 28 手白方走 Qxe4?? 之后）——
    ("3rr1k1/p1b2pp1/1p2p2p/8/3PQP2/P1P1B1P1/1q2R2P/2R3K1 b - - 0 28",
     "跑掉的子原来在守什么",
     "白后刚从 d3 跑到 e4。它看着还在 e 线上，但 e3 站着自己的象。", "win"),
]

# (fen, name, goal, side_to_train)  goal: 'win' | 'draw'
DRILLS = [
    ("8/8/8/4k3/8/8/4K1R1/8 w - - 0 1", "单车杀王", "win", "w"),
    ("8/8/8/3k4/8/8/4K1Q1/8 w - - 0 1", "单后杀王", "win", "w"),
    ("8/8/8/8/3pk3/8/3PK3/8 w - - 0 1", "王兵对王兵", "draw", "w"),
    ("1K6/1P1k4/8/8/8/8/r7/2R5 w - - 0 1", "卢塞纳局面（车兵取胜）", "win", "w"),
    ("8/7K/8/3q4/8/8/8/3k4 b - - 0 1", "单后杀王（执黑）", "win", "b"),
    ("8/5k2/8/4K3/4P3/8/8/8 w - - 0 1", "王兵：抢占关键格", "win", "w"),
    ("8/8/8/8/8/5k2/5p2/5K2 w - - 0 1", "守和：正面挡兵", "draw", "w"),
    ("8/2k5/8/2K1P3/8/8/8/8 w - - 0 1", "王兵：越过关键格", "win", "w"),
    ("8/8/1k6/8/1K6/1P6/8/8 w - - 0 1", "王兵：边路推进", "win", "w"),
]


def validate(seconds=3.0, verbose=True):
    """Check every entry with the engine; returns (good_tactics, good_drills)."""
    from board import Board, WHITE
    from engine import Engine, MATE_BOUND, score_text

    eng = Engine()
    good_t, good_d = [], []
    for fen, theme, hint, kind in TACTICS:
        b = Board(fen)
        ranked = eng.rank_moves(b, 6, seconds)
        if not ranked:
            continue
        best_m, best_s = ranked[0]
        second = ranked[1][1] if len(ranked) > 1 else -99999
        is_mate = best_s > MATE_BOUND
        gap = best_s - second
        ok = is_mate if kind == "mate" else (gap >= 250 and not is_mate)
        if verbose:
            print("%-6s %-14s best=%-7s %-8s gap=%-6d %s"
                  % ("TACTIC", theme, b.san(best_m), score_text(best_s),
                     min(gap, 9999), "ok" if ok else "REJECT"))
        if ok:
            good_t.append((fen, theme, hint, kind, b.san(best_m), best_s))

    for fen, name, goal, side in DRILLS:
        b = Board(fen)
        r = eng.search(b, 30, seconds)
        s = r.score if b.side == WHITE else -r.score      # white's perspective
        want_white = (side == "w")
        val = s if want_white else -s                      # trainee's perspective
        if goal == "win":
            ok = val >= 200
        else:
            ok = abs(val) <= 90
        if verbose:
            print("%-6s %-22s eval=%-8s want=%-5s %s"
                  % ("DRILL", name, score_text(r.score), goal,
                     "ok" if ok else "REJECT"))
        if ok:
            good_d.append((fen, name, goal, side))
    return good_t, good_d


if __name__ == "__main__":
    import sys
    t, d = validate(float(sys.argv[1]) if len(sys.argv) > 1 else 3.0)
    print("\n%d/%d tactics, %d/%d drills passed"
          % (len(t), len(TACTICS), len(d), len(DRILLS)))
