# Jeremy — Three Habits (from the Peter and Paul games)

Both games analysed by engine. Every item below points to a real move you played,
with the cost in pawns that the engine assigned to it.

Across the two games you gave away **22.7 pawns** in total. **Three habits account
for 18.8 of them — 83%.**

---

## Habit 1 — Trace the line. Twice. (10.6 pawns)

> Before you move a piece: **what am I blocking right now, and what opens up when
> I leave?**
> After you move it: **the squares I think I now defend — is anything standing in
> the way?**

**Your own pieces block your lines just as effectively as your opponent's do.**
Both of your biggest losses were exactly this, in mirror image:

| Move | What you missed | Cost |
|---|---|---|
| **6. Ne5??** (vs Peter) | Your knight on f3 was the only thing blocking Black's bishop on g4 from your queen on d1. The knight left, the line opened. | **4.8** |
| **28. Qxe4??** (vs Paul) | Your rook on e2 was defended by your queen on d3. From e4 the queen *looks* like it still covers e2 down the file — but your own bishop on e3 is in the way. | **5.8** |

One is "I moved away and opened a line against myself."
The other is "I'm counting on a line that isn't actually open."
**Same skill: knowing who is standing on the line.**

---

## Habit 2 — When one of your pieces is attacked, moving it is the *last* option (5.8 pawns)

Run these in order. Do not skip to 4.

1. **Is one of their pieces also hanging? Whose move is it?**
2. Can I capture the attacker?
3. Can I add a defender?
4. Move it — and first ask: **what was this piece defending?**

**28.Qxe4??** — your queen was attacked by a pawn, so you moved it. But Black's queen
on b2 was hanging too, and it was your move. **28.Rxb2!** simply takes it first and
the game stays level. (28.Qa6 also holds. You had two ways out and picked the third.)

*Note: this is the same move as Habit 1's second example — it's one blunder that two
different checks would each have caught. Don't count the pawns twice.*

---

## Habit 3 — After every move, name your own loose pieces (4.6 pawns)

Out loud if you're training alone: *"Right now, which of my pieces has no defender?"*

| Move | What was loose | Cost |
|---|---|---|
| 12. Bf4? | c2 was already hanging to the rook on c8 — you developed instead. **12.c3** deals with it. | 1.3 |
| 13. Nc3?! | b2 now hanging as well; still ignored. | 0.3 |
| 15. Rab1? | Black's rook had invaded on b2. **15.Na4!** attacks it instead of trading. | 1.1 |
| 21. Bxe5?? | Three loose things at once (Bf4, Na3, d4). You chose the recapture that left the knight on a3 hanging; **21.dxe5** keeps material. | 1.9 |

**When an enemy piece invades, go at it directly** — block it (c3), attack it (Na4).
Continuing to develop normally is the same as agreeing to lose the pawn.

---

## Habit 4 — Count retreat squares before you jump in (3.6 pawns)

**Before a knight goes deep into enemy territory, ask where it goes when it gets
kicked.**

Your knight on b5 (vs Peter) had exactly one square once ...a6 came — a3 — and that
is where it was eventually captured by ...Bxa3.

- **18. a4?** — the engine wanted **18.Nxa7+**: cash in while the knight still can.
  (1.3)
- **19. Re1??** — after this, ...a6 arrives and the knight is committed to a3. (2.3)

---

## Habit 5 — The better a move looks, the more it deserves one more look

This is not a separate check — it's the **trigger** that tells you to run the checks above.

Both of your worst moves felt like free money at the time:

- **6.Ne5** forked two pieces — it looked like winning a piece.
- **28.Qxe4** escaped an attack *and* grabbed a pawn — it looked like winning twice.

> **If a move feels like a bonus, that is the moment to slow down, not speed up.**

---

## One more thing: a trap is not a sacrifice

Your idea behind 6.Ne5 was real — after 6...Bxd1 7.Nxc6, the bishop on b5 and the
knight on c6 form a discovered-check battery, and in the game **it worked**: 8.Ne5+
won the queen back.

But it only works if Black cooperates. **7...Qb6!** and it collapses: the queen steps
out, and after 8.Nxa7+ Kd8 9.Kxd1 **Qxd4+** 10.Ke1 **Qxa7** Black is a queen for a
bishop and a pawn up — about **−5.0**.

The discovered checks are all still there (there are seven of them after 7...Qb6) —
they're just worthless, because:

> **A discovered check is only worth what's standing at the far end of the line.**
> Once the queen leaves d8, checking the king wins nothing.

**Know which one you're playing.** A sacrifice is calculated to a concrete result that
holds however the opponent replies. A trap depends on the opponent missing one move.
Traps are a reasonable bet against some opponents and a losing bet against others —
but you should always know you're making a bet.

---

## What you already fixed

In the Peter game you played 6.Ne5 in this opening and lost your queen.
In the Paul game you reached the **identical position after 5 moves** and played
**6.c3** — the correct move — and then held a level position for 27 moves at 90%
accuracy.

You already corrected one of these on your own. That's the strongest signal in either
game.

---

## Drill these

```bash
# your own positions, drilled for loose pieces and missed threats
CHESS_ENGINE=sf python3 trainer.py blind
#   → enter games/jvpaul.pgn  (or games/jvpeter.pgn) when asked for a source

# tactics set — now includes your own move-28 position
python3 trainer.py puzzle
```
