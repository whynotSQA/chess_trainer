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
    # —— 来自 Jeremy 2026-08 实战（vs elijah，第 10 步该走 Nxc3 那条线里）——
    # 白马刚 Nxa8 吃了你的车，但它困在角里（逃格 b6/c7 被 a7 兵和 d8 王封死）。
    # 用将军抢先手，把它收下来。这就是他实战漏掉的「角落困马」。
    ("N1bk3r/pp1p1ppp/2n5/8/8/2n5/PPP2PPP/R3KB1R b KQ - 0 12",
     "困死角落的马",
     "a8 的白马跑不掉——b6、c7 都被你封着。先用一步将军把白王赶开，再收马。", "win"),
    # —— 「找一步赢子」马叉练习（为 Jeremy 专门加的，练一步制胜的眼力）——
    ("r3k3/pp6/8/1N6/8/8/6PP/6K1 w - - 0 1",
     "皇家叉：马叉王车", "马有一步同时将军黑王、又碰到黑车。", "win"),
    ("3r3k/pp6/8/4N3/8/8/6PP/6K1 w - - 0 1",
     "马叉王车", "马跳一步，既将军黑王角，又攻黑车。", "win"),
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
    # —— 来自 Jeremy 2026-08 实战（vs elijah，第 22 手，均势车马残局）——
    # 引擎评分约 0：这是一盘平局的残局。练的是「怎么别把它下输」：
    # 王要中心化、别把兵推成孤兵（实战他走了 ...b5 ...d4，两个孤兵被逐个吃掉）。
    ("3r2k1/1p3ppp/p3n3/3p4/8/2NK1PP1/PPP4P/4R3 b - - 0 22",
     "守住均势残局（王中心化、别造孤兵）", "draw", "b"),
    # —— 转化优势：执白多一整子，对着引擎下到赢。练「不松劲、下干净」——
    # 他执白最大的毛病就是拿到优势赢不下来（George 那盘）。多一子都转化不了，
    # 等于白拿。目标是赢，不是守。
    ("r3k2r/ppp2ppp/8/4p3/4P3/2N5/PPP2PPP/R3K2R w KQkq - 0 1",
     "转化优势：执白多一马（中局，带车）", "win", "w"),
    # 残局里转化——简化局面，练「多子怎么一步步收成杀」的技术，不是中局算杀。
    ("4k3/ppp2ppp/8/8/8/5B2/PPP2PPP/4K3 w - - 0 1",
     "转化优势：执白残局多一象", "win", "w"),
    ("4k3/ppp2ppp/8/8/8/2N5/PPP2PPP/4K3 w - - 0 1",
     "转化优势：执白残局多一马", "win", "w"),
    # 多交换子（车换象）+ 一兵：练「多的不多，但要稳稳换成胜局」。
    ("r4bk1/ppp2pp1/8/4p3/4P3/8/PPP2PPP/R3R1K1 w - - 0 1",
     "转化优势：执白多一交换子带一兵", "win", "w"),
]


# —— 小优势转化 ——
# 优势很小（多一交换子、多一兵这种），弱引擎静态分够不到 drill 的 +200 门槛，
# 所以**不走 validate()**；但材料和"客观占优"我都逐个核过。练的是「薄优势怎么
# 稳稳转化」——比多一整子难得多，正是他真实对局里把握不住的那种优势。
# (fen, 题名, 目标, 执方) —— 跟 DRILLS 同形，drill 模式会一起列出来。
CONVERT = [
    ("r4bk1/ppp2ppp/8/8/8/8/PPP2PPP/R3R1K1 w - - 0 1",
     "小优势：多一交换子（车换象）", "win", "w"),
    ("5nk1/1p3ppp/8/8/8/5N2/PP3PPP/6K1 w - - 0 1",
     "小优势：马残局多一兵（外路 a 兵）", "win", "w"),
    ("6k1/1b3ppp/8/8/8/5B2/P4PPP/6K1 w - - 0 1",
     "小优势：同色象残局多一兵", "win", "w"),
]


# —— 实战研究局面 ——
# 这些是从 Jeremy 对局里挑的「判断/计算」局面，**不是**自动题库里的强制战术，
# 所以不走 validate()（弱引擎认证不了深算组合或带补偿的得子）。答案是人工给的。
# (fen, 走子方 w/b, 题面, 最佳着, 为什么)
STUDY = [
    ("r2qk2r/n3b1p1/3p3p/pNpPpp2/4n1b1/P2QBN2/1PP1BPPP/3RR1K1 w kq f6 0 16",
     "w", "对手刚走 f5?? 把局面送了。别顺手吃子——找最强的一击。",
     "Nxe5", "引擎的制胜手是 16.Nxe5‼（chess.com 标 brilliancy）；"
             "实战走的 16.Nxa7 也仍占优，但不是最强。教训：拿到优势要去算"
             "最锋利的一击、把它转化掉，而不是'先吃个子稳一稳'。"),
    ("3qk2r/3rb1p1/3p3p/pQpPpp2/1P2n1b1/P3BN2/2P1BPPP/3RR1K1 b k b3 0 18",
     "b", "白方刚走 b4。黑方有一步赢子——看出来了吗？（也是白方走 b4 前"
          "该扫到的威胁。）",
     "Nc3", "18...Nc3! 一步同时叉白方的后(b5)、车(d1)、象(e2)——三叉，稳赢"
             "一个交换子。白方走 b4 之前只要扫一眼『对方有什么威胁』就能看见："
             "那匹马从第 14 步就蹲在 e4 盯着 c3。这就是 CCT 里的 T（威胁）。"),
    ("r3k1nr/ppp2ppp/2nq4/3p4/3P2b1/5N2/PPPN1PPP/R2QKB1R w KQkq - 2 8",
     "w", "法兰西交换局。黑方 Nc6 和 Bg4 都对着 d4。白方该怎么守 d4？",
     "c3", "必须 8.c3 用兵实守 d4。实战走的 8.Bd3?? 直接丢兵：d4 看似有 Nf3 守着，"
           "但那匹马被 Bg4 钉在 d1 的后上（g4–f3–e2–d1 一条线），一动就丢后——"
           "所以 d4 的守卫是假的。8...Nxd4! 白吃一兵，这盘就是这么输的。"
           "教训：算'我的子有没有人守'时，先确认那个守卫自己没被钉住。"),
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
