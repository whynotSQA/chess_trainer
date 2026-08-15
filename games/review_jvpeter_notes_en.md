# Game Review — Caro-Kann Exchange

*Engine analysis (Stockfish). Scores are from White's point of view: negative = Black is better. 1.00 = one pawn.*

---

## First, an important note

**The report does not contain the part where the game was lost.**

The analysis stops at move 21, and at that moment the evaluation is **−5.69** — Black
is completely winning (a full knight up, with White's knight on a3 still hanging).
So whatever went wrong happened *after* the last line in the report.

Either the PGN was only pasted halfway, or the review hit a move it couldn't read and
stopped there. Re-run the review with the complete PGN to see the finish.

---

## The opening

1. e4 c6  2. Nf3 d5  3. exd5 cxd5  4. d4 Bg4  5. Bb5+ Nc6

Both sides played the top engine move for the first 10 plies. Then:

**6. Ne5?? Bxd1** — White hangs the queen. Black is now **a whole queen up**
(material −900).

---

## Black's biggest mistake: 7...Bg4?? (−4.88)

Position: `r2qkbnr/pp2pppp/2N5/1B1p4/3P4/8/PPP2PPP/RNBbK2R b KQkq - 0 7`

White's 7.Nxc6 carried **two** threats. Black only saw one.

- **The obvious one:** the knight captured the knight on c6.
- **The hidden one:** with the knight gone from c6, the bishop on b5 now looks
  straight down b5–c6–d7–e8 at the black king. That is a **discovered-check battery**,
  and its real target is the **queen on d8**.

7...Bg4 was an attempt to rescue the bishop on d1 (which was attacked by Kxd1).
White replied **8. Ne5+** — discovered check — and Black had to give the queen back:

> 8...Bd7  9.Bxd7+ Qxd7  10.Nxd7 Kxd7

Material: **−900 → 0**. A whole extra queen turned into a dead-equal position in
four moves.

**The correct move was 7...Qb6!** (8.Nxa7+ Kd8 9.a4). The queen steps out of range,
White's knight gets stuck on a7, and Black keeps the extra queen — about **−4.2**.

> **Lesson:** *Don't save the small piece and lose the big one.*
> When your opponent moves a piece, ask two questions, in this order:
> 1. What does it attack where it lands?
> 2. **What did it uncover when it left?**

---

## Second mistake: 13...Rxb2?? (−1.73)

Position: `5bnr/pp1kpppp/8/3p4/3P1B2/2N5/PPr2PPP/R4RK1 b - - 1 13` — Black stands
well at −1.90, with the rook already active on c2.

13...Rxb2 grabbed a second pawn. White answered **14. Rfc1**, the rook on b2 had no
good squares, and it was traded off by 15.Rab1. The whole advantage was gone (−0.04).

The engine wanted **13...e6** — finish developing, connect the bishop and rook, and
turn the invasion on c2 into lasting pressure.

> **Lesson:** *When you're better, add attackers — don't go pawn-hunting.*
> A rook that grabs a pawn on the edge is a rook that stops doing its job.

---

## The numbers

| | Avg. loss per move | Blunders | Accuracy |
|---|---|---|---|
| White | 66 | 3 | 80% |
| Black | 43 | 2 | 86% |

Black played **better on average than White**. White hung the queen (6.Ne5??),
then blundered again on move 19 (Re1??, −2.33) and move 21 (Bxe5??, −1.91).
The report ends with Black a clean piece up and winning.

---

## The pattern to work on

This is the same issue that showed up in the previous game reviewed:

**The problem is not getting an advantage. The problem is converting one.**

Twice in this game Black reached a winning position (+9 in material after 6...Bxd1,
and −5.69 at the end of the report), and the advantage did not hold.

Two concrete habits:

1. **After you win material, your only job is safety.** Before anything else, check
   the opponent's checks — especially discovered checks — and every piece of yours
   that is attacked. Trade pieces, not pawns.
2. **In a good position, ask "how do I bring one more piece in?"**, not "what else
   can I take?" Retreating or grabbing usually throws the advantage away.
