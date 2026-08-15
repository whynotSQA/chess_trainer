"""盲区训练底层计算的测试：SEE / 白吃清单 / 将军吃子清单 / 威胁。"""

import sys

from board import Board, WHITE, BLACK, sq_name, name_sq
from engine import Engine
import blindspot as bs

# 经典 SEE 测试局面（chessprogramming wiki 的两个例子）+ 几个手算得出的
SEE_CASES = [
    # (FEN, 着法, 期望值, 说明)
    ("1k1r4/1pp4p/p7/4p3/8/P5P1/1PP4P/2K1R3 w - - 0 1", "Rxe5", 100,
     "车吃兵，对方车吃回来但白方不必再吃：净 +1 兵"),
    ("1k1r3q/1ppn3p/p4b2/4p3/8/P2N2P1/1PP1R1BP/2K1Q3 w - - 0 1", "Nxe5", -220,
     "马吃兵，一长串兑子之后净亏（本项目马=320象=330，故与经典值 -200 差 20）"),
    ("4k3/8/8/3p4/8/8/8/3RK3 w - - 0 1", "Rxd5", 100,
     "白吃一个无保护的兵"),
    ("4k3/8/4p3/3p4/8/8/8/3RK3 w - - 0 1", "Rxd5", -400,
     "d5 兵有 e6 兵保护，车吃亏一个车换一个兵"),
    ("4k3/8/4p3/3p4/8/8/3R4/3RK3 w - - 0 1", "Rxd5", -400,
     "叠车也没用，第一个车换一个兵之后就该停手"),
    ("3rk3/8/4p3/3p4/8/8/3R4/3RK3 w - - 0 1", "Rxd5", -400,
     "双方都有后备子，仍然是白亏一个车换一个兵"),
    ("4k3/8/8/3q4/8/8/8/3RK3 w - - 0 1", "Rxd5", 900,
     "白吃一个无保护的后"),
    ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "e4", 0,
     "普通推兵，不涉及兑子"),
]


def test_see():
    ok = True
    print("== 静态兑子(SEE) ==")
    for fen, san, expect, why in SEE_CASES:
        b = Board(fen)
        m = b.parse_move(san)
        if m is None:
            print("  FAIL 着法不合法: %s @ %s" % (san, fen))
            ok = False
            continue
        got = bs.see(b, m)
        flag = "ok " if got == expect else "FAIL"
        if got != expect:
            ok = False
        print("  %s %-6s 期望 %+5d 实得 %+5d   %s" % (flag, san, expect, got, why))
        if b.fen() != fen:
            print("  FAIL SEE 改动了棋盘")
            ok = False

    # 用经典的 P=100 N=B=300 R=500 Q=900 复现 chessprogramming wiki 上公布的两个值
    classic = dict(bs.SEE_VALUE)
    saved = dict(bs.SEE_VALUE)
    from board import KNIGHT, BISHOP
    classic[KNIGHT] = 300
    classic[BISHOP] = 300
    bs.SEE_VALUE.update(classic)
    try:
        for fen, san, expect in [
                ("1k1r4/1pp4p/p7/4p3/8/P5P1/1PP4P/2K1R3 w - - 0 1", "Rxe5", 100),
                ("1k1r3q/1ppn3p/p4b2/4p3/8/P2N2P1/1PP1R1BP/2K1Q3 w - - 0 1",
                 "Nxe5", -200)]:
            b = Board(fen)
            got = bs.see(b, b.parse_move(san))
            flag = "ok " if got == expect else "FAIL"
            if got != expect:
                ok = False
            print("  %s %-6s 经典子力值下 期望 %+5d 实得 %+5d   （对照公开数据）"
                  % (flag, san, expect, got))
    finally:
        bs.SEE_VALUE.update(saved)
    return ok


def test_hanging():
    ok = True
    print("\n== 白吃清单 ==")
    cases = [
        # 黑后在 d5 无保护，白车在 d1 → 黑方有一个子挂着
        ("4k3/8/8/3q4/8/8/8/3RK3 b - - 0 1", BLACK, ["d5"]),
        # 兵保护着的兵不算挂
        ("4k3/8/4p3/3p4/8/8/8/3RK3 b - - 0 1", BLACK, []),
        # 开局谁都不挂
        (Board().fen(), WHITE, []),
    ]
    for fen, color, expect in cases:
        b = Board(fen)
        got = sorted(sq_name(s) for s, _t, _v in bs.hanging(b, color))
        flag = "ok " if got == sorted(expect) else "FAIL"
        if got != sorted(expect):
            ok = False
        print("  %s %-46s 期望 %-10s 实得 %s"
              % (flag, fen[:44], expect or "无", got or "无"))
    return ok


def test_cc():
    ok = True
    print("\n== 将军与吃子清单 ==")
    b = Board("r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4")
    got = sorted(b.san(m) for m, _c, _k in bs.checks_and_captures(b))
    print("  意大利开局局面: %s" % ", ".join(got))
    # Nxe5 和 Bxf7+ 都必须在清单里
    for must in ("Nxe5", "Bxf7+"):
        if must not in got:
            print("  FAIL 漏了 %s" % must)
            ok = False
    # 清单里的每一步都必须真的是吃子或将军
    for m, is_cap, gives in bs.checks_and_captures(b):
        if not is_cap and not gives:
            print("  FAIL 清单里混进了既不吃子也不将军的着法")
            ok = False
    # 起始局面：无吃子无将军
    if bs.checks_and_captures(Board()):
        print("  FAIL 起始局面不该有将军或吃子")
        ok = False
    else:
        print("  起始局面: 无（正确）")
    return ok


def test_threat():
    ok = True
    print("\n== 对手威胁（空着搜索） ==")
    eng = Engine()
    # 白方 Qh5 已经威胁 Qxf7#，轮到黑走：黑方眼里对手的威胁应该是 Qxf7#
    b = Board("rnbqkbnr/pppp1ppp/8/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 2 3")
    fen = b.fen()
    t = bs.threat(eng, b, 1.0)
    if t is None:
        print("  FAIL 没算出威胁")
        return False
    m, sc, _now = t
    b.make_null()
    san = b.san(m)
    b.unmake_null()
    print("  黑方要提防的是: %s (%+d)" % (san, sc))
    if san.rstrip("+#") != "Qxf7":
        print("  FAIL 没识别出 Qxf7# 这个威胁")
        ok = False
    if b.fen() != fen:
        print("  FAIL threat() 改动了棋盘")
        ok = False
    return ok


def test_position_source():
    print("\n== 练习局面生成 ==")
    import random
    eng = Engine()
    rnd = random.Random(3)
    okc = 0
    for _ in range(4):
        b = bs.random_position(eng, rnd, 12, 30, level=3)
        if b.legal_moves():
            okc += 1
    print("  自对弈生成 %d/4 个可用局面" % okc)
    return okc == 4


def test_drill_grading():
    """判卷逻辑：喂进已知答案，检查得分对不对。"""
    print("\n== 判卷逻辑 ==")
    import trainer
    ok = True
    saved_ask = trainer.ask
    eng = Engine()

    def run(fn, fen, answer, expect):
        trainer.ask = lambda _p="": answer
        b = Board(fen)
        before = b.fen()
        got = fn(b, eng, 0.4)
        flag = "ok " if got == expect else "FAIL"
        if got != expect:
            nonlocal ok
            ok = False
        print("  %s %-22s 答「%-12s」→ %s（期望 %s）"
              % (flag, fn.__name__, answer, got, expect))
        if b.fen() != before:
            print("  FAIL 判卷过程改动了棋盘")
            ok = False

    italian = "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"
    try:
        run(trainer.drill_checks_captures, italian, "Nxe5 Bxf7+", (2, 2))
        run(trainer.drill_checks_captures, italian, "Nxe5", (1, 2))
        run(trainer.drill_checks_captures, italian, "无", (0, 2))
        run(trainer.drill_hanging, "4k3/8/8/3q4/8/8/8/3RK3 b - - 0 1",
            "d5", (1, 1))
        run(trainer.drill_hanging, "4k3/8/8/3q4/8/8/8/3RK3 b - - 0 1",
            "无", (0, 1))
        run(trainer.drill_threat,
            "rnbqkbnr/pppp1ppp/8/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 2 3",
            "Qxf7", (1, 1))
        run(trainer.drill_threat,
            "rnbqkbnr/pppp1ppp/8/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 2 3",
            "a3", (0, 1))
    finally:
        trainer.ask = saved_ask
    return ok


def main():
    ok = all([test_see(), test_hanging(), test_cc(), test_threat(),
              test_position_source(), test_drill_grading()])
    print("\n%s" % ("盲区训练模块测试通过" if ok else "有失败项"))
    return 0 if ok else 1


def test_seen_filter():
    """练过的局面要排到后面去——这里踩过一个变量重名的坑，加个回归。"""
    import random
    import blindspot as bs
    pool, per, n_fresh = bs.positions_from_dir("games", random.Random(1),
                                               want=5, seen=set())
    total = sum(c for _f, c in per)
    assert n_fresh == total, "空的 seen 应该全部算「没练过」，得到 %d/%d" % (n_fresh, total)
    assert pool, "应该取到局面"
    first = {b.fen() for b in pool}
    pool2, _p, n2 = bs.positions_from_dir("games", random.Random(2),
                                          want=5, seen=first)
    assert n2 == total - len(first), "练过的应该从 fresh 里扣掉"
    assert not (first & {b.fen() for b in pool2}), "练过的不该再排在前面"
    print("已练过的局面排后测试通过")


def test_decided():
    """胜负已定之后的丢分不该计入统计（+19 掉到 +17 不是「崩」）。"""
    from trainer import is_decided
    assert is_decided(1930, 1710), "+19.3 → +17.1 应该算已定"
    assert is_decided(-800, -1200), "已经输定了，再掉也算已定"
    assert not is_decided(407, 240), "+4.07 → +2.40 还没定，要算"
    assert not is_decided(600, 200), "从赢定掉回没定，必须算——这才是真的崩"
    assert not is_decided(-600, 300), "符号都反了，当然算"
    print("胜负已定过滤测试通过")


if __name__ == "__main__":
    sys.exit(main())