# -*- coding: utf-8 -*-
"""盲区训练的练习日志——每练一次记一行，家长/教练每天能查坚持情况和**错在哪**。

按三类分别记对错：
  cc     = 将军与吃子清单（把 1 层的着法数全）
  threat = 对手的威胁（他下一步想干嘛）
  hang   = 谁在白送（哪些子没保护）

查看时按天汇总，给出连续天数、最近一周的量，以及**哪一类最弱**。

    python3 blind_log.py          # 查看日志
"""

import csv
import os
import time

DIR = os.path.join(os.environ.get("CHESS_GAMES", "games"), "students")
PATH = os.path.join(DIR, "_blind_log.csv")
FIELDS = ["date", "time",
          "cc_ok", "cc_n", "threat_ok", "threat_n", "hang_ok", "hang_n"]

# blind 里类别索引 → 日志字段前缀 / 中文名
CATS = [(0, "cc", "将军吃子清单"),
        (1, "threat", "对手的威胁"),
        (2, "hang", "谁在白送")]


def record(cat_stats):
    """cat_stats = {0:[对,共], 1:[对,共], 2:[对,共]}。一题没做就不记。"""
    total_n = sum(v[1] for v in cat_stats.values())
    if not total_n:
        return None
    try:
        os.makedirs(DIR, exist_ok=True)
    except OSError:
        return None
    new = not os.path.exists(PATH)
    row = {"date": time.strftime("%Y-%m-%d"), "time": time.strftime("%H:%M")}
    for idx, key, _name in CATS:
        ok, n = cat_stats.get(idx, [0, 0])
        row[key + "_ok"] = ok
        row[key + "_n"] = n
    with open(PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)
    return PATH


def _load():
    if not os.path.exists(PATH):
        return []
    with open(PATH, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f)]


def _i(r, k):
    try:
        return int(float(r.get(k) or 0))
    except (ValueError, TypeError):
        return 0


def _streak(days):
    import datetime
    d = datetime.date.today()
    n = 0
    while d.strftime("%Y-%m-%d") in days:
        n += 1
        d -= datetime.timedelta(days=1)
    return n


def report():
    rows = _load()
    if not rows:
        return "还没有盲区训练记录。练一次（python3 trainer.py blind）就会开始记。"
    import datetime
    byday = {}
    cat_tot = {key: [0, 0] for _i, key, _n in CATS}      # 全程按类别累计
    for r in rows:
        qn = sum(_i(r, key + "_n") for _i2, key, _n in CATS)
        qok = sum(_i(r, key + "_ok") for _i2, key, _n in CATS)
        a = byday.setdefault(r.get("date", ""), {"q": 0, "ok": 0, "n": 0})
        a["q"] += qn
        a["ok"] += qok
        a["n"] += 1
        for _i2, key, _n in CATS:
            cat_tot[key][0] += _i(r, key + "_ok")
            cat_tot[key][1] += _i(r, key + "_n")

    out = ["", "———— 盲区训练日志 ————",
           "%-12s %-5s %-5s %-5s %s" % ("日期", "次数", "题数", "答对", "正确率")]
    for d in sorted(byday)[-14:]:
        a = byday[d]
        pct = (100.0 * a["ok"] / a["q"]) if a["q"] else 0
        out.append("%-12s %-5d %-5d %-5d %.0f%%"
                   % (d, a["n"], a["q"], a["ok"], pct))

    streak = _streak(set(byday))
    last7 = [d for d in byday
             if (datetime.date.today()
                 - datetime.date(*map(int, d.split("-")))).days < 7]
    q7 = sum(byday[d]["q"] for d in last7)
    ok7 = sum(byday[d]["ok"] for d in last7)
    out.append("")
    out.append("连续练习 %d 天%s" % (streak, "，不错 ↑" if streak >= 3 else ""))
    out.append("最近 7 天：练了 %d 天，共 %d 题，答对 %d（%.0f%%）"
               % (len(last7), q7, ok7, (100.0 * ok7 / q7) if q7 else 0))

    # 错在哪：按类别的正确率
    out.append("")
    out.append("———— 各类正确率（错在哪）————")
    worst = None
    for _idx, key, name in CATS:
        ok, n = cat_tot[key]
        if not n:
            out.append("  %-14s 还没练过" % name)
            continue
        pct = 100.0 * ok / n
        bar = "█" * int(round(pct / 10))
        out.append("  %-14s %3d/%-3d  %3.0f%%  %s" % (name, ok, n, pct, bar))
        if worst is None or pct < worst[1]:
            worst = (name, pct)
    if worst:
        out.append("")
        out.append("最弱的一类是「%s」（%.0f%%）——这一类多练。" % worst)

    today = datetime.date.today().strftime("%Y-%m-%d")
    if today not in byday:
        out.append("")
        out.append("※ 今天还没练。")
    return "\n".join(out)


if __name__ == "__main__":
    print(report())
