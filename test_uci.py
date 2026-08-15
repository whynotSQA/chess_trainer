"""UCI 适配层测试。

装了 Stockfish 就直接测 Stockfish；没装就用 fake_uci.py（本项目引擎伪装成
UCI 引擎）跑一遍完整协议流程——真子进程、真管道、真解析。
"""

import os
import sys

from board import Board, START_FEN
from engine import mate_in
import uci


def make(elo=None):
    path = uci.find_stockfish()
    if path:
        return uci.UciEngine(path, elo=elo), "Stockfish (%s)" % path
    fake = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "fake_uci.py")
    eng = uci.UciEngine.__new__(uci.UciEngine)      # 手动指定假引擎的启动命令
    import subprocess
    import random
    import threading
    eng.path = fake
    eng.debug = False
    eng.rnd = random.Random(0)
    eng.nodes = 0
    eng._lock = threading.Lock()
    eng.proc = subprocess.Popen([sys.executable, fake],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL,
                                universal_newlines=True, bufsize=1)
    eng.name = "?"
    eng.options = {}
    eng._handshake()
    return eng, "fake_uci（没装 Stockfish，用本项目引擎代替）"


def main():
    ok = True
    eng, who = make()
    print("被测引擎: %s" % who)
    print("引擎自报: %s" % eng.name)
    print("支持限强度: %s" % ("是" if "UCI_LimitStrength" in eng.options
                              else "否"))

    # 1. 开局局面：给出的必须是合法着法，且棋盘不能被弄脏
    b = Board(START_FEN)
    fen = b.fen()
    r = eng.search(b, 64, 0.6)
    if not r.move or not b.is_legal(r.move):
        print("FAIL 开局给出的着法不合法")
        ok = False
    else:
        print("开局推荐 %-6s 评估 %+d  深度 %d  主变 %d 步"
              % (b.san(r.move), r.score, r.depth, len(r.pv)))
    if b.fen() != fen:
        print("FAIL 搜索之后棋盘状态被改了")
        ok = False

    # 2. 主变必须是一串能连续走下去的合法着法
    made = 0
    for m in r.pv:
        if not b.is_legal(m):
            print("FAIL 主变里有非法着法")
            ok = False
            break
        b.make(m)
        made += 1
    for _ in range(made):
        b.unmake()

    # 3. 将杀分数要能正确翻译
    b2 = Board("6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1")
    r2 = eng.search(b2, 64, 0.6)
    m2 = mate_in(r2.score)
    print("底线杀局面: %s，分数 %d → %s"
          % (b2.san(r2.move) if r2.move else "无", r2.score,
             ("%d 步杀" % m2) if m2 else "没识别成杀棋"))
    if m2 != 1:
        print("FAIL 一步杀没被识别成 mate 1")
        ok = False

    # 4. MultiPV
    b3 = Board("r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4")
    fen3 = b3.fen()
    ranked = eng.rank_moves(b3, 6, 1.0, k=4)
    print("候选着法: %s" % ", ".join("%s(%+d)" % (b3.san(m), s)
                                     for m, s in ranked))
    if len(ranked) < 2:
        print("FAIL MultiPV 没返回多个候选")
        ok = False
    for m, _s in ranked:
        if not b3.is_legal(m):
            print("FAIL 候选里有非法着法")
            ok = False
    if b3.fen() != fen3:
        print("FAIL rank_moves 之后棋盘被改了")
        ok = False

    # 5. 从任意 FEN 开始（含吃过路兵、易位权）也要正常
    for fen in ("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
                "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3"):
        bb = Board(fen)
        rr = eng.search(bb, 64, 0.4)
        if not rr.move or not bb.is_legal(rr.move):
            print("FAIL 这个局面给出的着法不合法: %s" % fen)
            ok = False
    print("各种局面下都给出合法着法")

    # 6. 连着下十来步不出错
    bb = Board(START_FEN)
    for _ in range(12):
        if bb.outcome():
            break
        rr = eng.search(bb, 64, 0.25)
        if not rr.move or not bb.is_legal(rr.move):
            print("FAIL 自对弈中出现非法着法")
            ok = False
            break
        bb.make(rr.move)
    print("连续对弈 12 步正常")

    eng.close()
    test_bounds_ignored()
    print("\n%s" % ("UCI 适配层测试通过" if ok else "有失败项"))
    return 0 if ok else 1


def test_bounds_ignored():
    """lowerbound / upperbound 是窗口边界，不是评估——必须忽略。

    真实报告里出现过 -70.45 这种评分，就是把边界行当成评分打印出来的。
    """
    import uci
    from board import Board, START_FEN
    b = Board(START_FEN)
    e = uci.UciEngine.__new__(uci.UciEngine)      # 不启动子进程
    sink = {}
    e._parse_info("info depth 20 score cp 35 pv e2e4 e7e5", b, sink)
    assert sink[1]["score"] == 35
    e._parse_info("info depth 21 score cp 7045 lowerbound pv e2e4", b, sink)
    assert sink[1]["score"] == 35, "lowerbound 不该覆盖评分"
    e._parse_info("info depth 21 score cp -8115 upperbound pv d2d4", b, sink)
    assert sink[1]["score"] == 35, "upperbound 不该覆盖评分"
    e._parse_info("info depth 22 score cp 41 pv d2d4 d7d5", b, sink)
    assert sink[1]["score"] == 41, "正常行应该更新评分"
    print("边界行忽略测试通过")


if __name__ == "__main__":
    sys.exit(main())
