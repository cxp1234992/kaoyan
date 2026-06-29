from __future__ import annotations

import re
import sys
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib-cache"))
os.environ.setdefault("MPLBACKEND", "Agg")
LOCAL_LIBS = ROOT / ".python-libs"
if LOCAL_LIBS.exists():
    sys.path.insert(0, str(LOCAL_LIBS))

import matplotlib.pyplot as plt
import pandas as pd

SYSTEM_DIR = ROOT / "我的考研系统"
DAILY_DIR = SYSTEM_DIR / "每日记录"
OUTPUT_DIR = SYSTEM_DIR / "可视化"


@dataclass
class TimeEntry:
    date: str
    subject: str
    hours: float
    content: str


@dataclass
class AccuracyEntry:
    date: str
    subject: str
    content: str
    correct: int
    total: int
    reason: str


def section(content: str, title: str) -> str:
    pattern = rf"## {re.escape(title)}\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, content, re.S)
    return match.group(1).strip() if match else ""


def parse_markdown_table(text: str) -> list[dict[str, str]]:
    rows = []
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    if len(lines) < 3:
        return rows

    headers = [cell.strip() for cell in lines[0].strip("|").split("|")]
    for line in lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        row = dict(zip(headers, cells))
        if any(value for value in row.values()):
            rows.append(row)
    return rows


def parse_hours(value: str) -> float:
    value = str(value).strip().lower().replace("小时", "h")
    if not value:
        return 0.0
    match = re.search(r"(\d+(?:\.\d+)?)", value)
    return float(match.group(1)) if match else 0.0


def parse_int(value: str) -> int | None:
    value = str(value).strip()
    if not value:
        return None
    match = re.search(r"\d+", value)
    return int(match.group(0)) if match else None


def collect_entries() -> tuple[list[TimeEntry], list[AccuracyEntry]]:
    time_entries: list[TimeEntry] = []
    accuracy_entries: list[AccuracyEntry] = []

    for path in sorted(DAILY_DIR.glob("*.md")):
        date = path.stem
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            continue

        content = path.read_text(encoding="utf-8")

        for row in parse_markdown_table(section(content, "学习时长")):
            subject = row.get("科目", "").strip()
            hours = parse_hours(row.get("时长", ""))
            detail = row.get("内容", "").strip()
            if subject and hours > 0:
                time_entries.append(TimeEntry(date, subject, hours, detail))

        for row in parse_markdown_table(section(content, "正确率")):
            subject = row.get("科目", "").strip()
            detail = row.get("内容", "").strip()
            correct = parse_int(row.get("做对", ""))
            total = parse_int(row.get("总数", ""))
            reason = row.get("错因", "").strip()
            if subject and correct is not None and total and total > 0:
                accuracy_entries.append(AccuracyEntry(date, subject, detail, correct, total, reason))

    return time_entries, accuracy_entries


def save_tables(time_entries: list[TimeEntry], accuracy_entries: list[AccuracyEntry]) -> tuple[pd.DataFrame, pd.DataFrame]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    time_df = pd.DataFrame([entry.__dict__ for entry in time_entries])
    acc_df = pd.DataFrame([entry.__dict__ for entry in accuracy_entries])

    if not time_df.empty:
        time_df.to_csv(OUTPUT_DIR / "学习时长汇总.csv", index=False, encoding="utf-8-sig")
    if not acc_df.empty:
        acc_df["accuracy"] = acc_df["correct"] / acc_df["total"]
        acc_df.to_csv(OUTPUT_DIR / "正确率汇总.csv", index=False, encoding="utf-8-sig")

    return time_df, acc_df


def plot_time(time_df: pd.DataFrame) -> None:
    if time_df.empty:
        return

    plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "STHeiti", "Arial Unicode MS", "Arial Unicode"]
    plt.rcParams["axes.unicode_minus"] = False

    pivot = time_df.pivot_table(index="date", columns="subject", values="hours", aggfunc="sum").fillna(0)
    pivot.index = pd.to_datetime(pivot.index)
    pivot = pivot.sort_index()

    ax = pivot.plot(kind="bar", stacked=True, figsize=(11, 6), width=0.8)
    ax.set_title("每日学习时长")
    ax.set_xlabel("日期")
    ax.set_ylabel("小时")
    ax.legend(title="科目", loc="upper left")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "每日学习时长.png", dpi=200)
    plt.close()

    subject_total = time_df.groupby("subject")["hours"].sum().sort_values(ascending=False)
    ax = subject_total.plot(kind="bar", figsize=(8, 5), color="#4C78A8")
    ax.set_title("各科学习总时长")
    ax.set_xlabel("科目")
    ax.set_ylabel("小时")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "各科学习总时长.png", dpi=200)
    plt.close()


def plot_accuracy(acc_df: pd.DataFrame) -> None:
    if acc_df.empty:
        return

    plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "STHeiti", "Arial Unicode MS", "Arial Unicode"]
    plt.rcParams["axes.unicode_minus"] = False

    acc_df = acc_df.copy()
    acc_df["date"] = pd.to_datetime(acc_df["date"])
    acc_df["accuracy"] = acc_df["correct"] / acc_df["total"]

    plt.figure(figsize=(10, 5))
    for subject, group in acc_df.groupby("subject"):
        group = group.sort_values("date")
        plt.plot(group["date"], group["accuracy"], marker="o", label=subject)

    plt.title("正确率趋势")
    plt.xlabel("日期")
    plt.ylabel("正确率")
    plt.ylim(0, 1.05)
    plt.grid(True, alpha=0.3)
    plt.legend(title="科目")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "正确率趋势.png", dpi=200)
    plt.close()


def markdown_dashboard(time_df: pd.DataFrame, acc_df: pd.DataFrame) -> str:
    lines = [
        "# 我的学习可视化",
        "",
        "这个页面由 `tools/generate_personal_dashboard.py` 自动生成。",
        "",
    ]

    if time_df.empty:
        lines += ["## 学习时长", "", "还没有有效学习时长记录。", ""]
    else:
        total_hours = time_df["hours"].sum()
        days = time_df["date"].nunique()
        subject_total = time_df.groupby("subject")["hours"].sum().sort_values(ascending=False)

        lines += [
            "## 学习时长",
            "",
            f"- 记录天数：{days}",
            f"- 总学习时长：{total_hours:.1f} 小时",
            f"- 日均学习时长：{total_hours / days:.1f} 小时",
            "",
            "![每日学习时长](每日学习时长.png)",
            "",
            "![各科学习总时长](各科学习总时长.png)",
            "",
            "| 科目 | 总时长 |",
            "| --- | --- |",
        ]
        for subject, hours in subject_total.items():
            lines.append(f"| {subject} | {hours:.1f}h |")
        lines.append("")

    if acc_df.empty:
        lines += ["## 正确率", "", "还没有有效正确率记录。", ""]
    else:
        acc_df = acc_df.copy()
        acc_df["accuracy"] = acc_df["correct"] / acc_df["total"]
        subject_acc = acc_df.groupby("subject").apply(
            lambda group: group["correct"].sum() / group["total"].sum(),
            include_groups=False,
        ).sort_values(ascending=False)

        lines += [
            "## 正确率",
            "",
            "![正确率趋势](正确率趋势.png)",
            "",
            "| 科目 | 综合正确率 |",
            "| --- | --- |",
        ]
        for subject, acc in subject_acc.items():
            lines.append(f"| {subject} | {acc:.1%} |")
        lines.append("")

    lines += [
        "## 怎么更新",
        "",
        "本地写完每日记录后运行：",
        "",
        "```bash",
        "python3 tools/generate_personal_dashboard.py",
        "```",
        "",
        "然后提交并推送到 GitHub。",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    time_entries, accuracy_entries = collect_entries()
    time_df, acc_df = save_tables(time_entries, accuracy_entries)
    plot_time(time_df)
    plot_accuracy(acc_df)
    (OUTPUT_DIR / "README.md").write_text(markdown_dashboard(time_df, acc_df), encoding="utf-8")
    print(f"[log] 已生成个人学习可视化：{OUTPUT_DIR}")


if __name__ == "__main__":
    main()
