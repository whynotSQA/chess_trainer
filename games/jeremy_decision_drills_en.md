# Three Decision Drills — from your game vs Hunter

*These aren't "spot the tactic" puzzles. In each one you already have a move you
**want** to play. The drill is to calculate your opponent's best reply **before** you
commit, and then decide. That one habit would have changed this whole game.*

*Set each position up in the trainer:*
```bash
python3 trainer.py play
#   at the prompt:  fen <the FEN below>
```

---

## Drill 1 — You want to sacrifice. Does it work?

**White to move.**
```
r2q1rk1/ppp2p2/2npbn1p/2b1p1p1/4P2B/1BPP1N1P/PP3PP1/RN1QK2R w KQ g6 0 10
```

Black just played ...g5, attacking your bishop on h4. You want **Nxg5** — sacrifice
the knight, then pin the f6 knight with Bxg5 and pile on with Qf3.

**Before you play it, calculate two things:**

1. After **Nxg5 hxg5 Bxg5**, how many of your pieces actually attack Black's king?
   *(Count them. The answer is zero.)*
2. A sacrifice needs a follow-up. If you have no attackers near the king, what is the
   knight buying you?

**Verdict:** the sac gives a knight for two pawns and **no attack.** The bishop is
attacked, yes — but the calm answer is simply **Bg3**, stepping back. Retreating a
piece by one square is not a defeat; throwing a knight away to avoid retreating is.

> **The rule:** a sacrifice is judged by what happens *after* your opponent's best
> reply — not by how nice your attack looks in your head.

---

## Drill 2 — You're up a piece, but the knight is pinned. Keep it.

**Black to move.** *(This is the position after the sac above. You're up a piece —
now hold on to it.)*
```
r2q1rk1/ppp2p2/2npbn2/2b1p1B1/4P3/1BPP3P/PP3PP1/RN1QK2R b - - 0 11
```

Your f6 knight is pinned to your queen by the bishop on g5. You want to unpin. There
are two ways — and they are **not** the same:

| Unpin | Does the queen still guard f6? | After White plays Bxf6 |
|---|---|---|
| **...Qd7** | **No** | White wins the knight — you're worse |
| **...Qe7** | **Yes** | ...Qxf6 takes back — you keep your piece |

Both moves unpin. Only **...Qe7** keeps defending f6 at the same time. That is the
move.

> **The rule:** when a pinned piece is attacked, don't just find *an* unpin — find the
> unpin that **still defends** the pinned piece. If the only unpin drops the guard, the
> pin really does win material. Here you had the good one, so the pin was harmless.

*(This is the mirror of Drill 1: it's exactly why the sacrifice didn't work. The
defender always had ...Qe7.)*

---

## Drill 3 — You're down a piece. Is the check worth anything?

**White to move.**
```
7r/1pp1k1q1/2n1p3/p3p3/2PpP1rb/3P1QN1/PP3PP1/R3R1K1 w - - 0 28
```

You're down a piece and looking for activity. You want **Nf5+** — it's a check, it
feels forcing.

**Before you play it, ask one question: after ...exf5, what do I have?**

The pawn on e6 just takes the knight. You get one pawn back for it, and now you're
down **two** pieces instead of one. The check achieved nothing — it only removed your
last active piece.

> **The rule:** a check is not automatically a good move. Before you give one, ask
> what it *does* after the opponent responds. "It's a check" is not a reason. "It wins
> something / leads to mate / improves my position" is.

---

## The one habit behind all three

Drill 1 (a sac), Drill 3 (a check), and the losing moves in your last three games are
the same thing: **a committal move played on hope instead of calculation.** The fix is
one question, every time you're about to capture, sacrifice, or check:

> **"What is my opponent's best reply — and after it, am I better or worse?"**

Ask it out loud. Slowly. On move 10 of this game, the answer was sitting on the board.
