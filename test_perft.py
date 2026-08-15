"""Move-generation correctness tests (perft) against published node counts."""
import sys
import time
from board import Board

SUITE = [
    ("startpos", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
     [20, 400, 8902, 197281, 4865609]),
    ("kiwipete",
     "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
     [48, 2039, 97862, 4085603]),
    ("position3", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
     [14, 191, 2812, 43238, 674624]),
    ("position4",
     "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
     [6, 264, 9467, 422333]),
    ("position5",
     "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
     [44, 1486, 62379, 2103487]),
    ("position6",
     "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",
     [46, 2079, 89890, 3894594]),
]


def perft(b, depth):
    if depth == 0:
        return 1
    moves = b.gen_moves()
    me = b.side
    if depth == 1:
        n = 0
        for m in moves:
            b.make(m)
            if not b.is_attacked(b.kings[me], b.side):
                n += 1
            b.unmake()
        return n
    n = 0
    for m in moves:
        b.make(m)
        if not b.is_attacked(b.kings[me], b.side):
            n += perft(b, depth - 1)
        b.unmake()
    return n


def main(maxnodes=250000):
    ok = True
    t0 = time.time()
    for name, fen, expected in SUITE:
        for d, exp in enumerate(expected, 1):
            if exp > maxnodes:
                continue
            b = Board(fen)
            key_before, fen_before = b.key, b.fen()
            got = perft(b, d)
            status = "ok " if got == exp else "FAIL"
            if got != exp:
                ok = False
            if b.key != key_before or b.fen() != fen_before:
                status, ok = "FAIL(state)", False
            print("%-10s depth %d  expected %-9d got %-9d %s"
                  % (name, d, exp, got, status))
    print("\n%s   (%.1fs)" % ("ALL TESTS PASSED" if ok else "FAILURES PRESENT",
                              time.time() - t0))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 250000))
