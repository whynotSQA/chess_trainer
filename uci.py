# -*- coding: utf-8 -*-
"""UCI 适配层：把 Stockfish（或任何 UCI 引擎）接进这个训练器。

用法::

    from uci import UciEngine, find_stockfish
    eng = UciEngine(find_stockfish())          # 不传路径就自动找
    r = eng.search(board, movetime=1.0)        # 和 engine.Engine.search 同签名
    print(board.san(r.move), r.score)
    eng.close()

接口刻意做成和 `engine.Engine` 一样（search / rank_moves / new_game / rnd），
所以哪里用 Engine 就能直接换成它。
"""

import os
import random
import shutil
import subprocess
import sys
import threading

from board import Board, START_FEN
from engine import MATE, SearchResult, mate_in           # noqa: F401

CANDIDATES = ("stockfish", "stockfish-x86-64", "Stockfish")
COMMON_PATHS = (
    "/opt/homebrew/bin/stockfish",          # Apple Silicon 的 Homebrew
    "/usr/local/bin/stockfish",             # Intel Mac 的 Homebrew
    "/usr/games/stockfish",
    "/usr/bin/stockfish",
)


def find_stockfish(explicit=None):
    """按 参数 → 环境变量 CHESS_SF → PATH → 常见安装位置 的顺序找。"""
    for cand in (explicit, os.environ.get("CHESS_SF")):
        if cand and os.path.exists(cand):
            return cand
    for name in CANDIDATES:
        p = shutil.which(name)
        if p:
            return p
    for p in COMMON_PATHS:
        if os.path.exists(p):
            return p
    return None


class UciError(RuntimeError):
    pass


class UciEngine(object):
    """一个 UCI 子进程的封装。"""

    def __init__(self, path=None, elo=None, threads=1, hash_mb=64,
                 skill=None, debug=False, seed=None):
        path = find_stockfish(path)
        if not path:
            raise UciError("没找到 Stockfish，装一个（brew install stockfish）"
                           "或用环境变量 CHESS_SF 指定路径。")
        self.path = path
        self.debug = debug
        self.rnd = random.Random(seed)
        self.nodes = 0
        self._lock = threading.Lock()
        self.proc = subprocess.Popen(
            [path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, universal_newlines=True, bufsize=1)
        self.name = "UCI engine"
        self.options = {}
        self._handshake()
        if threads:
            self.setoption("Threads", threads)
        if hash_mb:
            self.setoption("Hash", hash_mb)
        if skill is not None:
            self.setoption("Skill Level", skill)
        if elo is not None:
            self.set_elo(elo)

    # ------------------------------------------------------------ 底层通信
    def _send(self, line):
        if self.debug:
            sys.stderr.write("> %s\n" % line)
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()

    def _readline(self):
        line = self.proc.stdout.readline()
        if not line:
            raise UciError("引擎进程意外退出了")
        if self.debug:
            sys.stderr.write("< %s" % line)
        return line.strip()

    def _handshake(self):
        self._send("uci")
        while True:
            line = self._readline()
            if line.startswith("id name"):
                self.name = line[8:].strip()
            elif line.startswith("option name"):
                nm = line[12:].split(" type ")[0].strip()
                self.options[nm] = line
            elif line == "uciok":
                break
        self.isready()

    def isready(self):
        self._send("isready")
        while self._readline() != "readyok":
            pass

    def setoption(self, name, value):
        if isinstance(value, bool):
            value = "true" if value else "false"
        self._send("setoption name %s value %s" % (name, value))

    def set_elo(self, elo):
        """把引擎限制到指定等级分（Stockfish 支持范围约 1320-3190）。"""
        if "UCI_LimitStrength" not in self.options:
            raise UciError("这个引擎不支持 UCI_LimitStrength，没法限强度")
        self.setoption("UCI_LimitStrength", True)
        self.setoption("UCI_Elo", int(elo))
        self.elo = int(elo)
        self.isready()

    def new_game(self):
        self._send("ucinewgame")
        self.isready()

    def close(self):
        try:
            self._send("quit")
            self.proc.wait(timeout=3)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass

    # -------------------------------------------------------------- 搜索
    def _position(self, board):
        self._send("position fen %s" % board.fen())

    @staticmethod
    def _score_to_cp(kind, value):
        """UCI 的分数换算成本项目内部的表示（都是「该走方视角」）。"""
        if kind == "cp":
            return int(value)
        n = int(value)                      # mate in n（负数 = 被将杀）
        if n > 0:
            return MATE - (2 * n - 1)
        if n < 0:
            return -(MATE - (2 * (-n) - 1))
        return MATE                          # mate 0 = 已经被将杀

    def _parse_info(self, line, board, sink):
        toks = line.split()
        if toks[0] != "info" or "pv" not in toks:
            return
        # lowerbound / upperbound 是搜索窗口失败时的**边界值**，不是评估。
        # 引擎在评分剧烈变化时经常发这种行（比如一个兵变成不可阻挡的通路兵），
        # 当成评分用会打印出 -70.45 这种荒唐数字。UCI 规范要求忽略它们。
        if "lowerbound" in toks or "upperbound" in toks:
            return
        info = {"multipv": 1}
        i = 1
        while i < len(toks):
            t = toks[i]
            if t in ("depth", "seldepth", "multipv", "nodes", "nps", "time"):
                info[t] = int(toks[i + 1])
                i += 2
            elif t == "score":
                info["score"] = self._score_to_cp(toks[i + 1], toks[i + 2])
                i += 3
            elif t == "pv":
                info["pv"] = toks[i + 1:]
                i = len(toks)
            else:
                i += 1
        if "pv" not in info or "score" not in info:
            return
        moves, made = [], 0
        for u in info["pv"]:
            m = board.parse_move(u)
            if m is None:
                break
            moves.append(m)
            board.make(m)
            made += 1
        for _ in range(made):
            board.unmake()
        if not moves:
            return
        info["moves"] = moves
        sink[info["multipv"]] = info

    def _go(self, board, depth=None, movetime=None, multipv=1):
        with self._lock:
            if multipv != 1:
                self.setoption("MultiPV", multipv)
            self._position(board)
            cmd = "go"
            if depth and depth < 64:
                cmd += " depth %d" % depth
            if movetime:
                cmd += " movetime %d" % max(1, int(movetime * 1000))
            if not depth and not movetime:
                cmd += " movetime 1000"
            self._send(cmd)
            sink = {}
            best_uci = None
            while True:
                line = self._readline()
                if line.startswith("info"):
                    try:
                        self._parse_info(line, board, sink)
                    except Exception:
                        pass
                elif line.startswith("bestmove"):
                    parts = line.split()
                    best_uci = parts[1] if len(parts) > 1 else None
                    break
            if multipv != 1:
                self.setoption("MultiPV", 1)
            return sink, best_uci

    def search(self, board, depth=64, movetime=2.0, on_iter=None):
        base = board.fen()
        sink, best_uci = self._go(board, depth, movetime)
        assert board.fen() == base, "UCI 适配层弄坏了棋盘状态"
        info = sink.get(1)
        move = board.parse_move(best_uci) if best_uci and best_uci != "(none)" \
            else None
        if info is None:
            if move is None:
                return SearchResult()
            return SearchResult(move, 0, 0, 0, [move], movetime or 0.0)
        if move is None:
            move = info["moves"][0]
        self.nodes = info.get("nodes", 0)
        r = SearchResult(move, info["score"], info.get("depth", 0),
                         info.get("nodes", 0), info["moves"],
                         info.get("time", 0) / 1000.0,
                         mate_in(info["score"]))
        if on_iter:
            on_iter(r)
        return r

    MULTIPV = True                      # 支持一次搜索拿多条主变

    def rank_lines(self, board, depth=64, movetime=2.0, k=3):
        """返回 [(主变着法表, 分数)]，按好坏排序。一次搜索拿到 k 条线。"""
        base = board.fen()
        n = min(k, max(1, len(board.legal_moves())))
        sink, _best = self._go(board, depth, movetime, multipv=n)
        assert board.fen() == base, "UCI 适配层弄坏了棋盘状态"
        out = [(v["moves"], v["score"], v.get("depth", 0))
               for _i, v in sorted(sink.items()) if v.get("moves")]
        out.sort(key=lambda x: -x[1])
        return out

    def rank_moves(self, board, depth=8, movetime=2.0, k=8):
        """返回 [(着法, 分数)]，按好坏排序（用引擎自带的 MultiPV）。"""
        n = min(k, max(1, len(board.legal_moves())))
        sink, _ = self._go(board, depth, movetime, multipv=n)
        out = [(v["moves"][0], v["score"]) for _i, v in sorted(sink.items())]
        out.sort(key=lambda x: x[1], reverse=True)
        return out


def describe(path=None):
    """返回一行说明，找不到引擎就返回 None。"""
    p = find_stockfish(path)
    if not p:
        return None
    try:
        e = UciEngine(p)
        name = e.name
        limit = "支持限强度(UCI_Elo)" if "UCI_LimitStrength" in e.options \
            else "不支持限强度"
        e.close()
        return "%s  [%s]  %s" % (name, limit, p)
    except Exception as exc:
        return "找到 %s 但启动失败：%s" % (p, exc)


if __name__ == "__main__":
    d = describe(sys.argv[1] if len(sys.argv) > 1 else None)
    if not d:
        print("没找到 Stockfish。装一个：brew install stockfish")
        sys.exit(1)
    print("找到引擎：%s" % d)
    e = UciEngine()
    b = Board(START_FEN)
    r = e.search(b, 64, 1.0)
    print("开局第一步它推荐 %s（深度 %d，评估 %+d）"
          % (b.san(r.move), r.depth, r.score))
    e.close()
