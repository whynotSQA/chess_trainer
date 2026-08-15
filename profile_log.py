# -*- coding: utf-8 -*-
"""学生档案——把每盘复盘的结果累积起来，看趋势。

为什么要这个：**等级分是滞后指标**。一个学生的错误率已经在降了，等级分可能
两个月都不动，中间很容易误判成「白教了」。

这里记的主指标是「每 N 步崩一次严重失误」——它比等级分敏感得多，也比
「平均每步损失」稳定（后者依赖用哪个引擎、想多久，跨报告不可比）。

一个学生一个 CSV，存在 games/students/ 下，纯文本，随时可以自己看。

`python3 profile_log.py <名字>` 直接出报告。
"""

import csv
import os
import time

DIR = os.path.join(os.environ.get("CHESS_GAMES", "games"), "students")

FIELDS = ["date", "color", "result", "moves", "acpl",
          "inaccuracies", "mistakes", "blunders", "moves_per_blunder",
          "hang", "defender", "line", "miss", "grab", "note"]

TAG_NAME = {"hang": "白送子", "defender": "走开的子原来在守它",
            "line": "挪开挡线的子", "miss": "漏掉一步白吃", "grab": "贪兵"}


def path_for(student):
    safe = "".join(c for c in student if c not in '/\\:*?"<>|').strip()
    return os.path.join(DIR, (safe or "unnamed") + ".csv")


def list_students():
    """现有档案的名字。"""
    try:
        return sorted(f[:-4] for f in os.listdir(DIR) if f.endswith(".csv"))
    except OSError:
        return []


def similar(name):
    """名字打错时找回来：不区分大小写、互为前缀或包含，且只匹配到一个才算。

    「jerem」→「Jeremy」。匹配到多个就返回 None，不瞎猜。
    """
    if not name:
        return None
    low = name.strip().lower()
    names = list_students()
    for n in names:
        if n.lower() == low:
            return n                      # 本来就对
    hits = [n for n in names
            if n.lower().startswith(low) or low.startswith(n.lower())
            or low in n.lower() or n.lower() in low]
    return hits[0] if len(hits) == 1 else None


def record(student, row):
    """追加一盘。row 是 dict，缺的字段留空。"""
    p = path_for(student)
    try:
        os.makedirs(DIR, exist_ok=True)
    except OSError:
        return None
    new = not os.path.exists(p)
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        row = dict(row)
        row.setdefault("date", time.strftime("%Y-%m-%d"))
        w.writerow(row)
    return os.path.abspath(p)


def load(student):
    p = path_for(student)
    if not os.path.exists(p):
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f)]


def _f(row, key, default=0.0):
    try:
        return float(row.get(key) or default)
    except ValueError:
        return default


def _i(row, key, default=0):
    try:
        return int(float(row.get(key) or default))
    except ValueError:
        return default


def report(student, lang="zh"):
    """返回一段可以直接打印的文字。没有数据就返回 ''。"""
    rows = load(student)
    if not rows:
        return ""
    out = ["", "———— %s 的档案（%d 盘）————" % (student, len(rows)),
           "%-11s %-3s %-5s %-7s %-8s %s"
           % ("日期", "执", "步数", "严重失误", "每N步崩", "结果")]
    for r in rows:
        out.append("%-11s %-3s %-5s %-8s %-9s %s"
                   % (r.get("date", ""), r.get("color", ""),
                      r.get("moves", ""), r.get("blunders", ""),
                      r.get("moves_per_blunder", "—"), r.get("result", "")))

    # 主指标：每 N 步崩一次，按最近 3 盘 vs 之前 3 盘
    def rate(sub):
        mv = sum(_i(r, "moves") for r in sub)
        bl = sum(_i(r, "blunders") for r in sub)
        return (mv / float(bl)) if bl else None

    all_rate = rate(rows)
    if all_rate:
        out.append("")
        out.append("全部 %d 盘：每 %.1f 步一次严重失误"
                   % (len(rows), all_rate))
    if len(rows) >= 4:
        recent, older = rows[-3:], rows[:-3][-3:]
        rn, ro = rate(recent), rate(older)
        if rn and ro:
            arrow = "在变好 ↑" if rn > ro else ("在变差 ↓" if rn < ro else "持平")
            out.append("最近 3 盘：每 %.1f 步一次   之前 3 盘：每 %.1f 步一次   %s"
                       % (rn, ro, arrow))
            out.append("（这个数字越大越好——越久才崩一次。）")

    # 失误类型分布
    tally = {}
    for r in rows:
        for t in TAG_NAME:
            n = _i(r, t)
            if n:
                tally[t] = tally.get(t, 0) + n
    if tally:
        total = sum(tally.values())
        out.append("")
        out.append("失误类型（共打了 %d 个标签，一步棋可能同时属于多类）：" % total)
        for t, n in sorted(tally.items(), key=lambda kv: -kv[1]):
            bar = "█" * int(round(20.0 * n / total))
            out.append("  %-20s %3d  %s" % (TAG_NAME[t], n, bar))
        top = max(tally, key=lambda k: tally[k])
        out.append("")
        out.append("最集中的一类是「%s」，占 %.0f%%——先练这个。"
                   % (TAG_NAME[top], 100.0 * tally[top] / total))
    return "\n".join(out)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        try:
            names = [f[:-4] for f in os.listdir(DIR) if f.endswith(".csv")]
        except OSError:
            names = []
        print("用法: python3 profile_log.py <学生名字>")
        print("现有档案:", "、".join(names) if names else "（还没有）")
    else:
        r = report(sys.argv[1])
        print(r if r else "没有 %s 的记录。" % sys.argv[1])
