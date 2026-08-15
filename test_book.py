"""开局库自检：每一步必须合法，每条线的终局面评估必须在合理范围内。"""

import sys

import book
from board import Board, START_FEN, WHITE, pgn_moves
from engine import Engine, score_text

LIMIT = 200          # 终局面评估超过 ±2 兵就认为这条线可能抄错了


def main(seconds=0.6):
    ok = True
    st = book.stats()
    if st["problems"]:
        ok = False
        for name, i, san, fen in st["problems"]:
            print("非法着法: %-28s 第 %d 步 '%s'  局面 %s" % (name, i, san, fen))
    else:
        print("全部 %d 条主变的每一步都合法。" % st["lines"])

    eng = Engine()
    suspicious = 0
    for name, line in book.LINES:
        b = Board(START_FEN)
        sans = pgn_moves(line)
        broken = False
        for san in sans:
            m = b.parse_move(san)
            if m is None:
                broken = True
                break
            b.make(m)
        if broken:
            print("%-28s 无法走完，跳过评估" % name)
            ok = False
            continue
        eng.new_game()
        r = eng.search(b, 64, seconds)
        cp = r.score if b.side == WHITE else -r.score
        flag = ""
        if abs(cp) > LIMIT:
            flag = "  <-- 可疑，检查这条线"
            suspicious += 1
            ok = False
        print("%-28s %2d 步  白方视角 %-7s%s"
              % (name, len(sans), score_text(cp), flag))

    print("\n开局库: %d 条主变 / %d 个局面 / %d 个着法"
          % (st["lines"], st["positions"], st["moves"]))

    # 探测功能本身
    b = Board(START_FEN)
    seen = set()
    for _ in range(60):
        m, nm = book.probe(b)
        if m is None:
            break
        seen.add(nm)
    for line, expect_named in (("e4", False), ("e4 e5", False),
                               ("e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3", True),
                               ("d4 Nf6 c4 g6 Nc3 d5", True)):
        b = Board(START_FEN)
        for san in line.split():
            b.make(b.parse_move(san))
        nm = book.current_name(b)
        m, nxt = book.probe(b)
        print("%-34s 开局判定: %-14s 库里下一步: %s"
              % (line, nm or "（还看不出）", b.san(m) if m else "无"))
        if m is None:
            ok = False
        if expect_named and not nm:
            print("   ^ 这里本该能判定出开局名")
            ok = False
        if not expect_named and nm:
            print("   ^ 这么早不该断言开局名")
            ok = False
    b = Board(START_FEN)
    b.make(b.parse_move("e4"))
    fen_before = b.fen()
    book.probe(b)
    if b.fen() != fen_before:
        print("probe 破坏了棋盘状态！")
        ok = False

    print("\n%s" % ("开局库检查通过" if ok else "有 %d 条线需要复查" % suspicious))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(float(sys.argv[1]) if len(sys.argv) > 1 else 0.6))
