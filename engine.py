"""Evaluation + alpha-beta search engine."""

import random
import time

from board import (Board, WHITE, BLACK, PAWN, KNIGHT, BISHOP, ROOK, QUEEN,
                   KING, F_EP, opp, ptype, pcolor, move_uci)

INF = 1 << 30
MATE = 100000
MATE_BOUND = MATE - 1000

VALUE = {PAWN: 100, KNIGHT: 320, BISHOP: 330, ROOK: 500, QUEEN: 900, KING: 0}
PHASE_W = {PAWN: 0, KNIGHT: 1, BISHOP: 1, ROOK: 2, QUEEN: 4, KING: 0}
TOTAL_PHASE = 24

# ------------------------------------------------- piece-square tables (a8..h1)
_PST = {
    PAWN: [
        0, 0, 0, 0, 0, 0, 0, 0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
        5, 5, 10, 25, 25, 10, 5, 5,
        0, 0, 0, 20, 20, 0, 0, 0,
        5, -5, -10, 0, 0, -10, -5, 5,
        5, 10, 10, -20, -20, 10, 10, 5,
        0, 0, 0, 0, 0, 0, 0, 0],
    KNIGHT: [
        -50, -40, -30, -30, -30, -30, -40, -50,
        -40, -20, 0, 0, 0, 0, -20, -40,
        -30, 0, 10, 15, 15, 10, 0, -30,
        -30, 5, 15, 20, 20, 15, 5, -30,
        -30, 0, 15, 20, 20, 15, 0, -30,
        -30, 5, 10, 15, 15, 10, 5, -30,
        -40, -20, 0, 5, 5, 0, -20, -40,
        -50, -40, -30, -30, -30, -30, -40, -50],
    BISHOP: [
        -20, -10, -10, -10, -10, -10, -10, -20,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -10, 0, 5, 10, 10, 5, 0, -10,
        -10, 5, 5, 10, 10, 5, 5, -10,
        -10, 0, 10, 10, 10, 10, 0, -10,
        -10, 10, 10, 10, 10, 10, 10, -10,
        -10, 5, 0, 0, 0, 0, 5, -10,
        -20, -10, -10, -10, -10, -10, -10, -20],
    ROOK: [
        0, 0, 0, 0, 0, 0, 0, 0,
        5, 10, 10, 10, 10, 10, 10, 5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        0, 0, 0, 5, 5, 0, 0, 0],
    QUEEN: [
        -20, -10, -10, -5, -5, -10, -10, -20,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -10, 0, 5, 5, 5, 5, 0, -10,
        -5, 0, 5, 5, 5, 5, 0, -5,
        0, 0, 5, 5, 5, 5, 0, -5,
        -10, 5, 5, 5, 5, 5, 0, -10,
        -10, 0, 5, 0, 0, 0, 0, -10,
        -20, -10, -10, -5, -5, -10, -10, -20],
}
_KING_MID = [
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
    20, 20, 0, 0, 0, 0, 20, 20,
    20, 30, 10, 0, 0, 10, 30, 20]
_KING_END = [
    -50, -40, -30, -20, -20, -30, -40, -50,
    -30, -20, -10, 0, 0, -10, -20, -30,
    -30, -10, 20, 30, 30, 20, -10, -30,
    -30, -10, 30, 40, 40, 30, -10, -30,
    -30, -10, 30, 40, 40, 30, -10, -30,
    -30, -10, 20, 30, 30, 20, -10, -30,
    -30, -30, 0, 0, 0, 0, -30, -30,
    -50, -30, -30, -30, -30, -30, -30, -50]


def _expand(table, white):
    """Map an a8..h1 table onto 0x88 squares for one colour."""
    out = [0] * 128
    for s in range(128):
        if s & 0x88:
            continue
        r, f = s >> 4, s & 7
        idx = (7 - r) * 8 + f if white else r * 8 + f
        out[s] = table[idx]
    return out


PST = {}
for _pt, _tab in _PST.items():
    PST[WHITE | _pt] = _expand(_tab, True)
    PST[BLACK | _pt] = _expand(_tab, False)
KING_PST = {
    'mid': {WHITE: _expand(_KING_MID, True), BLACK: _expand(_KING_MID, False)},
    'end': {WHITE: _expand(_KING_END, True), BLACK: _expand(_KING_END, False)},
}

PASSED_BONUS = (0, 8, 15, 25, 40, 65, 100, 0)
ISOLATED = -14
DOUBLED = -12
BISHOP_PAIR = 30
ROOK_OPEN = 16
ROOK_SEMI = 8
TEMPO = 10


def evaluate(b):
    """Static evaluation in centipawns, from the side-to-move's perspective."""
    sqs = b.sq
    score = 0
    phase = 0
    wp_files = [0] * 8
    bp_files = [0] * 8
    wp_sqs, bp_sqs = [], []
    counts = {WHITE | BISHOP: 0, BLACK | BISHOP: 0}
    pieces = []
    mat = {WHITE: 0, BLACK: 0}
    for s in range(128):
        if s & 0x88:
            continue
        p = sqs[s]
        if not p:
            continue
        t = p & 7
        c = p & 24
        phase += PHASE_W[t]
        if t == PAWN:
            if c == WHITE:
                wp_files[s & 7] += 1
                wp_sqs.append(s)
            else:
                bp_files[s & 7] += 1
                bp_sqs.append(s)
        elif t == BISHOP:
            counts[p] += 1
        if t != KING:
            mat[c] += VALUE[t]
            v = VALUE[t] + PST[p][s]
            score += v if c == WHITE else -v
        pieces.append((s, p, t, c))

    phase = min(phase, TOTAL_PHASE)
    # kings, tapered
    for c in (WHITE, BLACK):
        ks = b.kings[c]
        if ks < 0:
            continue
        mid = KING_PST['mid'][c][ks]
        end = KING_PST['end'][c][ks]
        v = (mid * phase + end * (TOTAL_PHASE - phase)) // TOTAL_PHASE
        score += v if c == WHITE else -v

    # bishop pair
    if counts[WHITE | BISHOP] >= 2:
        score += BISHOP_PAIR
    if counts[BLACK | BISHOP] >= 2:
        score -= BISHOP_PAIR

    # pawn structure
    for s in wp_sqs:
        f, r = s & 7, s >> 4
        if wp_files[f] > 1:
            score += DOUBLED
        if (f == 0 or not wp_files[f - 1]) and (f == 7 or not wp_files[f + 1]):
            score += ISOLATED
        blocked = False
        for ff in range(max(0, f - 1), min(7, f + 1) + 1):
            if bp_files[ff]:
                for bs in bp_sqs:
                    if (bs & 7) == ff and (bs >> 4) > r:
                        blocked = True
                        break
            if blocked:
                break
        if not blocked:
            score += PASSED_BONUS[r]
    for s in bp_sqs:
        f, r = s & 7, s >> 4
        if bp_files[f] > 1:
            score -= DOUBLED
        if (f == 0 or not bp_files[f - 1]) and (f == 7 or not bp_files[f + 1]):
            score -= ISOLATED
        blocked = False
        for ff in range(max(0, f - 1), min(7, f + 1) + 1):
            if wp_files[ff]:
                for ws in wp_sqs:
                    if (ws & 7) == ff and (ws >> 4) < r:
                        blocked = True
                        break
            if blocked:
                break
        if not blocked:
            score -= PASSED_BONUS[7 - r]

    # rooks on (semi-)open files
    for s, p, t, c in pieces:
        if t != ROOK:
            continue
        f = s & 7
        own, foe = (wp_files, bp_files) if c == WHITE else (bp_files, wp_files)
        if not own[f]:
            bonus = ROOK_OPEN if not foe[f] else ROOK_SEMI
            score += bonus if c == WHITE else -bonus

    # endgame mating drive: push the bare king to the edge and close in
    if phase <= 6 and abs(mat[WHITE] - mat[BLACK]) >= 300:
        strong = WHITE if mat[WHITE] > mat[BLACK] else BLACK
        weak = opp(strong)
        if not (wp_sqs if weak == WHITE else bp_sqs):
            ws, ss = b.kings[weak], b.kings[strong]
            wf, wr = ws & 7, ws >> 4
            cmd = (3 - min(wf, 7 - wf)) + (3 - min(wr, 7 - wr))
            dist = abs(wf - (ss & 7)) + abs(wr - (ss >> 4))
            drive = 11 * cmd + 5 * (14 - dist)
            score += drive if strong == WHITE else -drive

    return (score + TEMPO) if b.side == WHITE else (-score + TEMPO)


class TimeUp(Exception):
    pass


EXACT, LOWER, UPPER = 0, 1, 2


class SearchResult(object):
    def __init__(self, move=0, score=0, depth=0, nodes=0, pv=None, elapsed=0.0,
                 mate=None):
        self.move = move
        self.score = score
        self.depth = depth
        self.nodes = nodes
        self.pv = pv or []
        self.elapsed = elapsed
        self.mate = mate

    def __repr__(self):
        return "<%s %+d d%d %dn>" % (move_uci(self.move), self.score,
                                     self.depth, self.nodes)


class Engine(object):
    def __init__(self, seed=None):
        self.tt = {}
        self.killers = [[0, 0] for _ in range(128)]
        self.hist = {}
        self.nodes = 0
        self.deadline = 0.0
        self.rnd = random.Random(seed)

    def new_game(self):
        self.tt.clear()
        self.hist.clear()
        self.killers = [[0, 0] for _ in range(128)]

    # ------------------------------------------------------------- ordering
    def _score_move(self, b, m, ttmove, ply):
        if m == ttmove:
            return 1 << 24
        to = (m >> 8) & 0xFF
        frm = m & 0xFF
        victim = b.sq[to]
        promo = (m >> 16) & 0xF
        if victim or ((m >> 20) & 0xF) == F_EP:
            att = VALUE[b.sq[frm] & 7]
            vic = VALUE[victim & 7] if victim else VALUE[PAWN]
            return (1 << 20) + vic * 16 - att
        if promo:
            return (1 << 19) + VALUE[promo]
        k = self.killers[ply]
        if m == k[0]:
            return 1 << 18
        if m == k[1]:
            return (1 << 18) - 1
        return self.hist.get((b.side, frm, to), 0)

    def _order(self, b, moves, ttmove, ply):
        moves.sort(key=lambda m: self._score_move(b, m, ttmove, ply),
                   reverse=True)

    # ------------------------------------------------------------ quiescence
    def _quiesce(self, b, alpha, beta, ply):
        self.nodes += 1
        if not (self.nodes & 2047) and time.time() > self.deadline:
            raise TimeUp()
        stand = evaluate(b)
        if stand >= beta:
            return stand
        if stand > alpha:
            alpha = stand
        if ply > 40:
            return stand
        moves = b.gen_moves(captures_only=True)
        moves.sort(key=lambda m: self._score_move(b, m, 0, min(ply, 127)),
                   reverse=True)
        me = b.side
        for m in moves:
            victim = b.sq[(m >> 8) & 0xFF]
            gain = VALUE[victim & 7] if victim else VALUE[PAWN]
            promo = (m >> 16) & 0xF
            if promo:
                gain += VALUE[promo]
            if stand + gain + 150 < alpha:
                continue
            b.make(m)
            if b.is_attacked(b.kings[me], b.side):
                b.unmake()
                continue
            s = -self._quiesce(b, -beta, -alpha, ply + 1)
            b.unmake()
            if s > alpha:
                alpha = s
                if alpha >= beta:
                    return alpha
        return alpha

    @staticmethod
    def _has_pieces(b):
        me = b.side
        for s in range(128):
            if s & 0x88:
                continue
            p = b.sq[s]
            if p and (p & 24) == me and (p & 7) not in (PAWN, KING):
                return True
        return False

    # ---------------------------------------------------------------- search
    def _negamax(self, b, depth, alpha, beta, ply, can_null=True):
        self.nodes += 1
        if not (self.nodes & 2047) and time.time() > self.deadline:
            raise TimeUp()
        if ply and (b.halfmove >= 100 or b.is_repetition(2)):
            return 0
        in_check = b.in_check()
        if in_check:
            depth += 1
        if depth <= 0:
            return self._quiesce(b, alpha, beta, ply)

        alpha_orig = alpha
        ttmove = 0
        ent = self.tt.get(b.key)
        if ent is not None:
            e_depth, e_score, e_flag, e_move = ent
            ttmove = e_move
            if ply and e_depth >= depth:
                s = e_score
                if s > MATE_BOUND:
                    s -= ply
                elif s < -MATE_BOUND:
                    s += ply
                if e_flag == EXACT:
                    return s
                if e_flag == LOWER and s > alpha:
                    alpha = s
                elif e_flag == UPPER and s < beta:
                    beta = s
                if alpha >= beta:
                    return s

        # null-move pruning
        if (can_null and ply and not in_check and depth >= 3
                and abs(beta) < MATE_BOUND and self._has_pieces(b)):
            r = 3 if depth > 6 else 2
            b.make_null()
            # NB: no try/finally here — on TimeUp the stack is unwound by
            # _restore(), which knows how to tell null entries from real moves.
            s = -self._negamax(b, depth - 1 - r, -beta, -beta + 1,
                               ply + 1, False)
            b.unmake_null()
            if s >= beta:
                return beta

        moves = b.gen_moves()
        self._order(b, moves, ttmove, min(ply, 127))
        me = b.side
        best, best_move, legal = -INF, 0, 0
        for m in moves:
            frm, to = m & 0xFF, (m >> 8) & 0xFF
            is_cap = bool(b.sq[to]) or ((m >> 20) & 0xF) == F_EP
            promo = (m >> 16) & 0xF
            b.make(m)
            if b.is_attacked(b.kings[me], b.side):
                b.unmake()
                continue
            legal += 1
            gives_check = b.in_check()
            if legal == 1:
                s = -self._negamax(b, depth - 1, -beta, -alpha, ply + 1)
            else:
                red = 0
                if (depth >= 3 and legal > 3 and not is_cap and not promo
                        and not in_check and not gives_check):
                    red = 2 if (legal > 6 and depth >= 5) else 1
                s = -self._negamax(b, depth - 1 - red, -alpha - 1, -alpha,
                                   ply + 1)
                if alpha < s < beta:
                    s = -self._negamax(b, depth - 1, -beta, -alpha, ply + 1)
            b.unmake()
            if s > best:
                best, best_move = s, m
                if s > alpha:
                    alpha = s
                    if alpha >= beta:
                        if not is_cap:
                            k = self.killers[min(ply, 127)]
                            if k[0] != m:
                                k[1] = k[0]
                                k[0] = m
                            key = (me, frm, to)
                            self.hist[key] = self.hist.get(key, 0) + depth * depth
                        break
        if legal == 0:
            return -MATE + ply if in_check else 0

        store = best
        if store > MATE_BOUND:
            store += ply
        elif store < -MATE_BOUND:
            store -= ply
        flag = EXACT if alpha_orig < best < beta else (
            LOWER if best >= beta else UPPER)
        if len(self.tt) > 600000:
            self.tt.clear()
        self.tt[b.key] = (depth, store, flag, best_move)
        return best

    # -------------------------------------------------------------- helpers
    def _pv(self, b, first, maxlen=12):
        pv, made = [], 0
        m = first
        seen = set()
        while m and len(pv) < maxlen:
            if not b.is_legal(m):
                break
            pv.append(m)
            b.make(m)
            made += 1
            if b.key in seen:
                break
            seen.add(b.key)
            ent = self.tt.get(b.key)
            m = ent[3] if ent else 0
        for _ in range(made):
            b.unmake()
        return pv

    @staticmethod
    def _restore(board, base):
        """Undo everything a timed-out search left on the move stack."""
        while len(board.history) > base:
            if board.history[-1][0] == 0:
                board.unmake_null()
            else:
                board.unmake()

    def search(self, board, depth=64, movetime=2.0, on_iter=None):
        """Iterative-deepening search. Returns SearchResult."""
        t0 = time.time()
        self.deadline = t0 + max(0.02, movetime)
        self.nodes = 0
        base = len(board.history)
        legal = board.legal_moves()
        if not legal:
            return SearchResult(elapsed=0.0)
        best = SearchResult(move=legal[0], elapsed=0.0)
        for d in range(1, max(1, depth) + 1):
            try:
                score = self._negamax(board, d, -INF, INF, 0)
            except TimeUp:
                self._restore(board, base)
                break
            ent = self.tt.get(board.key)
            mv = ent[3] if ent and ent[3] else best.move
            if not board.is_legal(mv):
                mv = best.move
            best = SearchResult(mv, score, d, self.nodes,
                                self._pv(board, mv), time.time() - t0,
                                mate_in(score))
            if on_iter:
                on_iter(best)
            if abs(score) > MATE_BOUND:
                break
            if time.time() > self.deadline:
                break
        return best

    MULTIPV = False                     # 自带引擎只有一条主变

    def rank_lines(self, board, depth=64, movetime=2.0, k=3):
        """自带引擎没有 MultiPV，只能给一条主变。

        plans.py 对「只有一条线」的情况会自动收紧判据，不会因此乱报主题。
        """
        r = self.search(board, depth, movetime)
        return [(r.pv, r.score, r.depth)] if r.move else []

    def rank_moves(self, board, depth=4, movetime=2.0):
        """Score every root move with a full window (used for weak levels)."""
        t0 = time.time()
        self.deadline = t0 + max(0.02, movetime)
        self.nodes = 0
        base = len(board.history)
        legal = board.legal_moves()
        scored = [(m, -INF) for m in legal]
        for d in range(1, max(1, depth) + 1):
            cur = []
            try:
                for m, _ in scored:
                    board.make(m)
                    s = -self._negamax(board, d - 1, -INF, INF, 1)
                    board.unmake()
                    cur.append((m, s))
            except TimeUp:
                self._restore(board, base)
                break
            cur.sort(key=lambda x: x[1], reverse=True)
            scored = cur
            if time.time() > self.deadline:
                break
        return scored


def mate_in(score):
    """Convert a score into 'mate in N moves' (positive = side to move mates)."""
    if score > MATE_BOUND:
        return (MATE - score + 1) // 2
    if score < -MATE_BOUND:
        return -((MATE + score + 1) // 2)
    return None


def score_text(score, pov_white=True):
    m = mate_in(score)
    if m is not None:
        if m == 0:
            return "#"                      # 已经将杀
        return "#%s%d" % ('' if m > 0 else '-', abs(m))
    return "%+.2f" % (score / 100.0)


# ------------------------------------------------------------------- levels
# level: (max depth, seconds, noise cp, blunder chance)
LEVELS = {
    1:  (1, 0.05, 150, 0.30),
    2:  (2, 0.10, 110, 0.20),
    3:  (2, 0.20, 80, 0.12),
    4:  (3, 0.35, 55, 0.07),
    5:  (4, 0.60, 35, 0.04),
    6:  (5, 1.00, 22, 0.02),
    7:  (6, 1.50, 12, 0.00),
    8:  (8, 2.50, 5, 0.00),
    9:  (12, 5.00, 0, 0.00),
    10: (24, 10.0, 0, 0.00),
}
# 只写能验证的事实：搜多少层、想多久、会不会故意走坏。
# 这里不写等级分——没有跟有分的对手实测过，写数字就是编。
LEVEL_DESC = {
    1: "极弱 · 1 层 · 常送子",
    2: "很弱 · 2 层 · 常漏着",
    3: "入门 · 2 层 · 偶尔漏着",
    4: "入门+ · 3 层",
    5: "中等 · 4 层 · 噪声较小",
    6: "中等+ · 5 层",
    7: "较强 · 6 层 · 基本按最佳走",
    8: "强 · 8 层 · 不故意走坏",
    9: "很强 · 每步 5 秒全力",
    10: "最强 · 每步 10 秒全力",
}
LEVEL_ELO = LEVEL_DESC          # 兼容旧名字


def choose_move(engine, board, level=5):
    """Pick a move at the requested playing strength."""
    depth, secs, noise, blunder = LEVELS.get(level, LEVELS[5])
    if noise == 0 and blunder == 0:
        return engine.search(board, depth, secs)
    scored = engine.rank_moves(board, depth, secs)
    if not scored:
        return SearchResult()
    best_score = scored[0][1]
    if best_score > MATE_BOUND:            # never miss a forced mate
        m, s = scored[0]
        return SearchResult(m, s, depth, engine.nodes, [m], secs, mate_in(s))
    rnd = engine.rnd
    if rnd.random() < blunder and len(scored) > 1:
        pool = scored[1:min(len(scored), 5)]
        m, s = rnd.choice(pool)
        return SearchResult(m, s, depth, engine.nodes, [m], secs, mate_in(s))
    noisy = [(m, s + rnd.gauss(0, noise)) for m, s in scored]
    noisy.sort(key=lambda x: x[1], reverse=True)
    m = noisy[0][0]
    s = dict(scored)[m]
    return SearchResult(m, s, depth, engine.nodes, [m], secs, mate_in(s))
