# Why White Lost — LAQueenKiller (1289) vs Morn-P (1269)

*Stockfish analysis. Scores are from White's point of view: positive = White better.*

---

## The headline

**White reached a winning position three separate times and gave it back every time.**

| Moment | Evaluation | What happened next |
|---|---|---|
| After move 19 | **+1.91** | Slid to −3.44 in five moves |
| After move 35 | **+4.93** | Slid to +0.49 in one move |
| After move 37 | **mate in 19** | Thrown away on move 38 |

Both players blundered constantly — White 7 blunders, Black 8. **White actually
blundered slightly less often and still lost.** So the question isn't "who played
better on average," it's what White specifically kept doing wrong.

Three things, and they're all the same thing wearing different clothes.

---

## 1. When you're attacked on the wing, hit back in the centre

Black's pawns came at the white king: ...f6, ...f5, ...f4, ...f3, backed by ...e5–e4.

**The engine asked for `c4` three times** — moves 21, 22 and 28. That's the classic
answer to a wing attack: open the centre, and the attack on the flank loses its base.

White played `b3`, `Qe1`, `Rbe1` instead — and then finally played **`c4` on move 29,
by which time it was a blunder worth −7.05.**

> **Right idea, three moves too late.** A central break has an expiry date. Once the
> attacking pawns are already on f3 and e4, the same move that would have saved you
> now just opens lines toward your own king.

The measurable version: at move 23, after ...f3 arrived, **White's queen was down to
4 available squares.** White spent those five moves shuffling a rook between e2 and e3.

**+1.91 → −3.44 in five moves, and not one of those moves was worse than −2.35.**
This was not a blunder. It was five moves of doing nothing while something was coming.

---

## 2. Take the free material

Three times the engine's move was simply a capture. Three times White declined it and
moved the queen backwards instead.

| Move | White played | Engine wanted | What was on offer |
|---|---|---|---|
| 20 | Qe2?? (−2.35) | **Qxd5+** | a free pawn, **with check** |
| 36 | Qe1?? (−4.66) | **Qxb7** | a free pawn |
| 38 | Qe4+?? (−10.00) | **Qxa5** | **a whole rook**, and mate in 19 was still on |

Look at White's queen moves across the whole game:

> 19.Qf3 · 20.Qe2 · 22.Qe1 · 27.Qg1 · 33.Qb1 · 36.Qe1 · 38.Qe4+

**Seven queen moves. Five of them went backwards to the first or second rank.**

And 38.Qe4+ is the most expensive move in the game: White had a forced mate in 19,
and offered a queen trade instead. After the trade the position was level; a few moves
later it was lost.

> **A check is not automatically a good move.** Before you check, ask what the check
> actually achieves. Qe4+ achieved a queen trade — the one thing a player with a
> forced mate should never want.

---

## 3. Count the pawn race before you trade the last rook

**50.Rxc3?? (−7.59)** — White won the exchange and lost the game on the same move.

After 50...bxc3 there are no rooks left, and Black's c-pawn plus the king race decide
it. White's king could not get back. The engine wanted **50.Rf4**, keeping rooks on.

> **Rooks are what save bad positions.** The moment you trade the last pair, the
> position becomes pure arithmetic and there is nothing left to swindle with.
> **Count the race to the end before you allow it — every time, no exceptions.**

---

## One that White got away with

**9.Nxf3??** should have lost a piece on the spot. The correct recapture was **Qxf3**.

Position: `r2qkb1r/pp2nppp/2n1p3/1B1p4/3P1B2/5N1P/PPP2PP1/R2QK2R b KQkq - 0 9`

I had the program list every check Black had. **There was exactly one: Qa5+.**

And Qa5+ does two jobs at once — it checks along a5–e1, and it attacks the loose
bishop on b5 along the fifth rank. After 9...Qa5+ 10.c3 Qxb5, Black is a piece up.
Stockfish rates the position **−4.43** after 9.Nxf3.

Black played 9...a6 and missed it.

> **When you recapture, you're choosing which piece to use. Ask what each recapture
> leaves loose.** Here Nxf3 left the b5 bishop hanging on the same diagonal-and-rank
> as a queen check. Qxf3 didn't.

---

## What to work on, in order

1. **When you're being attacked on a wing, look for the central break — and play it
   early.** If you find yourself shuffling a rook back and forth, that's the signal.
2. **Before any quiet move, check whether a capture is available.** Three times in
   this game the best move was just taking something.
3. **Never trade the last rook without counting the pawn ending to the finish.**
4. **A check is only good if it does something.** Trading queens when you have a
   forced mate is the extreme version of this.
