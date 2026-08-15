# Lesson — The Move Nobody Forced You To Make

*Two of your games, both checked with Stockfish 18: **vs Aichi** (you were Black)
and **LAQueenKiller vs Morn-P** (you were White). Every number below comes from the
engine report or from counting on the board.*

---

## The finding

I took the biggest blunders from both games and asked one question about each:
**was the piece you moved actually under attack?**

| Game | Move | Loss | Was the piece attacked? |
|---|---|---|---|
| Aichi | 14...Bxf3? | −1.23 | **No** |
| Aichi | 23...Be7? | −1.09 | Yes — by the e5 pawn |
| Aichi | 24...Bd8? | −1.13 | **No** |
| Aichi | 27...Qa4?? | −3.48 | **No** |
| Morn-P | 20.Qe2?? | −2.35 | **No** |
| Morn-P | 36.Qe1?? | −4.66 | **No** |
| Morn-P | 38.Qe4+?? | −10.00 | **No** |

**Six out of seven. Nobody was attacking the piece. Nobody made you move it.**

This is the opposite of what most players assume about their own blunders. You're not
losing games because opponents attack you and you crack. **You're losing them in
quiet moments, moving a piece that had no reason to move.**

So the two habits below are both about the *quiet* moves — the ones where nothing is
happening and you have to decide what to do.

---

## Habit 1 — Before you move a piece, ask what it is doing right now

### 27...Qa4?? — the most expensive move in the Aichi game

```
r1rb3k/2p3p1/p3Q2p/P3N3/5q2/8/5PPP/1R3RK1 b - - 2 27
```

**+0.63 → +4.14.** Nothing was attacking your queen on f4.

But she was doing a job: **guarding f7.** The f-file was clear — f5, f6, f7 all empty —
so from f4 she covered it. The moment she went to a4, **Nf7+** worked, and it **forks
your king on h8 and your bishop on d8.**

The engine's move was **Qf6** — which also guards f7.

> My program flagged this with no engine at all, just by counting: **"gave up the
> f-file."** That's the entire blunder, described before it was punished.

### 24...Bd8? — moving a piece off a square for nothing

Nothing was attacking the bishop on e7. You moved it to d8 anyway, and **your rook on
c8 went from 4 available squares to 1.** Cost: −1.13.

> **The check to build in:** before you touch a piece, say out loud what it is doing
> on its current square — guarding something, covering a square, blocking a line,
> giving another piece room. **If you can't answer, don't move it yet — look harder.**

---

## Habit 2 — In a quiet position, look for captures first

In the Morn-P game the engine's move was **a capture, three separate times.** Three
times you moved the queen somewhere quiet instead:

| Move | You played | Engine wanted | What was on offer |
|---|---|---|---|
| 20 | Qe2?? (−2.35) | **Qxd5+** | a pawn, **with check** |
| 36 | Qe1?? (−4.66) | **Qxb7** | a pawn |
| 38 | Qe4+?? (−10.00) | **Qxa5** | **a rook** — and you had mate in 19 |

Your queen moves that game: 19.Qf3 · 20.Qe2 · 22.Qe1 · 27.Qg1 · 33.Qb1 · 36.Qe1 ·
38.Qe4+. **Five of the seven went backwards to the first or second rank.**

> **The check to build in:** before playing any quiet move, list every capture you
> have. Not "does a capture look good" — **list them.** Three times in one game the
> answer was sitting there.

Note on 38.Qe4+: a check is not automatically good. **Qe4+ offered a queen trade
while you had a forced mate** — the one thing a player with a forced mate should
never want.

---

## The one move that *was* forced — and what it teaches

**23...Be7?** in the Aichi game. Here White really did attack you: the e5 pawn hit
your bishop on d6.

```
r1r3k1/2p2pp1/p1Qb3p/P3P3/5q2/5N2/5PPP/R4RK1 b - - 0 23
```

You retreated. **The engine's move was `Bxe5` — take it.** I counted the pieces on
that square: **e5 is attacked twice (your Bd6 and your Qf4) and defended once
(the Nf3).** Two against one. The exchange comes out about a pawn in your favour.

> **When a piece IS attacked, the order is: can I take? can I hit something bigger?
> can I defend it? — and only then, retreat.** Retreating is what's left when the
> first three fail. Here the very first question was the answer.

---

## What to practise

1. **Say the job out loud.** Every move, before you touch a piece: *"this piece is
   currently guarding ___."* Slow, annoying, and it would have saved 3.5 points on
   move 27 alone.
2. **List the captures.** In any quiet position, name every capture available before
   you consider anything else.
3. **Retreat is fourth on the list, not first.**

Drill position — find `Bxe5`:

```
r1r3k1/2p2pp1/p1Qb3p/P3P3/5q2/5N2/5PPP/R4RK1 b - - 0 23
```

---
---

# Appendix — Opening note for the Italian (Black)

*This is a separate, narrower point. It's worth knowing because you reach this
position repeatedly, but it cost only 0.34 — a fraction of the habits above.*

You play **e5 · Nc6 · Bc5 · d6 · Nf6 · h6** in both your Italian games as Black.
Against Aichi, White expanded with **21.b4, 23.a4, 25.a5**, pushing your bishop
c5 → b6 → a7.

### 12...a6?! was the wrong pawn

```
r4rk1/ppp2pp1/1bnp1q1p/4p2b/PPB1P3/2PP1N2/3N1PPP/R2Q1RK1 b - a3 0 12
```

You were better here (**−0.52**); after 12...a6 it was **−0.15**.

**Stockfish's first choice is `a5`.** Its line: **12...a5 13.b5 Ne7 14.Qc2.**

...a6 has one purpose — to prepare ...b5 — and 13.a5! killed it permanently.
I checked both tries on the board:

- **...b5** → **axb6 en passant**
- **...b6** → **axb6**

> **Rule:** before ...a6, ask whether ...b5 is actually achievable. If a5 can freeze
> it with en passant behind it, ...a6 is a free move for your opponent.

### Ba7 is fine — don't panic

```
13...Ba7   ← Stockfish: BEST MOVE
```

It had **6 available squares** there. Being chased to a7 is normal, not a defeat.

### A correction I owe you

I previously told you that **17...exd4 and 18...c5 blocked your own bishop's
diagonal** and that this was your mistake. The square count did fall — 6 → 4 → 3 → 2 —
but **Stockfish grades 17...exd4 `BEST` and 18...c5 `GOOD`**, the first drop was
caused by *White's* 17.d4, and two moves later the bishop was on **9** squares.

I read a number off my own tool and turned it into a verdict without checking. The
mobility count is a **signal to look**, not a conclusion.
