"""End-to-end sanity tests: self-play games plus board-state consistency.

Every ply asserts that the board stack, the move log and the FEN move counter
stay in sync, and that the engine never corrupts the position.
"""

import random
import sys

import trainer
from board import Board, WHITE, BLACK, START_FEN
from engine import Engine, choose_move, evaluate


def check_sync(s, plies):
    assert len(s.b.history) == plies, (len(s.b.history), plies)
    assert len(s.log) == plies, (len(s.log), plies)
    expect_full = 1 + (plies + (1 if Board(s.start_fen).side == BLACK else 0)) // 2
    assert s.b.fullmove == expect_full, (s.b.fullmove, expect_full, plies)
    assert s.b.side == (WHITE if plies % 2 == 0 else BLACK) or \
        Board(s.start_fen).side == BLACK


def selfplay(level_a, level_b, coach, max_plies=80, seed=0):
    rnd = random.Random(seed)
    s = trainer.Session(START_FEN, WHITE, level_a, coach)
    s.coach_secs = 0.08                      # keep the test suite quick
    plies = 0
    while s.b.outcome() is None and plies < max_plies:
        if s.b.side == WHITE:
            legal = s.b.legal_moves()
            m = rnd.choice(legal) if rnd.random() < 0.35 else \
                choose_move(s.eng, s.b, level_a).move
            fen_before = s.b.fen()
            s.human_move(m)
            assert Board(fen_before).fen() == fen_before
        else:
            s.level = level_b
            if not s.engine_move():
                break
        plies += 1
        check_sync(s, plies)
        if plies % 7 == 0:                      # exercise the analysis paths
            s.eval_note()
            r = s.best(0.15)
            trainer.pv_san(s.b, r.pv, 6)
            check_sync(s, plies)
    return s, plies


def main():
    random.seed(7)
    ok = True
    for i, (la, lb, coach) in enumerate([(3, 4, True), (1, 4, False),
                                         (4, 2, True)]):
        s, plies = selfplay(la, lb, coach, 26, seed=i)
        out = s.b.outcome()
        print("game %d: L%d vs L%d coach=%-5s %3d plies -> %s"
              % (i + 1, la, lb, coach, plies, out or "unfinished"))
        # replay the PGN from scratch and confirm it reproduces the position
        sans = [x[0] for x in s.log]
        b2 = Board(START_FEN)
        for san in sans:
            m = b2.parse_move(san)
            if m is None:
                print("   PGN replay FAILED at", san)
                ok = False
                break
            b2.make(m)
        else:
            if b2.fen() != s.b.fen():
                print("   replay mismatch:\n   %s\n   %s" % (b2.fen(), s.b.fen()))
                ok = False
            else:
                print("   SAN replay ok (%d plies)" % len(sans))

    # undo consistency
    s = trainer.Session(START_FEN, WHITE, 2, False)
    rnd = random.Random(11)
    for _ in range(3):
        s.human_move(rnd.choice(s.b.legal_moves()))
        s.engine_move()
    fen6 = s.b.fen()
    s.human_move(rnd.choice(s.b.legal_moves()))
    s.engine_move()
    for _ in range(2):
        s.b.unmake()
        s.log.pop()
    if s.b.fen() != fen6:
        print("undo FAILED\n  %s\n  %s" % (s.b.fen(), fen6))
        ok = False
    else:
        print("undo ok")

    # evaluation symmetry: a mirrored position must evaluate to the mirror score
    for fen in ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
                "8/5k2/8/4K3/4P3/8/8/8 w - - 0 1"):
        b = Board(fen)
        rows = fen.split()[0].split("/")
        flipped = "/".join(r.swapcase() for r in reversed(rows))
        rest = fen.split()
        cast = rest[2].swapcase() if rest[2] != "-" else "-"
        b2 = Board("%s %s %s - 0 1" % (flipped, "b" if rest[1] == "w" else "w",
                                       "".join(sorted(cast))))
        e1, e2 = evaluate(b), evaluate(b2)
        if e1 != e2:
            print("eval symmetry FAILED %d vs %d for %s" % (e1, e2, fen))
            ok = False
    print("eval symmetry ok")

    # review pipeline
    txt = trainer.review_moves(START_FEN,
                               ["e4", "e5", "Nf3", "Nc6", "Bc4", "Nf6",
                                "Ng5", "d5"],
                               0.12)
    if "复盘报告" not in txt:
        ok = False
    print("\n%s" % ("ALL SELF-PLAY TESTS PASSED" if ok else "FAILURES PRESENT"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
