# Game Review — Jeremy (White) vs Paul, "icea aug"

*Engine analysis. Scores are from White's point of view: negative = Black is better.
1.00 = one pawn.*

---

## Summary

**You played 27 good moves and lost the game with one.**

For the first 54 plies the evaluation never left the range +0.48 to −0.70 — a
completely level game. Then move 28: **−5.86**.

Your average loss per move was 36 centipawns and your accuracy was 90%. That is a
solid game. The problem is not your general play; it is one specific habit.

---

## The losing move: 28. Qxe4?? (−5.78)

`3rr1k1/p1b2pp1/1p2p2p/8/3PpP2/P1PQB1P1/1q2R2P/2R3K1 w - - 0 28`

Black has just played 27...dxe4, attacking your queen on d3. The key feature of this
position:

**Both queens are hanging at the same time.** Your queen on d3 is attacked by the
pawn on e4. Black's queen on b2 is attacked by your rook on e2 (along the second rank:
b2–c2–d2–e2, nothing in between). **And it is your move — whoever strikes first wins
the race.**

| Move | What follows | Evaluation |
|---|---|---|
| **28. Rxb2!** | exd3 — queens come off | **+0.34 (level)** |
| 28. Qa6 | also holds, slightly worse | about −0.7 |
| 28. Qxe4?? | Qxe2 — you lose a rook | +6.11 (Black winning) |

You had **at least two ways to stay level** and picked the one move that loses a rook.

### Why it happened — two reasons

**1. Qxe4 looked like a double win.** The queen escapes the attack *and* grabs a pawn.
A move that feels like a free bonus is exactly the move that doesn't get double-checked.

> **The better a move looks, the more it deserves one more look.**

**2. The rook on e2 was defended by the queen on d3.** When the queen went to e4 it
stopped defending it — and here is the subtle part:

**From e4 the queen looks like it still covers the e-file down to e2. It doesn't.
Your own bishop on e3 is in the way.**

---

## The same mistake in your previous game

Comparing this with your game against Peter (same opening, same colour):

| | The move | What happened |
|---|---|---|
| **vs Peter, 6. Ne5??** | Your knight on f3 was **blocking** Black's bishop on g4 from d1 | The knight moved, the line opened, you lost the queen |
| **vs Paul, 28. Qxe4??** | Your bishop on e3 was **blocking** the queen on e4 from e2 | You thought the rook was still defended; it wasn't; you lost the rook |

One is "my piece moved away and opened a line *against* me."
The other is "my piece is in the way, so the line I'm counting on isn't there."

**These are two sides of the same thing: not counting who is standing on a line.**

---

## The habit to build

Every time you move a piece, trace its **rank, file and diagonals all the way to both
ends** — twice:

1. **Before you move it:** what am I currently blocking? What gets uncovered when I
   leave? (Especially: is my king or queen on that line?)
2. **After you move it:** the squares I think I now defend — is anything standing in
   the way? *Your own pieces block your lines just as effectively as your
   opponent's do.*

### When one of your pieces is attacked

The instinct "it's attacked, so I must move it" is what cost the rook. Run this list
in order, and only reach step 4 at the end:

1. **Is one of *their* pieces also hanging? Whose move is it?** ← this game
2. Can I capture the attacker?
3. Can I add a defender?
4. Move it — and before you do, ask: **what was this piece defending?**

---

## The good news

In the game against Peter you played 6.Ne5 in this exact opening and lost your queen.
In this game you reached the identical position after 5 moves and played **6.c3** —
the correct move — and then held a level game for 27 moves.

**You already fixed one of these. This is the same lesson from the other direction.**

---

## Practice

The position after 28.Qxe4 has been added to the tactics set, under the theme
"what was the piece that ran away defending?" — from Black's side, where the answer
is the single move Qxe2.

```bash
python3 trainer.py puzzle
```

And the whole game can be used to generate blind-spot drills from your own positions:

```bash
CHESS_ENGINE=sf python3 trainer.py blind
# when asked where positions come from, enter: games/jvpaul.pgn
```
