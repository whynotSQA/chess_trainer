# Endgames — what to fix, from your game vs Elijah

*You didn't lose this game to a blunder. I checked the material on every move: it was
**dead even from move 13 to move 30.** You lost an **equal endgame** — by technique,
not by hanging anything. That's a different skill from tactics, and it's very
trainable. Here are the four things this game exposed, in order.*

---

## 1. Don't push a pawn where no other pawn can defend it

This is what actually lost the game. On moves 22–23 you played **...b5** and **...d4**.
Both pawns landed on squares with **no friendly pawn beside them** — isolated pawns.
I counted the d4 pawn at move 29:

> **d4 was attacked 3 times (Ne2, Re4, Kd3) and defended once (Ne6).** Three against
> one. White just played **30.Nxd4** and won it. Then **36.Rxb5** won the other one.

An advanced pawn that no pawn can defend isn't a spearhead — it's a **target** the
opponent walks over to and eats.

> **Rule:** before you push a pawn in the endgame, ask *"once it's there, can another
> pawn defend it?"* If the answer is no, you're creating a weakness. Keep your pawns
> **connected** and make the opponent come to you.

---

## 2. In the endgame, march your king to the centre

Here's the contrast I measured. From move 21, **White's king went to d3 — active,
central — and personally captured the d4 pawn (Kxd4).** Your king sat on **g8 until
move 24**, only reached f8 by move 29, and never helped.

In the middlegame the king hides. **In the endgame the king is a fighting piece** —
often the strongest one. White won this game with his king; yours watched.

> **Rule:** when the queens come off, start walking your king toward the centre and
> the action. A passive king in an endgame is like playing a piece down.

---

## 3. Your rook belongs active, not babysitting

Your rook ended up on c7, passively guarding pawns, and on move 33 you played
**Rc4+** — a check that achieved nothing (same habit as the Hunter game: a check for
its own sake). Meanwhile White's rook roamed and picked off pawns.

> **Rule:** rooks want to be **active** — behind a passed pawn (yours or the enemy's),
> or cutting off the enemy king. A rook tied to defending a weak pawn is a rook doing
> half a job. (And a check is only good if it *does* something.)

---

## 4. The draw you were missing: the Philidor position

You have the *winning* rook-endgame technique in your head, but not the **drawing**
one. This is the single most useful practical endgame skill, and it's exactly what
holds "lost-looking" rook endings — the kind you lost here.

**Set it up and play it (you're White, defending, and you draw):**
```bash
python3 trainer.py play
#   at the prompt:  fen 8/8/1r6/8/4pk2/R7/8/4K3 w - - 0 1
```
*(Verified: this is Philidor's 1777 position. White draws.)*

**The method — two steps, that's the whole thing:**

1. **Keep your rook on the 3rd rank** (here, rank 3) while the enemy pawn is still
   further advanced than it. This *forbids the enemy king from crossing to the 6th
   rank*, so it can never shelter the pawn's advance.
2. **The moment the pawn steps onto your 3rd rank**, send your rook to the **far end
   of the board (1st/8th rank) and check the king from behind — forever.** The king
   can't escape the checks without abandoning the pawn.

If the enemy ever offers a rook trade to break through, **take it** — king-and-pawn
vs king is a draw here.

> This is worth memorising cold. A player who knows Philidor holds half the rook
> endings that look lost.

---

## Practice, in order

1. **Your own equal endgame — hold the draw.** I saved the move-22 position into the
   trainer's drill set. Run `python3 trainer.py drill`, find *"守住均势残局"*, play
   Black, and this time **keep your king central and don't push b5/d4 into isolation.**
   Feel the difference.
2. **Philidor** (the FEN above) — until the two-step method is automatic.
3. **Lucena** (already in the drills) — the winning side of the same endgame.

---

## The endgame checklist — ask before every move

> **Is my king coming to the centre? · Is my rook active? · Are my pawns connected? ·
> Whose pawn is the weakest — and is it mine?**

That's the whole difference between this loss and a draw.

---

*Sources for the Philidor method: [Wikipedia — Philidor position](https://en.wikipedia.org/wiki/Philidor_position); [Chess.com — Philidor Position](https://www.chess.com/terms/philidor-position-chess).*
