# -*- coding: utf-8 -*-
"""冒烟测试：把几条主路径真的跑一遍。

为什么需要这个：`import trainer` 只检查语法，不会执行函数体。改代码时误删了
一个函数（真事：重写 make_engine 时把 is_decided 一起覆盖了），导入照样通过，
一直到复盘跑到一半才 NameError。这里的每个用例都会**真的调用**那些函数。

跑得快（几秒），可以每次改完都跑一遍：

    python3 test_smoke.py
"""

import io
import sys

from board import Board, START_FEN, WHITE, BLACK
from engine import Engine

SHORT = ("e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Be7 Re1 b5 Bb3 d6 c3 O-O "
         "h3 Nb8 d4 Nbd7").split()


class Quiet(object):
    """把 stdout 收起来，只在出错时打出来。"""

    def __enter__(self):
        self.old = sys.stdout
        sys.stdout = self.buf = io.StringIO()
        return self

    def __exit__(self, *a):
        sys.stdout = self.old
        return False


def test_review():
    """复盘：会用到 is_decided / errors.classify / structure.notes。"""
    import trainer
    with Quiet() as q:
        text = trainer.review_moves(START_FEN, SHORT, 0.05)
    assert "复盘报告" in text, "报告没生成"
    assert "分析引擎" in text, "报告头没记引擎"
    assert "平均损失" in text, "统计行缺失"
    print("复盘主路径 ok")


def test_review_with_profile():
    """带学生档案的复盘（走 profile_log 那条路）。"""
    import os
    import trainer
    import profile_log
    name = "_冒烟测试"
    p = profile_log.path_for(name)
    if os.path.exists(p):
        os.remove(p)
    with Quiet():
        trainer.review_moves(START_FEN, SHORT, 0.05,
                             student=name, student_side=WHITE, result="1-0")
    rows = profile_log.load(name)
    assert len(rows) == 1, "档案没记上"
    assert rows[0]["color"] == "白"
    with Quiet():
        rep = profile_log.report(name)
    assert name in rep
    os.remove(p)
    print("学生档案主路径 ok")


def test_advise_levels():
    """跟棋建议：满血、设难度、以及棋盘状态不能被弄坏。"""
    import trainer
    fen = "r2q1rk1/p4ppp/1pnbpn2/3p4/3P4/1NPQ1N2/PP3PPP/R1B2RK1 w - - 0 13"
    for lv in (None, 3, 9):
        b = Board(fen)
        with Quiet():
            r = trainer.advise(Engine(), b, 0.15, verbose=True,
                               use_book=False, level=lv)
        assert r and r.move, "level=%s 没给出着法" % lv
        assert b.fen() == fen, "level=%s 把棋盘弄坏了" % lv
    print("跟棋建议主路径 ok")


def test_decided_boundary():
    """胜负已定的判据（这个函数被误删过一次）。"""
    from trainer import is_decided
    assert is_decided(1930, 1710)
    assert not is_decided(600, 200), "从赢定掉回没定，必须算"
    print("胜负已定判据 ok")


def test_review_name():
    """报告名跟棋谱名一一对应。"""
    import os
    from trainer import review_name
    for src, want in (("games/jvaichi.pgn", "review_jvaichi.txt"),
                      ("/tmp/a b/Jeremy_R3.PGN", "review_Jeremy_R3.txt"),
                      ("games/game_20260812_2144.pgn",
                       "review_game_20260812_2144.txt")):
        got = os.path.basename(review_name(src))
        assert got == want, "%s → %s（应为 %s）" % (src, got, want)
    # 没有源文件（粘贴进来的）才退回时间戳
    n = os.path.basename(review_name(None))
    assert n.startswith("review_") and n.endswith(".txt") and len(n) == 26, n
    print("复盘报告命名 ok")


def test_blind_sources():
    """盲区训练取局面的两条路。"""
    import random
    import blindspot as bs
    pool, per, fresh = bs.positions_from_dir("games", random.Random(1),
                                             want=4, seen=set())
    assert pool and per and fresh == sum(c for _f, c in per)
    why = []
    assert bs.positions_from_dir("games", random.Random(1), want=4,
                                 match="不存在的名字", why=why)[0] == []
    assert why, "取不到局面时要说明原因"
    print("盲区训练取局面 ok")


def main():
    for fn in (test_decided_boundary, test_review_name, test_review,
               test_review_with_profile, test_advise_levels,
               test_blind_sources):
        fn()
    print("\n冒烟测试全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
