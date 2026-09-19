#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""国际象棋训练器 —— 对弈 / 跟棋助手 / 战术题 / 残局 / 复盘

用法:
    python3 trainer.py            进入菜单
    python3 trainer.py play       直接开始对弈
    python3 trainer.py advise     跟棋助手（你报双方着法，它给建议）
    python3 trainer.py blind      盲区训练（将军吃子清单 / 对手威胁 / 谁在白送）
    python3 trainer.py blind en   同上，英文出题（或 CHESS_LANG=en）
    python3 trainer.py puzzle     战术题
    python3 trainer.py drill      残局训练
    python3 trainer.py review [file.pgn]   复盘分析
"""

import os
import random
import sys
import time

from board import (Board, WHITE, BLACK, START_FEN, opp, move_uci,
                   pgn_moves, pgn_headers)
from engine import (Engine, SearchResult, choose_move, evaluate, score_text,
                    mate_in, LEVELS, LEVEL_ELO, MATE_BOUND)
import puzzles as puzzle_db
import book

ASCII = os.environ.get("CHESS_ASCII") == "1"
# 棋盘大小：small / big / huge。huge 每个棋子用三行字符拼，图标最大。
SIZE = os.environ.get("CHESS_SIZE", "big").lower()
if SIZE not in ("small", "big", "huge"):
    SIZE = "big"
if os.environ.get("CHESS_SMALL") == "1":
    SIZE = "small"


GAMES_DIR = os.environ.get("CHESS_GAMES", "games")


def game_path(name):
    """棋谱一律存进 games/ 子目录，跟代码和临时文件分开，不会被误删。"""
    if os.path.dirname(name):          # 用户给了路径就照办
        return name
    try:
        os.makedirs(GAMES_DIR, exist_ok=True)
        return os.path.join(GAMES_DIR, name)
    except OSError:
        return name


AUTOSAVE = "_autosave.pgn"          # 每走一步都覆盖写一份，防止意外丢失


def make_pgn(log, start_fen=START_FEN, result="*", event="跟棋记录"):
    """log 是 [(san, move), ...]，生成标准 PGN。"""
    head = ['[Event "%s"]' % event, '[Site "本地"]',
            '[Date "%s"]' % time.strftime("%Y.%m.%d"),
            '[Result "%s"]' % result]
    if start_fen != START_FEN:
        head += ['[FEN "%s"]' % start_fen, '[SetUp "1"]']
    white_first = Board(start_fen).side == WHITE
    body, n = [], 1
    for i, item in enumerate(log):
        san = item[0]
        if white_first and i % 2 == 0:
            body.append("%d." % (n + i // 2))
        elif not white_first and i % 2 == 1:
            body.append("%d." % (n + (i + 1) // 2))
        elif i == 0:
            body.append("%d..." % n)
        body.append(san)
    body.append(result)
    return "\n".join(head) + "\n\n" + " ".join(body) + "\n"


def review_name(src=None):
    """复盘报告的文件名——跟被分析的棋谱一一对应。

    games/jvaichi.pgn  →  games/review_jvaichi.txt

    这样一眼就知道哪份报告对应哪盘棋，重跑同一盘也直接覆盖旧报告
    （报告头里记着用的哪个引擎、想了多久，不怕搞混）。
    只有粘贴进来的、没有源文件的棋谱才退回时间戳。
    """
    if src:
        stem = os.path.splitext(os.path.basename(src))[0]
        if stem:
            return game_path("review_%s.txt" % stem)
    return game_path(time.strftime("review_%Y%m%d_%H%M%S.txt"))


def write_pgn(name, text):
    path = game_path(name if name.endswith(".pgn") else name + ".pgn")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return os.path.abspath(path)


def autosave(log, start_fen=START_FEN, event="跟棋记录"):
    """静默存一份快照，什么时候崩了都不会丢棋。"""
    if not log:
        return None
    try:
        return write_pgn(AUTOSAVE, make_pgn(log, start_fen, event=event))
    except OSError:
        return None


def board_text(b, flip=False, highlight=()):
    return b.render(flip=flip, ascii_only=ASCII, highlight=highlight,
                    size=SIZE)


SIZE_WORDS = {"small": "small", "小": "small", "缩小": "small",
              "big": "big", "large": "big", "大": "big", "放大": "big",
              "huge": "huge", "超大": "huge", "最大": "huge"}


def confirm_student(who):
    """名字打错会悄悄新建一个档案，很难发现（真事：jerem / Jeremy）。确认一下。"""
    import profile_log
    if not who or who.lower() in QUIT_WORDS:
        return None
    near = profile_log.similar(who)
    if near and near != who and ask_yes("  是不是「%s」？(Y/n) " % near, True):
        return near
    return who


def ask_student():
    """复盘完问一句记进谁的档案。返回 (名字, 执方) 或 (None, None)。"""
    import profile_log
    names = profile_log.list_students()
    hint = ("（现有：%s）" % "、".join(names)) if names else ""
    who = confirm_student(ask("记进哪个学生的档案？(回车 = 不记)%s: " % hint))
    if not who:
        return None, None
    return who, ask_side("  他执哪方？(w/b): ")


def engine_name(eng):
    """报告里要写清楚是谁判的卷——不同引擎跑出来的数字不能混着比。"""
    return getattr(eng, "name", None) or "自带引擎"


def make_engine(quiet=False, builtin_default=False):
    """默认**优先用 Stockfish**（装了就用），找不到才回退到自带引擎。

    例外是 builtin_default=True 的两个模式——**对弈**和**跟棋助手**：
    这两处都会用到难度档（engine.LEVELS），而难度档是拿自带引擎标定的，
    换成 Stockfish 之后同一档明显更强，跟实测的数字对不上。
    这两处要用 Stockfish 就显式设 CHESS_ENGINE=sf。

    环境变量可以强制：
      CHESS_ENGINE=sf       任何地方都用 Stockfish（含对弈对手）
      CHESS_ENGINE=builtin  任何地方都用自带引擎
    """
    want = os.environ.get("CHESS_ENGINE", "").lower()
    if want in ("builtin", "own", "self", "内置", "自带"):
        return Engine()
    if want in ("sf", "stockfish", "uci"):
        pass                                  # 强制外部引擎
    elif builtin_default:
        return Engine()                       # 对弈 / 跟棋默认用自带引擎
    try:
        import uci as uci_mod
        e = uci_mod.UciEngine()
        if not quiet:
            print("已接入外部引擎：%s" % e.name)
        return e
    except Exception as exc:
        if want in ("sf", "stockfish", "uci"):
            print("接外部引擎失败（%s），改用自带引擎。" % exc)
        elif not quiet:
            print("（没找到 Stockfish，用自带引擎分析——它只有 ~1230 的水平，"
                  "关键局面的评分别全信。装了之后会自动使用。）")
        return Engine()


# 胜负已定的门槛（百分之一兵）。走之前和走之后都超过这个数、而且同号，
# 说明这一步不影响结果——「+19 掉到 +17」和「把 5 步杀走成 10 步杀」都算。
# 这类丢分照样打印出来（有教学价值），但不计入失误统计，
# 否则「每 N 步崩一次」会被垃圾时间污染。
DECIDED = 500

# 下完一盘自动复盘时每步想多久（秒）。手动 review 模式会单独问，不受这个影响。
# 用 Stockfish 的话 3 秒比 0.6 秒稳很多，边界失误不会误判。
AUTO_REVIEW_SECS = float(os.environ.get("CHESS_REVIEW_SECS", "3.0"))


def is_decided(before, after):
    """before / after 都是**走棋方视角**的分数。"""
    return (before > DECIDED and after > DECIDED) or \
           (before < -DECIDED and after < -DECIDED)


# 失误分级：(最大损失分, 标签, 记号)
GRADES = [
    (10, "最佳", "!"),
    (30, "好棋", ""),
    (70, "略欠精确", "?!"),
    (150, "失误", "?"),
    (10 ** 9, "严重失误", "??"),
]


def grade(loss):
    for limit, label, mark in GRADES:
        if loss <= limit:
            return label, mark
    return GRADES[-1][1], GRADES[-1][2]


def eval_words(cp, side_to_move):
    """把分数翻译成人话：正数 = 该走棋一方占优，1.00 = 一个兵。"""
    m = mate_in(cp)
    who = "白方" if side_to_move == WHITE else "黑方"
    other = "黑方" if side_to_move == WHITE else "白方"
    if m is not None:
        if m == 0:
            return "已被将杀"
        return "%s %d 步内将杀" % (who if m > 0 else other, abs(m))
    if abs(cp) < 25:
        return "基本均势"
    lead = who if cp > 0 else other
    diff = abs(cp) / 100.0
    if diff < 0.8:
        how = "略优"
    elif diff < 1.6:
        how = "占优"
    elif diff < 3.0:
        how = "明显占优"
    else:
        how = "大优"
    return "%s%s %.1f 个兵" % (lead, how, diff)


def bar(cp, width=24):
    """白方视角的评估条。"""
    cp = max(-800, min(800, cp))
    n = int(round((cp + 800) / 1600.0 * width))
    return "[" + "#" * n + "-" * (width - n) + "]"


SEEN_DIR = os.path.join(GAMES_DIR, "students")


def seen_path(key):
    safe = "".join(c for c in key if c.isalnum() or c in "-_") or "all"
    return os.path.join(SEEN_DIR, "_seen_%s.txt" % safe)


def load_seen(key):
    """练过哪些局面（存 FEN，一行一个）。读不到就当没练过。"""
    try:
        with open(seen_path(key), encoding="utf-8") as f:
            return set(x.strip() for x in f if x.strip())
    except OSError:
        return set()


def save_seen(key, fens):
    try:
        os.makedirs(SEEN_DIR, exist_ok=True)
        with open(seen_path(key), "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(fens)) + "\n")
        return True
    except OSError:
        return False


def flush_input():
    """丢掉引擎思考期间抢先敲进来的内容，免得被当成答案。"""
    try:
        if sys.stdin.isatty():
            import termios
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except Exception:
        pass


def ask(prompt):
    flush_input()
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return "quit"


QUIT_WORDS = ("quit", "exit", "q", "退出")


def ask_side(prompt, default=WHITE):
    """认得 w / b / 白 / 黑 / 我执黑 / 是黑方 / random 之类的说法。"""
    while True:
        c = ask(prompt)
        low = c.lower()
        if low in QUIT_WORDS:
            return None
        if not c:
            return default
        if "黑" in c or "black" in low or low in ("b", "hei"):
            return BLACK
        if "白" in c or "white" in low or low in ("w", "bai"):
            return WHITE
        if low.startswith("r") or "随机" in c:
            return random.choice([WHITE, BLACK])
        print("  没太看懂「%s」。输入 w = 执白，b = 执黑（直接回车用默认）。" % c)


def ask_number(prompt, default, lo, hi, max_words=("最强", "最难", "最高",
                                                   "max", "最好", "最厉害")):
    """从一句话里把数字挑出来；说「最强」之类就取上限。"""
    import re
    while True:
        c = ask(prompt)
        low = c.lower()
        if low in QUIT_WORDS:
            return None
        if not c:
            return default
        # 粘错东西的时候不要硬从里面抠数字出来。真事：粘进来一条 figma 网址，
        # 「R9zSQ...」里的 9 被当成了「每步 9 秒」，一盘棋跑了十分钟。
        if "://" in c or c.count("/") >= 2 or len(c) > 30:
            print("  这不像个数字（粘错了？）。要停请按 Ctrl-C，或输入 quit。")
            continue
        m = re.search(r"\d+(?:\.\d+)?", c)
        if m:
            return max(lo, min(hi, float(m.group())))
        if any(k in c or k in low for k in max_words):
            return hi
        if any(k in c or k in low for k in ("最弱", "最简单", "min", "最低")):
            return lo
        print("  没太看懂「%s」。给个 %s 到 %s 之间的数字就行（回车用默认 %s）。"
              % (c, lo, hi, default))


def ask_yes(prompt, default=True):
    while True:
        c = ask(prompt)
        low = c.lower()
        if low in QUIT_WORDS:
            return None
        if not c:
            return default
        if low[0] in "yt1" or any(k in c for k in ("是", "好", "要", "开", "对",
                                                   "嗯", "行")):
            return True
        if low[0] in "nf0" or any(k in c for k in ("否", "不", "关", "别")):
            return False
        print("  没太看懂「%s」。回答 y 或 n 就行。" % c)


def show(b, human=WHITE, last=None, note=""):
    print()
    print(board_text(b, flip=(human == BLACK),
                     highlight=() if last is None else
                     (last & 0xFF, (last >> 8) & 0xFF)))
    turn = "白方" if b.side == WHITE else "黑方"
    line = "  第 %d 回合 · 轮到%s" % (b.fullmove, turn)
    if note:
        line += " · " + note
    print(line)


def material(b):
    from engine import VALUE
    from board import ptype, pcolor, KING
    s = 0
    for q in range(128):
        if q & 0x88:
            continue
        p = b.sq[q]
        if p and ptype(p) != KING:
            s += VALUE[ptype(p)] if pcolor(p) == WHITE else -VALUE[ptype(p)]
    return s


def pv_san(b, pv, limit=6, numbered=False):
    """主变是双方轮流走的。numbered=True 时加上回合数，一眼能看出谁走的。"""
    out, made, first = [], 0, True
    for m in pv[:limit]:
        if not b.is_legal(m):
            break
        san = b.san(m)
        if numbered:
            if b.side == WHITE:
                san = "%d.%s" % (b.fullmove, san)
            elif first:
                san = "%d...%s" % (b.fullmove, san)
        out.append(san)
        first = False
        b.make(m)
        made += 1
    for _ in range(made):
        b.unmake()
    return " ".join(out)


HELP = """
可用指令:
  e2e4 / Nf3 / O-O   走棋（坐标或简写记谱都行）
  hint               给我提示（引擎推荐的一步 + 后续变化）
  eval               当前局面评估
  moves              列出所有合法着法
  undo               悔棋（退回我的上一步）
  coach              开/关实时教练点评
  level N            改难度 1-10
  small / big / huge 棋盘三档大小（huge 的棋子用三行字符拼，最大）
  flip               翻转棋盘
  fen                显示当前 FEN
  pgn                显示当前对局的 PGN
  save [文件名]      保存对局为 PGN
  review             复盘目前为止的所有着法
  new                重新开局
  resign / quit      认输 / 退出
"""


class Session(object):
    """一局棋（对弈 / 残局训练共用）。"""

    def __init__(self, fen=START_FEN, human=WHITE, level=5, coach=True,
                 goal=None, title=""):
        self.b = Board(fen)
        self.start_fen = fen
        self.human = human
        self.level = level
        self.coach = coach
        self.goal = goal          # None | 'win' | 'draw'
        self.title = title
        self.eng = make_engine(builtin_default=True)
        self.eng.new_game()
        self.log = []             # [(san, move, loss or None)]
        self.losses = []
        self.wplosses = []
        self.coach_secs = None    # None = 按难度自动

    # -------------------------------------------------------------- helpers
    def coach_time(self):
        if self.coach_secs:
            return self.coach_secs
        return 0.5 if self.level <= 6 else 1.0

    def best(self, movetime=None):
        return self.eng.search(self.b, 64, movetime or self.coach_time())

    def eval_note(self):
        r = self.best(0.25)
        cp = r.score if self.b.side == WHITE else -r.score
        return "%s %s %s" % (bar(cp if abs(cp) < 90000 else
                                 (800 if cp > 0 else -800)),
                             score_text(cp), eval_words(r.score, self.b.side))

    def pgn(self, result="*"):
        head = ['[Event "训练对局"]', '[Site "本地"]',
                '[Date "%s"]' % time.strftime("%Y.%m.%d"),
                '[White "%s"]' % ("我" if self.human == WHITE
                                  else "引擎 L%d" % self.level),
                '[Black "%s"]' % ("我" if self.human == BLACK
                                  else "引擎 L%d" % self.level),
                '[Result "%s"]' % result]
        if self.start_fen != START_FEN:
            head.append('[FEN "%s"]' % self.start_fen)
            head.append('[SetUp "1"]')
        body, n = [], 1
        white_first = Board(self.start_fen).side == WHITE
        i = 0
        if not white_first and self.log:
            body.append("%d..." % n)
        for san, _m, _l in self.log:
            if white_first and i % 2 == 0:
                body.append("%d." % (n + i // 2))
            elif not white_first and i % 2 == 1:
                body.append("%d." % (n + (i + 1) // 2))
            body.append(san)
            i += 1
        body.append(result)
        return "\n".join(head) + "\n\n" + " ".join(body) + "\n"

    # ---------------------------------------------------------------- moves
    def human_move(self, m):
        """走人类的一步，若开教练则打分。"""
        in_book = m in book.BOOK.get(self.b.key, {})
        if in_book and self.coach:
            san = self.b.san(m)
            self.b.make(m)
            name = book.current_name(self.b)
            self.losses.append(0)
            self.wplosses.append(0.0)
            print("  你走 %s —— 开局理论%s" % (san, "（%s）" % name if name else ""))
            self.log.append((san, m, 0))
            return san
        before = self.best() if self.coach else None
        best_line = pv_san(self.b, before.pv, 4) if before else ""
        san = self.b.san(m)
        self.b.make(m)
        loss = None
        if before is not None:
            if self.b.legal_moves():
                mine = -self.best().score
            else:
                mine = 100000 if self.b.in_check() else 0
            loss = 0 if before.move == m else \
                min(1000, max(0, before.score - mine))
            self.losses.append(loss)
            self.wplosses.append(0.0 if not loss
                                 else wp_loss(before.score, mine))
            label, mark = grade(loss)
            msg = "  你走 %s%s —— %s" % (san, mark, label)
            if loss > 30 and before.move != m:
                msg += "（更好: %s，少丢 %d 分）" % (best_line, loss)
            print(msg)
        self.log.append((san, m, loss))
        autosave(self.log, self.start_fen, "训练对局")
        return san

    def engine_move(self):
        t0 = time.time()
        bm, bname = book.probe(self.b, self.eng.rnd)
        if bm is not None:
            san = self.b.san(bm)
            self.b.make(bm)
            self.log.append((san, bm, None))
            autosave(self.log, self.start_fen, "训练对局")
            print("  引擎走 %-8s (开局库%s)"
                  % (san, "：" + bname if bname else ""))
            return bm
        sys.stdout.write("  引擎思考中…")
        sys.stdout.flush()
        r = choose_move(self.eng, self.b, self.level)
        if not r.move:
            print()
            return None
        san = self.b.san(r.move)
        self.b.make(r.move)
        self.log.append((san, r.move, None))
        autosave(self.log, self.start_fen, "训练对局")
        print("\r  引擎走 %-8s (%.1fs)          " % (san, time.time() - t0))
        return r.move

    # ----------------------------------------------------------------- loop
    def run(self):
        if self.title:
            print("\n=== %s ===" % self.title)
            if self.goal:
                print("目标：%s。你执%s。"
                      % ("取胜" if self.goal == "win" else "守和",
                         "白" if self.human == WHITE else "黑"))
        print("难度 L%d (%s)  ·  输入 help 看指令" %
              (self.level, LEVEL_ELO[self.level]))
        last = None
        while True:
            out = self.b.outcome()
            if out:
                show(self.b, self.human, last)
                self.finish(out)
                return
            if self.b.side != self.human:
                show(self.b, self.human, last)
                last = self.engine_move()
                continue
            show(self.b, self.human, last, self.eval_note())
            cmd = ask("你走: ")
            low = cmd.lower()
            if low in ("quit", "exit", "q"):
                print("再见！")
                return
            if low in ("resign", "认输"):
                self.finish(("0-1" if self.human == WHITE else "1-0", "认输"))
                return
            if low in ("help", "h", "?"):
                print(HELP)
                continue
            if low in ("hint", "tip"):
                bm, bname = book.probe(self.b, self.eng.rnd)
                if bm is not None:
                    print("  提示: %s   （开局理论%s）"
                          % (self.b.san(bm),
                             "：" + bname if bname else ""))
                    continue
                r = self.best(max(1.0, self.coach_time()))
                print("  提示: %s   (%s)  后续: %s"
                      % (self.b.san(r.move), score_text(r.score),
                         pv_san(self.b, r.pv, 6)))
                continue
            if low in ("eval", "分数"):
                r = self.best(1.0)
                cp = r.score if self.b.side == WHITE else -r.score
                print("  静态评估 %+.2f   搜索 %s (深度%d)  主变: %s"
                      % (evaluate(self.b) / 100.0 *
                         (1 if self.b.side == WHITE else -1),
                         score_text(cp), r.depth, pv_san(self.b, r.pv, 6)))
                continue
            if low in ("moves", "m"):
                legal = self.b.legal_moves()
                print("  " + "  ".join(sorted(self.b.san(x, legal)
                                              for x in legal)))
                continue
            if low in ("undo", "u", "悔棋"):
                n = 0
                while self.b.history and n < 2:
                    self.b.unmake()
                    if self.log:
                        self.log.pop()
                    n += 1
                    if self.b.side == self.human:
                        break
                last = None
                print("  已悔棋。")
                continue
            if low == "coach":
                self.coach = not self.coach
                print("  教练点评：%s" % ("开" if self.coach else "关"))
                continue
            if low.startswith("level"):
                try:
                    v = int(low.split()[1])
                    if v in LEVELS:
                        self.level = v
                        print("  难度改为 L%d (%s)" % (v, LEVEL_ELO[v]))
                    else:
                        print("  难度必须是 1-10")
                except (IndexError, ValueError):
                    print("  用法: level 5")
                continue
            if low in SIZE_WORDS or cmd in SIZE_WORDS:
                globals()["SIZE"] = SIZE_WORDS.get(low) or SIZE_WORDS[cmd]
                print("  棋盘大小：%s" % SIZE)
                last = None
                continue
            if low == "flip":
                self.human = opp(self.human)
                print("  已翻转视角（现在你执%s）"
                      % ("白" if self.human == WHITE else "黑"))
                continue
            if low == "fen":
                print("  " + self.b.fen())
                continue
            if low == "pgn":
                print(self.pgn())
                continue
            if low.startswith("save"):
                parts = cmd.split(None, 1)
                name = parts[1].strip() if len(parts) > 1 else \
                    time.strftime("game_%Y%m%d_%H%M%S.pgn")
                if not name.endswith(".pgn"):
                    name += ".pgn"
                name = game_path(name)
                with open(name, "w", encoding="utf-8") as f:
                    f.write(self.pgn())
                print("  已保存到 %s" % os.path.abspath(name))
                continue
            if low == "review":
                review_moves(self.start_fen, [s for s, _, _ in self.log])
                continue
            if low == "new":
                self.__init__(START_FEN, self.human, self.level, self.coach)
                last = None
                continue
            if not cmd:
                continue
            m = self.b.parse_move(cmd)
            if m is None:
                print("  看不懂或不合法：%s （试试 e2e4 或 Nf3，moves 可列出所有着法）"
                      % cmd)
                continue
            self.human_move(m)
            last = m

    def finish(self, out):
        result, reason = out
        zh = {"checkmate": "将杀", "stalemate": "逼和", "认输": "认输",
              "fifty-move rule": "50 回合规则和棋",
              "threefold repetition": "三次重复和棋",
              "insufficient material": "子力不足和棋"}
        print("\n对局结束：%s（%s）" % (result, zh.get(reason, reason)))
        if self.goal:
            won = (result == "1-0" and self.human == WHITE) or \
                  (result == "0-1" and self.human == BLACK)
            drew = result == "1/2-1/2"
            ok = won if self.goal == "win" else (drew or won)
            print("训练目标：%s" % ("完成 ✓" if ok else "未完成 ✗"))
        if self.losses:
            acpl = sum(self.losses) / float(len(self.losses))
            awl = sum(self.wplosses) / float(len(self.wplosses))
            blunders = sum(1 for x in self.losses if x > 150)
            mistakes = sum(1 for x in self.losses if 70 < x <= 150)
            print("你的平均每步损失 %.0f 分 · 失误 %d · 严重失误 %d · 估算准确率 %.0f%%"
                  % (acpl, mistakes, blunders, accuracy(awl)))
        if self.log:
            path = write_pgn(time.strftime("game_%Y%m%d_%H%M%S.pgn"),
                             self.pgn(result))
            print("棋谱已自动保存：%s" % path)
            if ask_yes("要现在复盘分析吗？(Y/n) ", True):
                who, side = ask_student()
                review_moves(self.start_fen, [x[0] for x in self.log],
                             AUTO_REVIEW_SECS,
                             review_name(path),
                             student=who, student_side=side,
                             result=self.b.outcome()[0] if self.b.outcome()
                             else "")


def win_pct(cp):
    """把分数换算成胜率百分比（用于计算准确率）。"""
    import math
    cp = max(-1200, min(1200, cp))
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)


def wp_loss(before_cp, after_cp):
    return max(0.0, win_pct(before_cp) - win_pct(after_cp))


def accuracy(avg_wp_loss):
    """由平均胜率损失估算准确率（近似值，仅供参考）。"""
    import math
    return max(0.0, min(100.0,
                        103.1668 * math.exp(-0.04354 * avg_wp_loss) - 3.1669))


# ------------------------------------------------------------------ 复盘分析
def review_moves(fen, sans, seconds=0.8, out_file=None,
                 student=None, student_side=None, result=""):
    b = Board(fen)
    evals = []
    print("\n分析中（每步 %.1f 秒）…" % seconds)
    eng = make_engine()
    eng.new_game()
    rows = []
    truncated = None
    # 结构诊断：子力好不好用，全是数出来的，不花引擎时间
    import structure as st
    import errors as err
    tags = {WHITE: {}, BLACK: {}}
    junk = {}                                # 已定胜负局面里的丢分，单独记
    dev = {WHITE: st.Developed(), BLACK: st.Developed()}
    prev_snap = {WHITE: None, BLACK: None}
    series = {WHITE: [], BLACK: []}
    for i, san in enumerate(sans):
        m = b.parse_move(san)
        if m is None:
            print("\n第 %d 手 '%s' 无法解析，停止分析。" % (i + 1, san))
            truncated = (i + 1, san)
            break
        r = eng.search(b, 64, seconds)
        best_score = r.score
        # 引擎推荐和实战走的是同一步时就不必再“建议”了
        best_line = "" if r.move == m else pv_san(b, r.pv, 4)
        mover = b.side
        real_san = b.san(m)
        fen_before = b.fen()
        dev[mover].apply(b, m)              # 必须在 make 之前
        b.make(m)
        snap = st.snapshot(b, mover, dev[mover].squares())
        mv_no = b.fullmove - 1 if mover == BLACK else b.fullmove
        if snap["worst"]:
            series[mover].append((mv_no, snap["worst_label"],
                                  snap["worst"][2]))
        snotes = st.notes(prev_snap[mover], snap) if prev_snap[mover] else []
        prev_snap[mover] = snap
        if b.legal_moves():
            after = -eng.search(b, 64, seconds).score
        else:
            after = 100000 if b.in_check() else 0
        # 走的就是引擎首选 → 不算损失（两次搜索深度不同会有正常波动）
        loss = 0 if r.move == m else min(1000, max(0, best_score - after))
        label, mark = grade(loss)
        decided = is_decided(best_score, after)
        if decided and loss > 30:
            label += "·已定"                  # 胜负已定，不计入统计
        if loss > 70 and not decided:        # 只给「失误」以上的着法分类
            try:
                for t in err.classify(Board(fen_before), m, b, r.move):
                    tags[mover][t] = tags[mover].get(t, 0) + 1
            except Exception:
                pass
        rows.append((i + 1, mover, real_san, mark, label, loss,
                     score_text(after if mover == WHITE else -after),
                     best_line, mv_no, snotes))
        if decided:
            junk[mover] = junk.get(mover, 0) + (1 if loss > 150 else 0)
        else:
            evals.append((mover, loss,
                          0.0 if not loss else wp_loss(best_score, after)))
        sys.stdout.write("\r  已分析 %d/%d 手" % (i + 1, len(sans)))
        sys.stdout.flush()
    print()
    lines = ["复盘报告  (%s)" % time.strftime("%Y-%m-%d %H:%M"),
             "分析引擎: %s · 每步 %.1f 秒" % (engine_name(eng), seconds),
             "起始局面: %s" % fen]
    if truncated:
        lines.append("!! 只分析了前 %d 手：第 %d 手 '%s' 无法解析，后面的棋没看。"
                     % (len(rows), truncated[0], truncated[1]))
    elif len(rows) < len(sans):
        lines.append("!! 只分析了前 %d 手（棋谱共 %d 手）。"
                     % (len(rows), len(sans)))
    lines.append("")
    lines.append("%-5s %-4s %-8s %-10s %-7s %s"
                 % ("手数", "方", "实战", "评价", "评分", "引擎建议"))
    for n, mover, san, mark, label, loss, sc, line, _mv, _sn in rows:
        who = "白" if mover == WHITE else "黑"
        lines.append("%-5d %-4s %-8s %-10s %-7s %s"
                     % (n, who, san + mark, label + ("(-%d)" % loss if loss > 30 else ""),
                        sc, line if loss > 30 else ""))
    if any(tags.values()):
        lines.append("")
        lines.append("———— 失误类型（机械判定，见 errors.py）————")
        for color, nm in ((WHITE, "白方"), (BLACK, "黑方")):
            if tags[color]:
                bits = ["%s×%d" % (err.label(t), n)
                        for t, n in sorted(tags[color].items(),
                                           key=lambda kv: -kv[1])]
                lines.append("  %s：%s" % (nm, " · ".join(bits)))

    struct = ["", "———— 结构诊断（子力好不好用，纯数出来的，没用引擎）————",
              "「最差的子」= 已经出动过的子里，活动格数最少的那个。"]
    hit = False
    avg = []
    for color, name in ((WHITE, "白方"), (BLACK, "黑方")):
        ss = series[color]
        if ss:
            avg.append("%s 全程平均 %.1f 个落点"
                       % (name, sum(x[2] for x in ss) / float(len(ss))))
    if avg:
        struct.append("  " + " · ".join(avg))
    for color, name in ((WHITE, "白方"), (BLACK, "黑方")):
        t = st.trend(series[color])
        if t:
            a, z = series[color][t[0]], series[color][t[1]]
            struct.append("  %s：第 %d 回合 %s(%d 个落点) 一路掉到 第 %d 回合 "
                          "%s(%d)，中间没回升过。"
                          % (name, a[0], a[1], a[2], z[0], z[1], z[2]))
            hit = True
    for _n, mover, san, mark, _label, loss, _sc, _line, mv, sn in rows:
        if loss > 30 and sn:
            struct.append("  第 %d 回合 %s %s%s → %s"
                          % (mv, "白" if mover == WHITE else "黑",
                             san, mark, " · ".join(sn)))
            hit = True
    if hit:
        lines += struct

    for color, name in ((WHITE, "白方"), (BLACK, "黑方")):
        ls = [l for c, l, _w in evals if c == color]
        ws = [w for c, _l, w in evals if c == color]
        if ls:
            acpl = sum(ls) / float(len(ls))
            lines.append("")
            extra = ("   （另有 %d 步严重丢分发生在胜负已定之后，未计入）"
                     % junk[color]) if junk.get(color) else ""
            lines.append(("%s: 平均损失 %.0f 分 · 略欠精确 %d · 失误 %d · "
                          "严重失误 %d · 估算准确率 %.0f%%"
                          % (name, acpl,
                             sum(1 for x in ls if 30 < x <= 70),
                             sum(1 for x in ls if 70 < x <= 150),
                             sum(1 for x in ls if x > 150),
                             accuracy(sum(ws) / float(len(ws))))) + extra)
    text = "\n".join(lines)
    print()
    print(text)
    if out_file:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print("\n报告已保存到 %s" % os.path.abspath(out_file))

    if student and student_side in (WHITE, BLACK):
        ls = [l for c, l, _w in evals if c == student_side]
        if ls:
            import profile_log
            blunders = sum(1 for x in ls if x > 150)
            row = {"color": "白" if student_side == WHITE else "黑",
                   "result": result,
                   "moves": len(ls),
                   "acpl": "%.0f" % (sum(ls) / float(len(ls))),
                   "inaccuracies": sum(1 for x in ls if 30 < x <= 70),
                   "mistakes": sum(1 for x in ls if 70 < x <= 150),
                   "blunders": blunders,
                   "moves_per_blunder": ("%.1f" % (len(ls) / float(blunders))
                                         if blunders else ""),
                   "note": os.path.basename(out_file or "")}
            row.update({t: n for t, n in tags[student_side].items()})
            path = profile_log.record(student, row)
            if path:
                print("已记入 %s 的档案：%s" % (student, path))
                rep = profile_log.report(student)
                if rep:
                    print(rep)
    return text


def review_batch(paths):
    """一次复盘多个棋谱：时间和学生只问一次，Ctrl-C 停掉整批。

    为什么要在程序里做，而不是让用户写 shell 循环：Ctrl-C 只杀掉当前这个
    python 进程，shell 的 for 循环会若无其事地起下一个，看上去就像「停不下来」。
    """
    paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        print("没有能读的棋谱。")
        return
    print("要复盘 %d 个棋谱：%s"
          % (len(paths), "、".join(os.path.basename(p) for p in paths)))
    sec = ask_number("每步分析时间（秒，回车 = 0.8）: ", 0.8, 0.2, 10.0)
    if sec is None:
        return
    who = ask("全部记进哪个学生的档案？(回车 = 都不记): ")
    side = None
    if who and who.lower() not in QUIT_WORDS:
        who = confirm_student(who)
        side = ask_side("  他执哪方？(w/b，各盘不同就回车跳过): ") if who else None
    else:
        who = None
    print("（分析过程中按 Ctrl-C 会停掉整批，已完成的报告都留着。）")
    done = []
    for i, p in enumerate(paths, 1):
        print("\n———— [%d/%d] %s ————" % (i, len(paths), os.path.basename(p)))
        try:
            raw = open(p, encoding="utf-8", errors="ignore").read()
            head = pgn_headers(raw)
            sans = pgn_moves(raw)
            if not sans:
                print("没找到着法，跳过。")
                continue
            review_moves(head.get("FEN", START_FEN), sans, sec,
                         review_name(p),
                         student=who if side is not None else None,
                         student_side=side, result=head.get("Result", ""))
            done.append(p)
        except KeyboardInterrupt:
            print("\n已停止。完成 %d/%d，报告都在 %s/。"
                  % (len(done), len(paths), GAMES_DIR))
            return
    print("\n全部完成：%d 个报告写在 %s/。" % (len(done), GAMES_DIR))


def review_mode(path=None):
    if path and os.path.exists(path):
        raw = open(path, encoding="utf-8", errors="ignore").read()
    else:
        print("粘贴 PGN 或着法（如 1.e4 e5 2.Nf3），空行结束；或直接回车用示例对局：")
        buf = []
        while True:
            line = ask("")
            if line.lower() == "quit":
                return
            if line == "":
                break
            buf.append(line)
        raw = "\n".join(buf)
        if not raw.strip():
            raw = ("1.e4 e5 2.Nf3 Nc6 3.Bc4 Nf6 4.Ng5 d5 5.exd5 Nxd5 "
                   "6.Nxf7 Kxf7 7.Qf3+ Ke6 8.Nc3 Nb4 9.Qe4 c6 10.a3 Na6 "
                   "11.d4 Nc7")
            print("（使用示例对局：弗里德里希变例）")
    head = pgn_headers(raw)
    fen = head.get("FEN", START_FEN)
    sans = pgn_moves(raw)
    if not sans:
        print("没找到着法。")
        return
    sec = ask_number("每步分析时间（秒，回车 = 0.8）: ", 0.8, 0.2, 10.0)
    if sec is None:
        return
    name = review_name(path if path and os.path.exists(path) else None)
    # 记进学生档案（可选）——档案跟踪的是「每 N 步崩一次」，比等级分敏感得多
    hint = " / ".join(x for x in (head.get("White"), head.get("Black")) if x)
    who = ask("记进哪个学生的档案？(回车 = 不记%s): "
              % ("，这盘是 " + hint if hint else ""))
    side = None
    if who and who.lower() not in QUIT_WORDS:
        side = ask_side("  他执哪方？(w/b): ")
    else:
        who = None
    review_moves(fen, sans, sec, name, student=who, student_side=side,
                 result=head.get("Result", ""))


# -------------------------------------------------------------- 跟棋助手模式
ADVISOR_HELP = """
你只要按顺序报出双方走的着法就行，轮到你时我会自动给建议。

  e4        报一步棋（坐标 e2e4 或简写 Nf3 都行）
  e4 e5 Nf3 一次报好几步也可以，空格隔开
  top       列出前几个候选着法和分数
  think 5   把思考时间改成 5 秒
  again     重新想一遍（想久一点）
  undo      收回最后一步（undo 2 = 收回两步）
  side b    改成我执黑（side w = 改成执白），选错了不用重开
  load      列出 games/ 里的棋谱让你选编号；load 1 或 load 文件名 也行
  new       从头开始一盘新的
  small/big/huge 棋盘三档大小
  board     重新显示棋盘
  eval      当前评估
  fen       打印当前局面的 FEN（可贴出来或塞进 cct 分析）
  cct       列出「我所有的将军/吃子/威胁」——先自己口报，再敲这个对答案
  moves     列出所有合法着法
  fen <FEN> 从指定局面开始
  save      把到目前为止的棋谱存成 PGN
  resign    认输结束（可存谱、可直接复盘）
  quit      退出
"""


def advise(eng, b, secs, verbose=True, use_book=True, level=None):
    """给出当前该走方的推荐着法（先查开局库，再交给引擎算）。

    level 给定（1-8）时，额外算一步「这个难度的人会走什么」并一起显示——
    用来扮演特定水平的对手，或者看「学生大概会走哪步 vs 正确是哪步」。
    满血建议永远都算，不会因为设了难度就看不到正解。
    """
    if use_book:
        bm, bname = book.probe(b, eng.rnd)
        if bm is not None:
            if verbose:
                print("\n  ▶ 建议走: %s      （开局库%s）"
                      % (b.san(bm), "：" + bname if bname else ""))
                print("    这是公认的主流走法；想让引擎自己算就打 again。")
            return SearchResult(bm, 0, 0, 0, [bm], 0.0)
    t0 = time.time()

    def on_iter(res):
        if verbose and res.move:
            sys.stdout.write(
                "\r  思考中… 深度 %-2d  暂定 %-7s %-7s  %.0f/%.0f 秒     "
                % (res.depth, b.san(res.move), score_text(res.score),
                   time.time() - t0, secs))
            sys.stdout.flush()

    # 支持 MultiPV 的引擎（Stockfish）一次搜索就拿三条主变，用来归纳主题；
    # 自带引擎没有 MultiPV，走原来的路径，保留逐层刷新的思考进度。
    lines = []
    if getattr(eng, "MULTIPV", False):
        if verbose:
            sys.stdout.write("  思考中…（3 条主变）")
            sys.stdout.flush()
        try:
            lines = eng.rank_lines(b, 64, secs, k=3)
        except Exception:
            lines = []
        if lines:
            pv, sc, dp = lines[0]
            r = SearchResult(pv[0], sc, dp, 0, list(pv), time.time() - t0)
    if not lines:
        r = eng.search(b, 64, secs, on_iter=on_iter if verbose else None)
        lines = [(r.pv, r.score, r.depth)] if r.move else []
    if verbose:
        sys.stdout.write("\r" + " " * 66 + "\r")
        sys.stdout.flush()
    if not r.move:
        return None
    lvl_move = None
    if level is not None and 1 <= level < 9:
        lr = choose_move(eng, b, level)          # 这一档会走什么
        if lr.move and lr.move != r.move:
            lvl_move = lr.move
    if verbose:
        if lvl_move is not None:
            # 用满血搜索给这一档选的那步打分，才知道差多少
            b.make(lvl_move)
            gap = r.score - (-eng.search(b, 64, secs).score)
            b.unmake()
            print("\n  ▶ L%d 会走: %s      比最佳差 %.2f 个兵"
                  % (level, b.san(lvl_move), max(0.0, gap) / 100.0))
            print("  ▶ 最佳是:  %s      评估 %s（%s）   (深度 %d, 想了 %.1f 秒)"
                  % (b.san(r.move), score_text(r.score),
                     eval_words(r.score, b.side), r.depth, time.time() - t0))
        else:
            if level is not None and 1 <= level < 9:
                print("\n  （L%d 这次选的就是最佳着法）" % level)
            print("\n  ▶ 建议走: %s      评估 %s（%s）   (深度 %d, 想了 %.1f 秒)"
                  % (b.san(r.move), score_text(r.score),
                     eval_words(r.score, b.side), r.depth, time.time() - t0))
        line = pv_san(b, r.pv, 12, numbered=True)
        if line:
            print("    预计后续: %s" % line)
        try:
            import plans
            th = plans.format_themes(b, [pv for pv, _s, _d in lines],
                                     "en" if LANG == "en" else "zh")
        except Exception:
            th = ""
        if th:
            print("    主题: %s" % th)
    return r


def advisor_mode():
    print("\n=== 跟棋助手 ===")
    print("你在别处下棋，把双方的着法报给我，轮到你的时候我告诉你走哪一步。")
    me = ask_side("你执白还是黑？(w/b, 回车 = 白): ")
    if me is None:
        return
    secs = ask_number("每次思考几秒？(回车 = 2，想要最强就打「最强」): ",
                      2.0, 0.3, 15.0)
    if secs is None:
        return
    lvl = ask_number("按哪个难度给建议？(1-8，回车 = 满血；"
                     "设了之后会同时显示「这一档会走什么」和「最佳是什么」): ",
                     0, 0, 8)
    if lvl is None:
        return
    level = int(lvl) if lvl and 1 <= lvl <= 8 else None
    b = Board(START_FEN)
    start_fen = START_FEN
    eng = make_engine(builtin_default=True)    # 跟棋也有难度档，同样默认自带引擎
    eng.new_game()
    log = []
    print("\n好，你执%s，我每步想 %.1f 秒。%s"
          % ("白" if me == WHITE else "黑", secs,
             "白方先走，所以我先给你建议。" if me == WHITE
             else "白方是对手，请先把白方走的第一步报给我。"))
    if level:
        print("难度设成 L%d——每次会先显示「L%d 会走什么」，再显示最佳着法。"
              % (level, level))
    print("（选错了不用重开，打 side b 就改成执黑；"
          "level N 改难度，level 0 回到满血；help 看全部指令）")
    pending = True                      # 是否需要给建议
    suggested = None                    # 刚刚建议的那一步（回车就走它）
    while True:
        out = b.outcome()
        if out:
            show(b, me, log[-1][1] if log else None)
            zh = {"checkmate": "将杀", "stalemate": "逼和",
                  "fifty-move rule": "50 回合规则和棋",
                  "threefold repetition": "三次重复和棋",
                  "insufficient material": "子力不足和棋"}
            print("\n棋局结束：%s（%s）" % (out[0], zh.get(out[1], out[1])))
            if log:
                path = write_pgn(time.strftime("game_%Y%m%d_%H%M%S.pgn"),
                                 make_pgn(log, start_fen, out[0]))
                print("棋谱已自动保存：%s" % path)
                if ask_yes("要现在复盘分析吗？(Y/n) ", True):
                    who, side = ask_student()
                    review_moves(start_fen, [x[0] for x in log],
                                 AUTO_REVIEW_SECS,
                                 review_name(path),
                                 student=who, student_side=side,
                                 result=out[0] if out else "")
            return
        if b.side == me and pending:
            show(b, me, log[-1][1] if log else None)
            res = advise(eng, b, secs, level=level)
            suggested = res.move if res else None
            pending = False
            prompt = "你实际走了什么？(回车 = 就走建议的那步): "
        elif b.side == me:
            prompt = "你实际走了什么？(回车 = 就走建议的那步): "
        else:
            if pending:
                show(b, me, log[-1][1] if log else None)
                pending = False
            prompt = "对方（%s方）走了什么？: " % ("白" if b.side == WHITE
                                                else "黑")
        cmd = ask(prompt)
        low = cmd.lower()
        if low in ("quit", "exit", "q"):
            print("再见！")
            return
        if low in ("resign", "认输"):
            result = "0-1" if me == WHITE else "1-0"
            print("你认输了（判负 %s）。" % result)
            if log and ask_yes("要把这盘存下来并复盘吗？(Y/n) ", True):
                path = write_pgn(time.strftime("advice_%Y%m%d_%H%M%S.pgn"),
                                 make_pgn(log, start_fen, result))
                print("棋谱已保存：%s" % path)
                if ask_yes("现在复盘分析吗？(Y/n) ", True):
                    who, side = ask_student()
                    review_moves(start_fen, [x[0] for x in log],
                                 AUTO_REVIEW_SECS, review_name(path),
                                 student=who, student_side=side,
                                 result=result)
            return
        if low in ("help", "h", "?"):
            print(ADVISOR_HELP)
            continue
        if low in ("board", "b"):
            print(board_text(b, flip=(me == BLACK)))
            continue
        if low in SIZE_WORDS or cmd in SIZE_WORDS:
            globals()["SIZE"] = SIZE_WORDS.get(low) or SIZE_WORDS[cmd]
            print(board_text(b, flip=(me == BLACK)))
            continue
        if low in ("eval", "分数"):
            r = eng.search(b, 64, secs)
            cp = r.score if b.side == WHITE else -r.score
            print("  %s（白方视角 %s）%s\n  主变: %s"
                  % (eval_words(r.score, b.side), score_text(cp),
                     bar(cp if abs(cp) < 90000 else
                         (800 if cp > 0 else -800)),
                     pv_san(b, r.pv, 6)))
            continue
        if low in ("moves", "m"):
            legal = b.legal_moves()
            print("  " + "  ".join(sorted(b.san(x, legal) for x in legal)))
            continue
        if low in ("again", "再想", "重想"):
            res = advise(eng, b, secs * 2, use_book=False, level=level)
            if res and b.side == me:
                suggested = res.move
            continue
        if low.startswith("side") or low in ("执黑", "执白") or \
                cmd in ("我执黑", "我执白"):
            arg = cmd[4:].strip() if low.startswith("side") else cmd
            new_me = ask_side("你要执白还是黑？(w/b): ") if not arg else (
                BLACK if ("黑" in arg or arg.lower().startswith("b"))
                else WHITE if ("白" in arg or arg.lower().startswith("w"))
                else None)
            if new_me is None:
                print("  用法: side b（执黑）或 side w（执白）")
                continue
            me = new_me
            pending = True
            print("  好，现在你执%s。" % ("白" if me == WHITE else "黑"))
            continue
        if low.startswith("load") or low in ("games", "棋谱"):
            parts = cmd.split(None, 1)
            path = parts[1].strip().strip('"\'') if len(parts) > 1 else ""
            try:
                files = sorted(f for f in os.listdir(GAMES_DIR)
                               if f.lower().endswith(".pgn"))
            except OSError:
                files = []
            if not path:                       # 不给文件名就列出来选
                if not files:
                    print("  %s/ 里还没有棋谱。" % GAMES_DIR)
                    continue
                for i, f in enumerate(files, 1):
                    print("   %d. %s" % (i, f))
                pick = ask("  载入哪个？(编号，回车取消): ").strip()
                if not pick.isdigit() or not 1 <= int(pick) <= len(files):
                    continue
                path = os.path.join(GAMES_DIR, files[int(pick) - 1])
            else:
                if path.isdigit() and files and 1 <= int(path) <= len(files):
                    path = os.path.join(GAMES_DIR, files[int(path) - 1])
                elif not os.path.exists(path):
                    cand = game_path(path)
                    if os.path.exists(cand):
                        path = cand
                    elif os.path.exists(cand + ".pgn"):
                        path = cand + ".pgn"
                    else:                      # 模糊匹配：只要能唯一对上就行
                        key = os.path.basename(path).lower()
                        hits = [f for f in files if key in f.lower()]
                        if len(hits) == 1:
                            path = os.path.join(GAMES_DIR, hits[0])
            if not os.path.exists(path):
                print("  找不到「%s」。%s/ 里现有：" % (path, GAMES_DIR))
                for i, f in enumerate(files, 1):
                    print("   %d. %s" % (i, f))
                print("  可以直接打 load 1 这样按编号载入。")
                continue
            try:
                raw = open(path, encoding="utf-8", errors="ignore").read()
                head = pgn_headers(raw)
                nb = Board(head.get("FEN", START_FEN))
                nlog, bad = [], None
                for san in pgn_moves(raw):
                    mv = nb.parse_move(san)
                    if mv is None:
                        bad = san
                        break
                    nlog.append((nb.san(mv), mv))
                    nb.make(mv)
            except Exception as exc:
                print("  读不了这个文件：%s" % exc)
                continue
            if bad:
                print("  第 %d 手 '%s' 无法解析，只载入了前面的部分。"
                      % (len(nlog) + 1, bad))
            b, log = nb, nlog
            start_fen = head.get("FEN", START_FEN)
            eng.new_game()
            pending, suggested = True, None
            autosave(log, start_fen)
            print("  已从 %s 载入 %d 手，轮到%s走。"
                  % (os.path.basename(path), len(log),
                     "白方" if b.side == WHITE else "黑方"))
            continue
        if low in ("new", "reset", "重开", "新棋局"):
            b = Board(START_FEN)
            start_fen = START_FEN
            log = []
            eng.new_game()
            pending = True
            print("  已重新开局。")
            continue
        if low in ("cct", "cct"):
            import cct as cct_mod
            print(cct_mod.report(b, LANG))
            continue
        if low == "top" or low.startswith("top "):
            try:
                k = int(low.split()[1])
            except (IndexError, ValueError):
                k = 3
            print("  正在比较各个候选着法…")
            ranked = eng.rank_moves(b, 6, max(secs, 2.0))
            for i, (mv, sc) in enumerate(ranked[:k], 1):
                print("   %d. %-8s %-8s %s"
                      % (i, b.san(mv), score_text(sc), eval_words(sc, b.side)))
            continue
        if low.startswith("level"):
            arg = cmd.split(None, 1)[1] if len(cmd.split(None, 1)) > 1 else ""
            v = ask_number("难度设成几？(0-8，0 = 满血): ", 0, 0, 8) \
                if not arg.strip() else None
            if v is None:
                try:
                    v = float(arg.strip())
                except ValueError:
                    print("  没看懂，用法：level 4（0 = 满血）")
                    continue
            level = int(v) if 1 <= v <= 8 else None
            print("  难度：%s" % ("L%d" % level if level else "满血"))
            pending = True
            continue
        if low.startswith("think"):
            import re
            mm = re.search(r"\d+(?:\.\d+)?", low)
            if mm:
                secs = max(0.2, min(30.0, float(mm.group())))
                print("  思考时间改为 %.1f 秒" % secs)
            else:
                print("  用法: think 5")
            continue
        if low.startswith("undo"):
            try:
                n = int(low.split()[1])
            except (IndexError, ValueError):
                n = 1
            for _ in range(n):
                if b.history:
                    b.unmake()
                    if log:
                        log.pop()
            pending = True
            autosave(log, start_fen)
            print("  已收回 %d 步。" % n)
            continue
        if low == "fen":
            print("  " + b.fen())        # 打印当前局面，可贴给别处或 cct
            continue
        if low.startswith("fen "):
            try:
                nb = Board(cmd[4:].strip())
                nb.legal_moves()
                b, log, pending = nb, [], True
                start_fen = b.fen()
                eng.new_game()
                print("  已载入局面。")
            except Exception:
                print("  这个 FEN 读不出来。")
            continue
        if low.startswith("save"):
            parts = cmd.split(None, 1)
            name = parts[1].strip() if len(parts) > 1 else \
                time.strftime("advice_%Y%m%d_%H%M%S.pgn")
            print("  已保存到 %s" % write_pgn(name, make_pgn(log, start_fen)))
            continue
        if not cmd:                       # 回车 = 采纳刚才建议的那一步
            if b.side != me:
                print("  现在轮对方走，请报出对方的着法。")
                continue
            mv = suggested
            if mv is None or not b.is_legal(mv):
                r = advise(eng, b, secs, verbose=False)
                mv = r.move if r else None
            if mv is None:
                continue
            print("  采纳建议：%s" % b.san(mv))
            log.append((b.san(mv), mv))
            b.make(mv)
            suggested = None
            pending = True
            autosave(log, start_fen)
            continue
        # 一次可以报多步
        applied = 0
        for tok in pgn_moves(cmd):
            m = b.parse_move(tok)
            if m is None:
                print("  '%s' 不是这里的合法着法（board 看棋盘，moves 看可选着法）。"
                      % tok)
                break
            log.append((b.san(m), m))
            b.make(m)
            applied += 1
        if applied:
            pending = True
            suggested = None
            autosave(log, start_fen)


# ---------------------------------------------------------------- 盲区训练
# 界面语言：CHESS_LANG=en 或 `python3 trainer.py blind en` 切英文
LANG = os.environ.get("CHESS_LANG", "zh").lower()[:2]

MSG = {
    "title": ("=== 盲区训练 ===",
              "=== Blind-Spot Drills ==="),
    "intro": ("练的不是算得深，是别漏看。每题都有确定答案，程序当场判卷。",
              "Not about calculating deeper — about not overlooking. "
              "Every drill has a definite answer, graded on the spot."),
    "menu1": ("  1  将军与吃子清单（把 1 层的着法全数出来）",
              "  1  Checks & captures (list every 1-ply forcing move)"),
    "menu2": ("  2  对手的威胁（他下一步想干嘛）",
              "  2  Opponent's threat (what does he want to play?)"),
    "menu3": ("  3  谁在白送（哪些子没保护）",
              "  3  Hanging pieces (what can be won for free?)"),
    "menu4": ("  4  混合", "  4  Mixed"),
    "pick": ("选一项 (回车 = 混合): ", "Pick one (Enter = mixed): "),
    "howmany": ("做几题？(回车 = 8): ", "How many drills? (Enter = 8): "),
    "fresh":  ("  还没练过的局面：%d / %d 个。",
               "  Unseen positions: %d of %d."),
    "roundup": ("  全部 %d 个局面都练过一遍了——从第 2 轮开始，会重新出现。",
                "  All %d positions have been drilled once — starting round 2."),
    "srcdir": ("  从 %s 的 %d 个棋谱里取到 %d 个局面。", 
               "  %d positions from %d game files in %s."),
    "source": ("局面从哪来？(回车 = games/ 里的全部棋谱；"
               "gen = 自动生成；也可以输入文件名或学生名字): ",
               "Positions from? (Enter = auto-generated, or type a PGN file): "),
    "loaded": ("从 %s 取了 %d 个局面。", "Loaded %d positions from %s."),
    "qhead": ("———— 第 %d/%d 题 · %s ————",
              "———— Drill %d/%d · %s ————"),
    "d1name": ("将军与吃子清单", "Checks & captures"),
    "d2name": ("对手的威胁", "Opponent's threat"),
    "d3name": ("谁在白送", "Hanging pieces"),
    "white": ("白方", "White"),
    "black": ("黑方", "Black"),
    "ansprompt": ("  你的答案（fen 看局面串 / skip 跳过）: ",
                  "  Your answer (fen = show FEN / skip): "),
    "d1q": ("  题目：现在轮%s走。把%s此刻能走的**所有**吃子和将军列出来，\n"
            "  一个都不能漏（吃子写成 Nxe5 这样，将军写成 Qh5+ 这样）。\n"
            "  这是最基础的 1 层扫描，实战里绝大多数漏着都死在这一步。",
            "  Task: %s to move. List **every** capture and check %s can play\n"
            "  right now — miss none (write them like Nxe5, Qh5+).\n"
            "  Pure 1-ply scanning; most blunders happen right here."),
    "d1ans": ("  正确答案（共 %d 个）：%s", "  Answer (%d total): %s"),
    "d2q": ("  题目：现在轮%s走。先别想自己走什么——\n"
            "  假设%s这一手白白让掉（什么都不做），换%s再走一步，\n"
            "  %s最想走哪一步？这就是%s此刻必须提防的**威胁**。",
            "  Task: %s to move. Forget your own move for a second —\n"
            "  suppose %s passes (does nothing) and %s gets a free move:\n"
            "  what would %s play? That is the **threat** %s must deal with."),
    "d2ans": ("  他真正的威胁是: %s   (走完之后 %s，比现在多捞约 %.1f 个兵)",
              "  The real threat is %s   (%s after it, worth about %.1f pawns "
              "more than now)"),
    "d2skip": ("  威胁是: %s   (%s)", "  Threat: %s   (%s)"),
    "rescue": ("  注意：%s 上那个子现在正被你攻击。所谓「威胁」其实是把它救走——\n"
               "  也就是说，**你现在可以直接吃掉它**（净赚 %d 分）。",
               "  Note: the piece on %s is attacked by you right now. The "
               "\"threat\" is simply\n  White rescuing it — meaning **you can "
               "just take it** (nets %d)."),
    "d3q": ("  题目：双方的子里，哪些现在是「白送」的——也就是对方吃了它\n"
            "  之后，把兑子过程走完仍然净赚。有保护、吃了会亏的不算。\n"
            "  写格子名，比如 e5 c4；一个都没有就打「无」。",
            "  Task: which pieces on either side are hanging — i.e. after the\n"
            "  full exchange sequence the capture still nets material?\n"
            "  Defended pieces that lose material don't count.\n"
            "  Write squares like e5 c4; type none if there are none."),
    "d3ans": ("  正确答案: %s", "  Answer: %s"),
    "d3item": ("%s（%s的子，值 %d 分）", "%s (%s's piece, worth %d)"),
    "why": ("  为什么：%s", "  Why: %s"),
    "whyline": ("%s 上的%s%s——被 %s 攻击，%s，吃了净赚 %d 分",
                "%s: %s's %s is attacked by %s, %s — the capture nets %d"),
    "undef": ("没有子保护它", "no defender"),
    "defby": ("虽然有 %s 保护，但兑完子仍然亏", "defended by %s but still loses material"),
    "none": ("无", "none"),
    "missed": ("  ✗ 漏掉: %s", "  ✗ Missed: %s"),
    "extra": ("  ✗ 多写: %s", "  ✗ Not hanging: %s"),
    "extra1": ("  ✗ 多写(不合法或不是将军/吃子): %s",
               "  ✗ Wrong (illegal, or not a check/capture): %s"),
    "allright": ("  ✓ 全对", "  ✓ All correct"),
    "right": ("  ✓ 对", "  ✓ Correct"),
    "wrong2": ("  ✗ 没看到", "  ✗ Missed it"),
    "yourmv": ("  你答的 %s 值 %s，比最佳差 %.1f 个兵。"
               "（差距在 0.6 兵以内就算对；这个判断只有 ~1230 的水平，"
               "觉得不服可以自己复核）",
               "  Your %s scores %s — %.1f pawns below best. "
               "(Within 0.6 counts as correct. This judge plays at ~1230, "
               "so treat close calls with suspicion.)"),
    "alsoOK": ("  你答的 %s 值 %s，跟最佳只差 %.1f 个兵，也算对。",
               "  Your %s scores %s, only %.1f pawns off — that counts too."),
    "fallback": ("这一轮改用自动生成的局面。",
                 "Falling back to auto-generated positions for this round."),
    "score": ("\n本次成绩：%d/%d 题全对（%.0f%%）",
              "\nScore: %d/%d drills fully correct (%.0f%%)"),
    "score2": ("  要点细分：%d/%d（%.0f%%）—— 「将军吃子」这类题一题有好几个答案，"
               "所以要点数比题数多",
               "  Items: %d/%d (%.0f%%) — drills like checks & captures have "
               "several answers each, so items outnumber drills"),
    "poor": ("漏看得有点多——这正是实战里丢子的原因，多练几轮。",
             "A lot of oversights — that is exactly how pieces get lost. "
             "Run a few more rounds."),
    "good": ("不错。实战里也照这个顺序过一遍：先将军、再吃子、再看对手威胁。",
             "Well done. Use the same order in a real game: checks, captures, "
             "then the opponent's threat."),
    "nofile": ("  %s/ 里还没有棋谱。", "  No PGN files in %s/ yet."),
}


def T(key, *args):
    zh, en = MSG[key]
    s = en if LANG == "en" else zh
    return s % args if args else s


def _norm_san(s):
    return s.rstrip("+#!? ").replace("0", "O")


def drill_ask(prompt, b, explain):
    """答题输入：顺便支持 fen（看局面串）、help（再解释一遍）、skip（跳过）。"""
    while True:
        ans = ask(prompt)
        low = ans.lower()
        if low in QUIT_WORDS:
            return None
        if low == "fen":
            print("  " + b.fen())
            continue
        if low in ("help", "?", "什么意思", "看不懂"):
            print(explain)
            continue
        if low in ("skip", "pass", "跳过"):
            return "__skip__"
        return ans


def _is_none(ans):
    return ans.strip().lower() in ("无", "没有", "none", "no", "-", "n/a")


def drill_checks_captures(b, eng, secs):
    """把所有将军和吃子数出来——纯 1 层的活儿，但失误大多死在这。"""
    import blindspot as bs
    truth = bs.checks_and_captures(b)
    names = set(_norm_san(b.san(m)) for m, _c, _k in truth)
    who = T("white") if b.side == WHITE else T("black")
    explain = T("d1q", who, who)
    print(explain)
    ans = drill_ask(T("ansprompt"), b, explain)
    if ans is None:
        return None
    if ans == "__skip__":
        print(T("d1ans", len(names), "  ".join(sorted(names)) or T("none")))
        return (0, len(names) or 1)
    given = set()
    for tok in ans.replace(",", " ").split():
        m = b.parse_move(tok)
        given.add(_norm_san(b.san(m)) if m else _norm_san(tok))
    if _is_none(ans):
        given = set()
    missed, extra = names - given, given - names
    print(T("d1ans", len(names), "  ".join(sorted(names)) or T("none")))
    if missed:
        print(T("missed", "  ".join(sorted(missed))))
    if extra:
        print(T("extra1", "  ".join(sorted(extra))))
    if not missed and not extra:
        print(T("allright"))
    return (len(names) - len(missed), len(names))


def _rescue_note(b, mv, bs):
    """「威胁」只是把一个正在挨打的子撤走时，点明这其实是你的白吃机会。"""
    from board import sq_name
    frm = mv & 0xFF
    for sq, _t, val in bs.hanging(b, opp(b.side)):
        if sq == frm:
            print(T("rescue", sq_name(sq), val))
            return True
    return False


def drill_threat(b, eng, secs):
    """对手如果能白走一步，他最想走什么。"""
    import blindspot as bs
    t = bs.threat(eng, b, secs)
    if t is None:
        return None
    mv, sc, _now = t
    me = T("white") if b.side == WHITE else T("black")
    foe = T("black") if b.side == WHITE else T("white")
    explain = T("d2q", me, me, foe, foe, me)
    print(explain)
    ans = drill_ask(T("ansprompt"), b, explain)
    if ans is None:
        return None
    if ans == "__skip__":
        b.make_null()
        san = b.san(mv)
        b.unmake_null()
        print(T("d2skip", san, score_text(sc)))
        _rescue_note(b, mv, bs)
        return (0, 1)
    b.make_null()
    user_san, mine = None, None
    try:
        best_san = b.san(mv)
        user_m = b.parse_move(ans)
        good = False
        if user_m is not None:
            user_san = b.san(user_m)
            if user_m == mv:
                good = True
            else:
                b.make(user_m)
                mine = -eng.search(b, 64, max(secs, 1.0)).score
                b.unmake()
                good = mine >= sc - 60
    finally:
        b.unmake_null()
    gain = sc - t[2]
    print(T("d2ans", best_san, score_text(sc), max(0, gain) / 100.0))
    _rescue_note(b, mv, bs)
    if good:
        print(T("right"))
        if user_san and mine is not None:
            print(T("alsoOK", user_san, score_text(mine), (sc - mine) / 100.0))
        return (1, 1)
    if user_san and mine is not None:
        print(T("yourmv", user_san, score_text(mine), (sc - mine) / 100.0))
    print(T("wrong2"))
    return (0, 1)


def drill_hanging(b, eng, secs):
    """哪些子现在是白送的（双方都算）。"""
    import blindspot as bs
    from board import sq_name
    truth = {}
    for color in (WHITE, BLACK):
        for s, _t, v in bs.hanging(b, color):
            truth[sq_name(s)] = (color, v)
    explain = T("d3q")
    print(explain)
    ans = drill_ask(T("ansprompt"), b, explain)
    if ans is None:
        return None
    names = set(truth)

    def answer_text():
        if not names:
            return T("none")
        return "  ".join(T("d3item", k,
                           T("white") if truth[k][0] == WHITE else T("black"),
                           truth[k][1]) for k in sorted(names))

    def why_lines():
        from board import name_sq, PIECE_LETTER
        out = []
        for k in sorted(names):
            info = bs.explain_square(b, name_sq(k))
            if not info:
                continue
            owner = T("white") if info["owner"] == WHITE else T("black")
            att = ", ".join(info["attackers"]) or "?"
            dfd = (T("defby", ", ".join(info["defenders"]))
                   if info["defenders"] else T("undef"))
            out.append(T("whyline", k, owner, info["piece"], att, dfd,
                         truth[k][1]))
        return out

    if ans == "__skip__":
        print(T("d3ans", answer_text()))
        for ln in why_lines():
            print(T("why", ln))
        return (0, max(1, len(names)))
    given = set(x.lower() for x in ans.replace(",", " ").split())
    if _is_none(ans):
        given = set()
    missed, extra = names - given, given - names
    print(T("d3ans", answer_text()))
    for ln in why_lines():
        print(T("why", ln))
    if missed:
        print(T("missed", "  ".join(sorted(missed))))
    if extra:
        print(T("extra", "  ".join(sorted(extra))))
    if not missed and not extra:
        print(T("allright"))
    return (len(names) - len(missed), max(1, len(names)))


def _threat_worth_asking(b, eng, bs):
    """只挑「真有威胁」的局面：不管的话至少要亏 1.5 个兵，否则这题没意义。"""
    t = bs.threat(eng, b, 0.35)
    if t is None:
        return False
    _mv, sc, now_from_foe = t
    return (sc - now_from_foe) >= 150


DRILLS = [
    ("d1name", drill_checks_captures,
     lambda b, eng, bs: 3 <= len(bs.checks_and_captures(b)) <= 12),
    ("d2name", drill_threat, _threat_worth_asking),
    ("d3name", drill_hanging,
     lambda b, eng, bs: 1 <= len(bs.hanging(b, WHITE)) + len(bs.hanging(b, BLACK)) <= 4),
]


def blindspot_mode(lang=None):
    import blindspot as bs
    if lang:
        globals()["LANG"] = lang
    print("\n" + T("title"))
    print(T("intro"))
    for k in ("menu1", "menu2", "menu3", "menu4"):
        print(T(k))
    c = ask(T("pick")).strip()
    pick = {"1": [0], "2": [1], "3": [2]}.get(c, [0, 1, 2])
    n = ask(T("howmany"))
    try:
        n = max(1, int(n))
    except ValueError:
        n = 8
    src = ask(T("source")).strip()

    eng = make_engine()
    rnd = random.Random()
    pool = []
    why = []
    per_file = []
    pool_key = None
    seen_now = set()
    if src.lower() in ("gen", "random", "随机", "自动", "自动生成"):
        pass                                   # 明确要求自动生成
    elif src and os.path.exists(src) and os.path.isfile(src):
        pool = bs.positions_from_pgn(src, rnd, want=n * 3, why=why)
        print(T("loaded", len(pool), src) if LANG == "en"
              else T("loaded", src, len(pool)))
    else:
        # 回车 = 整个 games/；输入别的字 = 按文件名筛（比如学生名字）
        seen_key = pool_key = (src or "all").lower()
        seen = load_seen(seen_key)
        pool, per_file, n_fresh = bs.positions_from_dir(
            GAMES_DIR, rnd, want=n * 5, why=why, match=(src or None),
            seen=seen)
        if pool:
            print(T("srcdir", len(pool), len(per_file), GAMES_DIR)
                  if LANG == "en" else T("srcdir", GAMES_DIR,
                                         len(per_file), len(pool)))
            for f, c in per_file:
                print("    %-32s %d" % (f, c))
            total_pos = sum(c for _f, c in per_file)
            if n_fresh:
                print(T("fresh", n_fresh, total_pos))
            else:
                print(T("roundup", total_pos))
                seen = set()
                save_seen(seen_key, seen)
    if not pool:
        for msg in why:
            print("  ！ %s" % msg)
        print("  ！ %s" % (T("fallback")))

    got = total = done = tries = 0
    q_ok = q_n = 0

    def report():
        if not q_n:
            return
        print(T("score", q_ok, q_n, 100.0 * q_ok / q_n))
        if total != q_n:
            print(T("score2", got, total, 100.0 * got / total))

    secs = 0.5
    while done < n and tries < n * 12:
        tries += 1
        which = rnd.choice(pick)
        namekey, fn, cond = DRILLS[which]
        from_pool = bool(pool)
        b = pool.pop() if pool else bs.random_position(eng, rnd, 12, 44, 4)
        if b.outcome() or not b.legal_moves():
            continue
        if cond and not cond(b, eng, bs):
            continue
        done += 1
        if pool_key and from_pool:      # 自动生成的局面不记进「练过」
            seen_now.add(b.fen())
        print("\n" + T("qhead", done, n, T(namekey)))
        print(board_text(b, flip=(b.side == BLACK)))
        res = fn(b, eng, secs)
        if res is None:
            done -= 1
            if fn is drill_threat:
                continue
            if pool_key and seen_now:
                save_seen(pool_key, load_seen(pool_key) | seen_now)
            report()
            return
        got += res[0]
        total += res[1]
        q_n += 1
        if res[0] >= res[1]:
            q_ok += 1
    if pool_key and seen_now:
        save_seen(pool_key, load_seen(pool_key) | seen_now)
    if q_n:
        report()
        print(T("poor") if got < total * 0.7 else T("good"))


# ------------------------------------------------------------------ 战术题
def puzzle_mode(level=5):
    items = list(puzzle_db.TACTICS)
    random.shuffle(items)
    eng = make_engine()
    solved = 0
    for idx, (fen, theme, hint, kind) in enumerate(items, 1):
        b = Board(fen)
        me = b.side
        print("\n=== 第 %d/%d 题 · %s ===" % (idx, len(items), theme))
        print("轮到%s走，找出最强的一步。" % ("白方" if me == WHITE else "黑方"))
        print(board_text(b, flip=(me == BLACK)))
        eng.new_game()
        ref = eng.search(b, 64, 1.5)
        while True:
            cmd = ask("你的答案（或 hint / solution / skip / quit）: ")
            low = cmd.lower()
            if low in ("quit", "q"):
                print("\n本次做对 %d 题。" % solved)
                return
            if low == "skip":
                print("答案：%s" % pv_san(b, ref.pv, 5))
                break
            if low == "hint":
                print("  " + hint)
                continue
            if low in ("solution", "答案"):
                print("  答案：%s  (%s)" % (pv_san(b, ref.pv, 5),
                                          score_text(ref.score)))
                break
            m = b.parse_move(cmd)
            if m is None:
                print("  不是合法着法。")
                continue
            b.make(m)
            if b.legal_moves():
                r2 = eng.search(b, 64, 1.5)
                mine = -r2.score
            else:
                mine = 100000 if b.in_check() else 0
            b.unmake()
            if mine >= ref.score - 40:
                print("  正确！✓  %s   后续: %s"
                      % (score_text(ref.score), pv_san(b, ref.pv, 5)))
                solved += 1
                break
            print("  不对（这步之后只有 %s，最佳能到 %s）。再试试，或输入 hint。"
                  % (score_text(mine), score_text(ref.score)))
    print("\n全部做完，做对 %d/%d 题。" % (solved, len(items)))


# ------------------------------------------------------------------ 残局训练
def drill_mode(level=5):
    print("\n可选残局：")
    for i, (_fen, name, goal, side) in enumerate(puzzle_db.DRILLS, 1):
        print("  %2d. %-24s 目标:%s  你执%s"
              % (i, name, "取胜" if goal == "win" else "守和",
                 "白" if side == "w" else "黑"))
    c = ask("选一个 (回车随机): ")
    try:
        item = puzzle_db.DRILLS[int(c) - 1]
    except (ValueError, IndexError):
        item = random.choice(puzzle_db.DRILLS)
    fen, name, goal, side = item
    s = Session(fen, WHITE if side == "w" else BLACK, level, True, goal, name)
    s.run()


def cct_mode(arg=""):
    """CCT 扫描练习：给个局面，先自己口报将军/吃子/威胁，再看答案。

    用法：
      python3 trainer.py cct                     从起始局面，之后可 fen/着法 切换
      python3 trainer.py cct "<FEN>"             直接看某个局面
    循环里：报着法推进局面；打 cct 看答案；fen <FEN> 换局面；quit 退出。
    """
    import cct as cct_mod
    HELP = ("\n  这个模式帮你练「落子前先扫一遍」。用法：\n"
            "    回车 或 cct   ——  看当前局面的 将军/吃子/威胁（答案）\n"
            "    fen <FEN>     ——  换一个局面来练（把 FEN 贴在 fen 后面）\n"
            "    e4 / Nf3      ——  报一步着法，推进局面\n"
            "    board         ——  重看棋盘\n"
            "    quit          ——  退出\n"
            "  练法：先自己心里报「我有哪些将军、吃子、威胁」，再按回车对答案。\n")
    b = Board(arg.strip()) if arg.strip() else Board()
    print("CCT 扫描练习。先自己口报「将军/吃子/威胁」，再【按回车】看答案。")
    print("换局面用 fen <FEN>；打 help 看全部用法；quit 退出。\n")
    show(b, b.side)
    print("（先自己报，然后直接按回车看答案。）")
    while True:
        line = ask("报完按回车看答案（或 fen <FEN> / 着法 / help / quit）: ").strip()
        low = line.lower()
        if low in QUIT_WORDS:
            return
        if low in ("help", "h", "?", "帮助"):
            print(HELP); continue
        if low == "cct" or low == "":
            print(cct_mod.report(b, LANG)); print()
            continue
        if low == "fen":                    # 光打 fen = 显示当前 FEN
            print("  当前 FEN：%s" % b.fen())
            print("  （想换局面：fen 后面加上 FEN 串，例如 fen %s）" % b.fen())
            continue
        if low.startswith("fen "):
            try:
                b = Board(line[4:].strip()); show(b, b.side)
                print("（先自己报，再按回车看答案。）")
            except Exception:
                print("  这个 FEN 读不了，检查一下有没有贴全。")
            continue
        if low in ("board", "b"):
            show(b, b.side); continue
        m = b.parse_move(line)
        if m is None:
            print("  没看懂「%s」。直接按回车看答案；换局面用 fen <FEN>；"
                  "退出打 quit；不清楚打 help。" % line)
            continue
        b.make(m)
        show(b, b.side)


# ---------------------------------------------------------------------- 菜单
def choose_level(default=5):
    print("\n难度：")
    for k in sorted(LEVELS):
        print("  %2d  %s" % (k, LEVEL_ELO[k]))
    v = ask_number("选难度 1-10 (回车 = %d): " % default, default, 1, 10)
    return default if v is None else int(v)


def play_mode():
    level = choose_level()
    human = ask_side("你执白还是黑？(w/b/r 随机, 回车 = 白): ")
    if human is None:
        return
    coach = ask_yes("开启实时教练点评？(Y/n): ", True)
    if coach is None:
        return
    Session(START_FEN, human, level, coach).run()


MENU = """
================ 国际象棋训练器 ================
  1  对弈（可提示、悔棋、实时点评）
  2  跟棋助手（你报双方着法，我告诉你走哪一步）
  3  盲区训练（练「别漏看」，1000-1600 最该练的）
  4  战术题
  5  残局训练
  6  复盘分析（PGN / 着法）
  7  自检（perft + 题库 + 适配层）
  q  退出
"""


def main():
    args = sys.argv[1:]
    if args:
        cmd = args[0].lower()
        if cmd.startswith("play"):
            return play_mode()
        if cmd.startswith("adv") or cmd.startswith("coach") or \
                cmd.startswith("assist"):
            return advisor_mode()
        if cmd.startswith("blind") or cmd.startswith("盲"):
            lang = args[1].lower()[:2] if len(args) > 1 else None
            return blindspot_mode(lang)
        if cmd.startswith("puz"):
            return puzzle_mode()
        if cmd.startswith("dr") or cmd.startswith("end"):
            return drill_mode()
        if cmd.startswith("rev"):
            if len(args) > 2:                 # 一次给了好几个棋谱
                return review_batch(args[1:])
            return review_mode(args[1] if len(args) > 1 else None)
        if cmd == "cct":
            return cct_mode(" ".join(args[1:]))
    while True:
        print(MENU)
        c = ask("选择: ").lower()
        if c in ("q", "quit", "exit"):
            return
        if c == "1":
            play_mode()
        elif c == "2":
            advisor_mode()
        elif c == "3":
            blindspot_mode()
        elif c == "4":
            puzzle_mode()
        elif c == "5":
            drill_mode()
        elif c == "6":
            review_mode()
        elif c == "7":
            import test_perft
            import test_book
            import test_uci
            import test_blindspot
            test_perft.main(250000)
            test_book.main(0.4)
            test_uci.main()
            test_blindspot.main()
            puzzle_db.validate(2.0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # 退出码 130 = 被 Ctrl-C 中断。shell 循环里可以用 `|| break` 停掉整批。
        print("\n再见！")
        sys.exit(130)
