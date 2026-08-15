# Game Review — Queen's Gambit Declined (Black)

*Engine analysis. Scores are from White's point of view: positive = White is better.
1.00 = one pawn.*

1.d4 d5 2.c4 e6 3.Nc3 Nf6 4.Bg5 Be7 5.e3 O-O 6.Nf3 c6 7.Qc2 Nbd7 8.a3 b6
9.cxd5 **Nxd5?!** 10.Nxd5 cxd5 11.h4 **Bb7?** 12.Bxe7 Qxe7 13.Qc7 **Rab8??**
14.Ne5 Rfd8 15.Bb5 **Ba8?!** 16.Rc1 h6 17.O-O **Rb7??** 18.Nc6 Qxh4 19.Qxd8+ Qxd8
20.Nxd8 **Nf6?** 21.Rc8

---

## First: who is White?

White played 21 moves with an average loss of **1 centipawn**, zero inaccuracies,
zero mistakes, 99% accuracy. **No human plays like that.** White is an engine, so
everything below is about Black.

---

## The one fact that explains the whole game

I measured the material balance and the number of legal moves available to Black's
pieces at each of the four critical moments:

| Moment | Material | Legal moves for Black's light-squared bishop | Black's rooks |
|---|---|---|---|
| 11...Bb7? | **level** | 6 (still on e7) | a8: 2 · f8: 1 |
| 13...Rab8?? | **level** | 4 (on b7) | b8: 4 · f8: 3 |
| 15...Ba8?! | **level** | **2** | b8: 2 · d8: 3 |
| 17...Rb7?? | **level** | **0** | b7: 2 · d8: 4 |

**Black never lost a single piece — and the evaluation still went from +0.3 to +6.55.**

**Black wasn't captured to death. Black was suffocated.**

By move 17 that bishop had **zero legal moves**. It was sitting on a8, permanently
walled in on the long diagonal by Black's own pawn on d5.

---

## Every mistake was a retreat

| Black played | The engine wanted |
|---|---|
| 11...Bb7? | **Nf6** |
| 13...Rab8?? | **Bc8** |
| 15...Ba8?! | **a6** |
| 17...Rb7?? | **a6** |
| 20...Nf6? | Rb8 |

Not one of the engine's suggestions is defensive. Every single one **frees a piece**.

And **a6 appears twice** — both times the idea is to hit the bishop on b5 with a pawn
and pry the position open. Black never played it.

---

## The root cause: move 9

**9...Nxd5?!** — the pawn recapture **9...cxd5** was correct.

After 9...Nxd5 10.Nxd5 cxd5 the pawn structure is identical, but Black has traded off
a pair of knights and lost a tempo. Worse, **the pieces Black kept were exactly the
wrong ones**: a light-squared bishop that its own d5 pawn permanently blocks, and a
knight stuck on d7.

From there 11.h4! and 12.Bxe7 both came with tempo, and Black never got a single
active move for the rest of the game.

---

## What to work on

**Blind-spot drills will not fix this.** Those train "don't overlook things," and
nothing was overlooked here. Nothing hung. This is a purely positional loss.

Three concrete habits:

### 1. Every move, ask: which of my pieces is the worst one?

That bishop's mobility went **6 → 4 → 2 → 0**. Asking this question at *any* point
in that slide would have produced ...a6 or ...Bc8 on its own.

This is the single most useful positional question there is, and it costs five seconds.

### 2. Don't put a bishop on the same colour as your own pawns

d5 is a light square. Black's light-squared bishop went to b7, then a8 — behind its
own pawn, on its own colour. That's how you bury a piece without anyone capturing it.

This rule is concrete enough to teach directly.

### 3. When you're being squeezed, seek exchanges and pawn breaks — don't keep giving ground

Passive moves feel safe. They are not. Each retreat here cost roughly a pawn of
evaluation while losing no material at all.

The engine's answer both times was **...a6** — challenge the bishop, make the opponent
decide something.

---

## Why this game matters

Compared with the other games reviewed, this is the opposite failure mode:

| | Failure mode |
|---|---|
| The tactical games | Solid play, then a single one-move oversight drops a piece |
| **This game** | **Zero oversights, zero material lost — squeezed to death over 20 moves** |

Both lose. But they need completely different training, so it's worth knowing which
one you're looking at.
