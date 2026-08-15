"""0x88 chess board: move generation, make/unmake, FEN / SAN / PGN.

Pure Python, no dependencies.
"""

import random

# ---------------------------------------------------------------- constants
EMPTY = 0
PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING = 1, 2, 3, 4, 5, 6
WHITE, BLACK = 8, 16

PIECE_LETTER = {PAWN: 'P', KNIGHT: 'N', BISHOP: 'B',
                ROOK: 'R', QUEEN: 'Q', KING: 'K'}
LETTER_PIECE = {v: k for k, v in PIECE_LETTER.items()}

UNICODE = {
    WHITE | PAWN: '♙', WHITE | KNIGHT: '♘', WHITE | BISHOP: '♗',
    WHITE | ROOK: '♖', WHITE | QUEEN: '♕', WHITE | KING: '♔',
    BLACK | PAWN: '♟', BLACK | KNIGHT: '♞', BLACK | BISHOP: '♝',
    BLACK | ROOK: '♜', BLACK | QUEEN: '♛', BLACK | KING: '♚',
}

# castling right bits
CR_WK, CR_WQ, CR_BK, CR_BQ = 1, 2, 4, 8

# move flags
F_NORMAL, F_EP, F_CASTLE, F_DPP = 0, 1, 2, 3

KNIGHT_DIRS = (33, 31, 18, 14, -33, -31, -18, -14)
BISHOP_DIRS = (17, 15, -17, -15)
ROOK_DIRS = (16, -16, 1, -1)
KING_DIRS = (17, 16, 15, 1, -1, -15, -16, -17)

A1, E1, H1 = 0, 4, 7
A8, E8, H8 = 112, 116, 119

# subtract these bits from castling rights when a square is touched
CASTLE_MASK = [15] * 128
CASTLE_MASK[A1] = 15 ^ CR_WQ
CASTLE_MASK[H1] = 15 ^ CR_WK
CASTLE_MASK[E1] = 15 ^ (CR_WK | CR_WQ)
CASTLE_MASK[A8] = 15 ^ CR_BQ
CASTLE_MASK[H8] = 15 ^ CR_BK
CASTLE_MASK[E8] = 15 ^ (CR_BK | CR_BQ)

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

# 超大棋盘用的三行棋子图案（每格 5 字宽）：白子空心，黑子实心
_HAT = {KING: r" \|/ ", QUEEN: r" ooo ", ROOK: r" |-| ",
        BISHOP: r"  ^  ", KNIGHT: r" /^  ", PAWN: r"  o  "}
PIECE_ART = {}
for _t, _hat in _HAT.items():
    _L = PIECE_LETTER[_t]
    PIECE_ART[WHITE | _t] = (_hat, " (%s) " % _L, r" /_\ ")
    PIECE_ART[BLACK | _t] = (_hat, " [%s] " % _L.lower(), r" /#\ ")
LIGHT_ART = ("     ", "     ", "     ")
DARK_ART = ("     ", "  ·  ", "     ")


def ptype(p):
    return p & 7


def pcolor(p):
    return p & 24


def opp(color):
    return BLACK if color == WHITE else WHITE


def sq_name(s):
    return "abcdefgh"[s & 7] + "12345678"[s >> 4]


def name_sq(n):
    return "abcdefgh".index(n[0]) | ("12345678".index(n[1]) << 4)


# ------------------------------------------------------------------- moves
def mk_move(frm, to, promo=0, flag=F_NORMAL):
    return frm | (to << 8) | (promo << 16) | (flag << 20)


def m_from(m):
    return m & 0xFF


def m_to(m):
    return (m >> 8) & 0xFF


def m_promo(m):
    return (m >> 16) & 0xF


def m_flag(m):
    return (m >> 20) & 0xF


def move_uci(m):
    s = sq_name(m & 0xFF) + sq_name((m >> 8) & 0xFF)
    p = (m >> 16) & 0xF
    if p:
        s += PIECE_LETTER[p].lower()
    return s


# ----------------------------------------------------------------- zobrist
_rng = random.Random(20240817)
Z_PIECE = [[_rng.getrandbits(64) for _ in range(128)] for _ in range(32)]
Z_CASTLE = [_rng.getrandbits(64) for _ in range(16)]
Z_EP = [_rng.getrandbits(64) for _ in range(8)]
Z_SIDE = _rng.getrandbits(64)


class Board:
    """A chess position."""

    __slots__ = ('sq', 'side', 'castling', 'ep', 'halfmove', 'fullmove',
                 'kings', 'key', 'history', 'reps')

    def __init__(self, fen=START_FEN):
        self.set_fen(fen)

    # ------------------------------------------------------------ FEN I/O
    def set_fen(self, fen):
        parts = fen.strip().split()
        while len(parts) < 6:
            parts.append('-' if len(parts) < 4 else '0')
        self.sq = [EMPTY] * 128
        rank, file = 7, 0
        for ch in parts[0]:
            if ch == '/':
                rank -= 1
                file = 0
            elif ch.isdigit():
                file += int(ch)
            else:
                color = WHITE if ch.isupper() else BLACK
                self.sq[(rank << 4) | file] = color | LETTER_PIECE[ch.upper()]
                file += 1
        self.side = WHITE if parts[1] == 'w' else BLACK
        self.castling = 0
        for ch, bit in (('K', CR_WK), ('Q', CR_WQ), ('k', CR_BK), ('q', CR_BQ)):
            if ch in parts[2]:
                self.castling |= bit
        self.ep = name_sq(parts[3]) if parts[3] not in ('-', '') else -1
        self.halfmove = int(parts[4]) if parts[4].isdigit() else 0
        self.fullmove = int(parts[5]) if parts[5].isdigit() else 1
        self.kings = {WHITE: -1, BLACK: -1}
        for s in range(128):
            if not (s & 0x88) and ptype(self.sq[s]) == KING:
                self.kings[pcolor(self.sq[s])] = s
        self.history = []
        self.key = self._compute_key()
        self.reps = [self.key]

    def fen(self):
        rows = []
        for rank in range(7, -1, -1):
            row, gap = '', 0
            for file in range(8):
                p = self.sq[(rank << 4) | file]
                if p == EMPTY:
                    gap += 1
                else:
                    if gap:
                        row += str(gap)
                        gap = 0
                    ch = PIECE_LETTER[ptype(p)]
                    row += ch if pcolor(p) == WHITE else ch.lower()
            if gap:
                row += str(gap)
            rows.append(row)
        cast = ''.join(c for c, b in (('K', CR_WK), ('Q', CR_WQ),
                                      ('k', CR_BK), ('q', CR_BQ))
                       if self.castling & b) or '-'
        return "%s %s %s %s %d %d" % (
            '/'.join(rows), 'w' if self.side == WHITE else 'b', cast,
            sq_name(self.ep) if self.ep >= 0 else '-',
            self.halfmove, self.fullmove)

    def _compute_key(self):
        k = 0
        for s in range(128):
            if not (s & 0x88):
                p = self.sq[s]
                if p:
                    k ^= Z_PIECE[p & 31][s]
        k ^= Z_CASTLE[self.castling]
        if self.ep >= 0:
            k ^= Z_EP[self.ep & 7]
        if self.side == WHITE:
            k ^= Z_SIDE
        return k

    # -------------------------------------------------------------- attacks
    def is_attacked(self, s, by):
        """Is square `s` attacked by color `by`?"""
        sqs = self.sq
        # pawns
        if by == WHITE:
            for d in (-15, -17):
                t = s + d
                if not (t & 0x88) and sqs[t] == (WHITE | PAWN):
                    return True
        else:
            for d in (15, 17):
                t = s + d
                if not (t & 0x88) and sqs[t] == (BLACK | PAWN):
                    return True
        # knights
        kn = by | KNIGHT
        for d in KNIGHT_DIRS:
            t = s + d
            if not (t & 0x88) and sqs[t] == kn:
                return True
        # king
        kg = by | KING
        for d in KING_DIRS:
            t = s + d
            if not (t & 0x88) and sqs[t] == kg:
                return True
        # bishops / queens
        bq_b, bq_q = by | BISHOP, by | QUEEN
        for d in BISHOP_DIRS:
            t = s + d
            while not (t & 0x88):
                p = sqs[t]
                if p:
                    if p == bq_b or p == bq_q:
                        return True
                    break
                t += d
        # rooks / queens
        rq_r = by | ROOK
        for d in ROOK_DIRS:
            t = s + d
            while not (t & 0x88):
                p = sqs[t]
                if p:
                    if p == rq_r or p == bq_q:
                        return True
                    break
                t += d
        return False

    def in_check(self, color=None):
        if color is None:
            color = self.side
        return self.is_attacked(self.kings[color], opp(color))

    # ------------------------------------------------------- move generation
    def gen_moves(self, captures_only=False):
        """Pseudo-legal moves for the side to move."""
        moves = []
        add = moves.append
        sqs = self.sq
        me = self.side
        them = opp(me)
        for frm in range(128):
            if frm & 0x88:
                continue
            p = sqs[frm]
            if not p or (p & 24) != me:
                continue
            t = p & 7
            if t == PAWN:
                if me == WHITE:
                    push, start, last, caps = 16, 1, 7, (15, 17)
                else:
                    push, start, last, caps = -16, 6, 0, (-15, -17)
                to = frm + push
                if not captures_only and not (to & 0x88) and not sqs[to]:
                    if (to >> 4) == last:
                        for pr in (QUEEN, ROOK, BISHOP, KNIGHT):
                            add(mk_move(frm, to, pr))
                    else:
                        add(mk_move(frm, to))
                        if (frm >> 4) == start and not sqs[to + push]:
                            add(mk_move(frm, to + push, 0, F_DPP))
                for d in caps:
                    to = frm + d
                    if to & 0x88:
                        continue
                    tp = sqs[to]
                    if tp and (tp & 24) == them:
                        if (to >> 4) == last:
                            for pr in (QUEEN, ROOK, BISHOP, KNIGHT):
                                add(mk_move(frm, to, pr))
                        else:
                            add(mk_move(frm, to))
                    elif not tp and to == self.ep:
                        add(mk_move(frm, to, 0, F_EP))
            elif t == KNIGHT or t == KING:
                dirs = KNIGHT_DIRS if t == KNIGHT else KING_DIRS
                for d in dirs:
                    to = frm + d
                    if to & 0x88:
                        continue
                    tp = sqs[to]
                    if tp:
                        if (tp & 24) == them:
                            add(mk_move(frm, to))
                    elif not captures_only:
                        add(mk_move(frm, to))
            else:
                if t == BISHOP:
                    dirs = BISHOP_DIRS
                elif t == ROOK:
                    dirs = ROOK_DIRS
                else:
                    dirs = KING_DIRS
                for d in dirs:
                    to = frm + d
                    while not (to & 0x88):
                        tp = sqs[to]
                        if tp:
                            if (tp & 24) == them:
                                add(mk_move(frm, to))
                            break
                        if not captures_only:
                            add(mk_move(frm, to))
                        to += d
        # castling
        if not captures_only:
            if me == WHITE:
                k, r_k, r_q, ck, cq = E1, H1, A1, CR_WK, CR_WQ
            else:
                k, r_k, r_q, ck, cq = E8, H8, A8, CR_BK, CR_BQ
            if sqs[k] == (me | KING):
                if (self.castling & ck) and sqs[r_k] == (me | ROOK) \
                        and not sqs[k + 1] and not sqs[k + 2]:
                    if not self.is_attacked(k, them) and \
                            not self.is_attacked(k + 1, them) and \
                            not self.is_attacked(k + 2, them):
                        add(mk_move(k, k + 2, 0, F_CASTLE))
                if (self.castling & cq) and sqs[r_q] == (me | ROOK) \
                        and not sqs[k - 1] and not sqs[k - 2] and not sqs[k - 3]:
                    if not self.is_attacked(k, them) and \
                            not self.is_attacked(k - 1, them) and \
                            not self.is_attacked(k - 2, them):
                        add(mk_move(k, k - 2, 0, F_CASTLE))
        return moves

    def legal_moves(self):
        out = []
        me = self.side
        for m in self.gen_moves():
            self.make(m)
            if not self.is_attacked(self.kings[me], self.side):
                out.append(m)
            self.unmake()
        return out

    def is_legal(self, m):
        """Full check: never trusts `m` (a stale hash move could be nonsense)."""
        if not m:
            return False
        p = self.sq[m & 0xFF]
        if not p or (p & 24) != self.side or m not in self.gen_moves():
            return False
        me = self.side
        self.make(m)
        ok = not self.is_attacked(self.kings[me], self.side)
        self.unmake()
        return ok

    # ------------------------------------------------------- make / unmake
    def make(self, m):
        sqs = self.sq
        frm = m & 0xFF
        to = (m >> 8) & 0xFF
        promo = (m >> 16) & 0xF
        flag = (m >> 20) & 0xF
        piece = sqs[frm]
        me = piece & 24
        cap_sq = to
        if flag == F_EP:
            cap_sq = to - 16 if me == WHITE else to + 16
        captured = sqs[cap_sq]

        self.history.append((m, captured, self.castling, self.ep,
                             self.halfmove, self.key, cap_sq))

        key = self.key
        # remove captured
        if captured:
            sqs[cap_sq] = EMPTY
            key ^= Z_PIECE[captured & 31][cap_sq]
        # move piece
        sqs[frm] = EMPTY
        key ^= Z_PIECE[piece & 31][frm]
        newp = (me | promo) if promo else piece
        sqs[to] = newp
        key ^= Z_PIECE[newp & 31][to]
        if (piece & 7) == KING:
            self.kings[me] = to
        # castling rook
        if flag == F_CASTLE:
            if to > frm:      # king side
                r_f, r_t = frm + 3, frm + 1
            else:             # queen side
                r_f, r_t = frm - 4, frm - 1
            rook = sqs[r_f]
            sqs[r_f] = EMPTY
            sqs[r_t] = rook
            key ^= Z_PIECE[rook & 31][r_f] ^ Z_PIECE[rook & 31][r_t]
        # castling rights
        key ^= Z_CASTLE[self.castling]
        self.castling &= CASTLE_MASK[frm] & CASTLE_MASK[to]
        key ^= Z_CASTLE[self.castling]
        # en passant square
        if self.ep >= 0:
            key ^= Z_EP[self.ep & 7]
        if flag == F_DPP:
            self.ep = (frm + to) >> 1
            key ^= Z_EP[self.ep & 7]
        else:
            self.ep = -1
        # clocks
        if (piece & 7) == PAWN or captured:
            self.halfmove = 0
        else:
            self.halfmove += 1
        if me == BLACK:
            self.fullmove += 1
        self.side = BLACK if me == WHITE else WHITE
        key ^= Z_SIDE
        self.key = key
        self.reps.append(key)

    def unmake(self):
        m, captured, castling, ep, halfmove, key, cap_sq = self.history.pop()
        self.reps.pop()
        sqs = self.sq
        frm = m & 0xFF
        to = (m >> 8) & 0xFF
        promo = (m >> 16) & 0xF
        flag = (m >> 20) & 0xF
        piece = sqs[to]
        me = piece & 24
        if promo:
            piece = me | PAWN
        sqs[to] = EMPTY
        sqs[frm] = piece
        if (piece & 7) == KING:
            self.kings[me] = frm
        if captured:
            sqs[cap_sq] = captured
        if flag == F_CASTLE:
            if to > frm:
                r_f, r_t = frm + 3, frm + 1
            else:
                r_f, r_t = frm - 4, frm - 1
            sqs[r_f] = sqs[r_t]
            sqs[r_t] = EMPTY
        self.castling = castling
        self.ep = ep
        self.halfmove = halfmove
        self.key = key
        if me == BLACK:
            self.fullmove -= 1
        self.side = me

    def make_null(self):
        self.history.append((0, EMPTY, self.castling, self.ep,
                             self.halfmove, self.key, 0))
        key = self.key
        if self.ep >= 0:
            key ^= Z_EP[self.ep & 7]
        self.ep = -1
        self.side = opp(self.side)
        key ^= Z_SIDE
        self.key = key
        self.reps.append(key)
        self.halfmove += 1

    def unmake_null(self):
        _, _, castling, ep, halfmove, key, _ = self.history.pop()
        self.reps.pop()
        self.castling = castling
        self.ep = ep
        self.halfmove = halfmove
        self.key = key
        self.side = opp(self.side)

    # -------------------------------------------------------------- status
    def piece_counts(self):
        c = {}
        for s in range(128):
            if not (s & 0x88) and self.sq[s]:
                p = self.sq[s]
                c[p] = c.get(p, 0) + 1
        return c

    def insufficient_material(self):
        c = self.piece_counts()
        if any(ptype(p) in (PAWN, ROOK, QUEEN) for p in c):
            return False
        minors = sum(n for p, n in c.items() if ptype(p) in (KNIGHT, BISHOP))
        return minors <= 1

    def is_repetition(self, need=3):
        k = self.key
        n = 0
        start = max(0, len(self.reps) - 1 - self.halfmove)
        for i in range(len(self.reps) - 1, start - 1, -1):
            if self.reps[i] == k:
                n += 1
                if n >= need:
                    return True
        return False

    def outcome(self):
        """Returns (result, reason) or None if the game continues."""
        if not self.legal_moves():
            if self.in_check():
                return ("0-1" if self.side == WHITE else "1-0", "checkmate")
            return ("1/2-1/2", "stalemate")
        if self.halfmove >= 100:
            return ("1/2-1/2", "fifty-move rule")
        if self.is_repetition():
            return ("1/2-1/2", "threefold repetition")
        if self.insufficient_material():
            return ("1/2-1/2", "insufficient material")
        return None

    # ----------------------------------------------------------------- SAN
    def san(self, m, legal=None):
        frm, to = m & 0xFF, (m >> 8) & 0xFF
        promo, flag = (m >> 16) & 0xF, (m >> 20) & 0xF
        piece = self.sq[frm]
        t = piece & 7
        if flag == F_CASTLE:
            s = "O-O" if to > frm else "O-O-O"
        else:
            capture = bool(self.sq[to]) or flag == F_EP
            if t == PAWN:
                s = (sq_name(frm)[0] + 'x') if capture else ''
                s += sq_name(to)
                if promo:
                    s += '=' + PIECE_LETTER[promo]
            else:
                s = PIECE_LETTER[t]
                if legal is None:
                    legal = self.legal_moves()
                same = [x for x in legal
                        if (x >> 8) & 0xFF == to and x & 0xFF != frm
                        and self.sq[x & 0xFF] == piece]
                if same:
                    if all((x & 0xFF) & 7 != frm & 7 for x in same):
                        s += "abcdefgh"[frm & 7]
                    elif all((x & 0xFF) >> 4 != frm >> 4 for x in same):
                        s += "12345678"[frm >> 4]
                    else:
                        s += sq_name(frm)
                if capture:
                    s += 'x'
                s += sq_name(to)
        self.make(m)
        if self.in_check():
            s += '#' if not self.legal_moves() else '+'
        self.unmake()
        return s

    def parse_move(self, text):
        """Accepts SAN (Nf3, exd5, O-O, e8=Q) or coordinates (e2e4, e7e8q)."""
        text = text.strip()
        if not text:
            return None
        legal = self.legal_moves()
        # coordinate notation
        low = text.lower().replace('-', '')
        if len(low) in (4, 5) and low[0] in 'abcdefgh' and low[1] in '12345678' \
                and low[2] in 'abcdefgh' and low[3] in '12345678':
            frm, to = name_sq(low[:2]), name_sq(low[2:4])
            pr = LETTER_PIECE.get(low[4].upper()) if len(low) == 5 else 0
            for m in legal:
                if (m & 0xFF) == frm and ((m >> 8) & 0xFF) == to:
                    if not pr or ((m >> 16) & 0xF) == pr:
                        return m
                    continue
            return None
        norm = text.rstrip('+#!? ').replace('0', 'O')
        for m in legal:
            if self.san(m, legal).rstrip('+#') == norm:
                return m
        # lenient: ignore case of the file letter / missing '='
        for m in legal:
            if self.san(m, legal).rstrip('+#').replace('=', '').lower() == \
                    norm.replace('=', '').lower():
                return m
        return self._parse_san_loose(norm, legal)

    def _parse_san_loose(self, txt, legal):
        """Structural SAN parse: tolerates redundant or missing disambiguation
        (e.g. 'Ndb5' where plain 'Nb5' is already unambiguous)."""
        import re
        t = txt.replace('-', '').replace('x', 'x')
        if t.upper() in ('OO', 'O-O'):
            t = 'O-O'
        if t.upper().replace('-', '') == 'OOO':
            for m in legal:
                if ((m >> 20) & 0xF) == F_CASTLE and \
                        ((m >> 8) & 0xFF) < (m & 0xFF):
                    return m
            return None
        if t.upper().replace('-', '') == 'OO':
            for m in legal:
                if ((m >> 20) & 0xF) == F_CASTLE and \
                        ((m >> 8) & 0xFF) > (m & 0xFF):
                    return m
            return None
        mt = re.match(r'^([KQRBN])?([a-h])?([1-8])?(x)?([a-h][1-8])'
                      r'(?:=?([QRBNqrbn]))?$', txt)
        if not mt and txt[:1] in 'kqrbn':      # 允许小写子力字母，如 nf3
            txt = txt[0].upper() + txt[1:]
            mt = re.match(r'^([KQRBN])?([a-h])?([1-8])?(x)?([a-h][1-8])'
                          r'(?:=?([QRBNqrbn]))?$', txt)
        if not mt:
            return None
        pc, ff, fr, _cap, to_s, promo = mt.groups()
        want_type = LETTER_PIECE[pc] if pc else PAWN
        to = name_sq(to_s)
        want_promo = LETTER_PIECE[promo.upper()] if promo else 0
        hits = []
        for m in legal:
            frm = m & 0xFF
            if ((m >> 8) & 0xFF) != to:
                continue
            if ptype(self.sq[frm]) != want_type:
                continue
            if ff and "abcdefgh"[frm & 7] != ff:
                continue
            if fr and "12345678"[frm >> 4] != fr:
                continue
            if want_promo and ((m >> 16) & 0xF) != want_promo:
                continue
            if not want_promo and ((m >> 16) & 0xF) not in (0, QUEEN):
                continue
            hits.append(m)
        return hits[0] if len(hits) == 1 else None

    # ------------------------------------------------------------- display
    def render_huge(self, flip=False, ascii_only=False, highlight=()):
        """超大棋盘：每个棋子用三行字符拼出来，图标本身就变大了。"""
        ranks = range(8) if flip else range(7, -1, -1)
        files = range(7, -1, -1) if flip else range(8)
        sep = "    +" + "-------+" * 8
        lines = [sep]
        for r in ranks:
            rows = ["", "", ""]
            for f in files:
                s = (r << 4) | f
                p = self.sq[s]
                art = PIECE_ART.get(p)
                if art is None:                       # 空格
                    art = DARK_ART if (r + f) % 2 == 0 else LIGHT_ART
                mark = "*" if s in highlight else " "
                for i in range(3):
                    rows[i] += mark + art[i] + mark + "|"
            for i in range(3):
                head = "  %d |" % (r + 1) if i == 1 else "    |"
                lines.append(head + rows[i])
            lines.append(sep)
        lines.append("    " + "".join("   %s    " % c
                                      for c in ("hgfedcba" if flip
                                                else "abcdefgh")))
        return "\n".join(lines)

    def render_big(self, flip=False, ascii_only=False, highlight=()):
        """大号棋盘：格子画成方框，看着不费眼。"""
        ranks = range(8) if flip else range(7, -1, -1)
        files = range(7, -1, -1) if flip else range(8)
        sep = "    +" + "-----+" * 8
        lines = [sep]
        for r in ranks:
            row = "  %d |" % (r + 1)
            for f in files:
                s = (r << 4) | f
                p = self.sq[s]
                if p:
                    ch = (PIECE_LETTER[ptype(p)] if pcolor(p) == WHITE
                          else PIECE_LETTER[ptype(p)].lower()) \
                        if ascii_only else UNICODE[p]
                else:
                    ch = ' ' if (r + f) % 2 else '.'
                if s in highlight:
                    row += " *%s* |" % ch
                else:
                    row += "  %s  |" % ch
            lines.append(row)
            lines.append(sep)
        foot = "    " + "".join("   %s  " % c
                                for c in ("hgfedcba" if flip else "abcdefgh"))
        lines.append(foot)
        return "\n".join(lines)

    def render(self, flip=False, ascii_only=False, highlight=(), big=False,
               size=None):
        """size: 'small' | 'big' | 'huge'（big 参数为兼容旧调用保留）。"""
        size = size or ("big" if big else "small")
        if size == "huge":
            return self.render_huge(flip, ascii_only, highlight)
        if size == "big":
            return self.render_big(flip, ascii_only, highlight)
        ranks = range(8) if flip else range(7, -1, -1)
        files = range(7, -1, -1) if flip else range(8)
        lines = ["  +------------------------+"]
        for r in ranks:
            row = "%d |" % (r + 1)
            for f in files:
                s = (r << 4) | f
                p = self.sq[s]
                if p:
                    ch = (PIECE_LETTER[ptype(p)] if pcolor(p) == WHITE
                          else PIECE_LETTER[ptype(p)].lower()) \
                        if ascii_only else UNICODE[p]
                else:
                    ch = '.' if (r + f) % 2 else ':'
                mark = '*' if s in highlight else ' '
                row += mark + ch + ('*' if s in highlight else ' ')
            lines.append(row + "|")
        lines.append("  +------------------------+")
        lines.append("    " + "  ".join("hgfedcba" if flip else "abcdefgh"))
        return "\n".join(lines)


# -------------------------------------------------------------- PGN reader
def strip_pgn(text):
    out, i, depth = [], 0, 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == '{':
            j = text.find('}', i)
            i = n if j < 0 else j + 1
            continue
        if c == ';':
            j = text.find('\n', i)
            i = n if j < 0 else j + 1
            continue
        if c == '[' and depth == 0:
            j = text.find(']', i)
            i = n if j < 0 else j + 1
            continue
        if c == '(':
            depth += 1
            i += 1
            continue
        if c == ')':
            depth = max(0, depth - 1)
            i += 1
            continue
        if depth == 0:
            out.append(c)
        i += 1
    return ''.join(out)


def pgn_moves(text):
    """Extract the SAN token list from a PGN (main line only)."""
    body = strip_pgn(text)
    tokens = []
    for tok in body.replace('\n', ' ').split():
        if tok.startswith('$'):
            continue
        if tok in ('1-0', '0-1', '1/2-1/2', '*'):
            continue
        # strip leading move numbers such as "12." or "12..."
        while tok and (tok[0].isdigit() or tok[0] == '.'):
            j = 0
            while j < len(tok) and tok[j].isdigit():
                j += 1
            if j < len(tok) and tok[j] == '.':
                while j < len(tok) and tok[j] == '.':
                    j += 1
                tok = tok[j:]
            else:
                break
        tok = tok.strip('.')
        if tok and tok not in ('1-0', '0-1', '1/2-1/2', '*'):
            tokens.append(tok)
    return tokens


def pgn_headers(text):
    h = {}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('[') and line.endswith(']'):
            body = line[1:-1]
            if '"' in body:
                k = body.split(' ', 1)[0]
                v = body.split('"')[1]
                h[k] = v
    return h
