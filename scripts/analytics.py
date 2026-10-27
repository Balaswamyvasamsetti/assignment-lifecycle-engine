"""Analytics CLI tool executing business intelligence and audit queries against database.sqlite."""

import sqlite3
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.config import SQLITE_DB_PATH


def run_analytics_queries(db_path: Path) -> None:
    console = Console()
    console.print(Panel.fit("[bold green]ACADEMIC LIFECYCLE ANALYTICS & AUDIT REPORT[/bold green]", border_style="green"))

    if not db_path.exists():
        console.print(f"[bold red]Database not found at {db_path}. Please run generation or export-sql first.[/bold red]")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Query 1: Overall Platform Summary
    table_summary = Table(title="1. Core Operational Metrics", show_lines=True)
    table_summary.add_column("Metric", style="cyan")
    table_summary.add_column("Value", justify="right", style="magenta")

    queries = [
        ("Total Active Courses", "SELECT COUNT(*) FROM courses WHERE status = 'ACTIVE'"),
        ("Total Active Learners", "SELECT COUNT(*) FROM learners WHERE status = 'ACTIVE'"),
        ("Total Active Enrollments", "SELECT COUNT(*) FROM enrollments WHERE status = 'ACTIVE'"),
        ("Total Published Assignments", "SELECT COUNT(*) FROM assignments WHERE status = 'PUBLISHED'"),
        ("Total Submissions Recorded", "SELECT COUNT(*) FROM submissions"),
        ("Total Graded Submissions", "SELECT COUNT(*) FROM grades"),
        ("Total Resubmissions Executed", "SELECT COUNT(*) FROM resubmissions"),
        ("Total Appeals Filed", "SELECT COUNT(*) FROM appeals"),
    ]

    for label, q in queries:
        val = cur.execute(q).fetchone()[0]
        table_summary.add_row(label, f"{val:,}")
    console.print(table_summary)

    # Query 2: Lateness and Penalty Impact
    table_late = Table(title="2. Submission Lateness & Penalty Breakdown", show_lines=True)
    table_late.add_column("Category", style="yellow")
    table_late.add_column("Count", justify="right", style="cyan")
    table_late.add_column("Percentage", justify="right", style="blue")
    table_late.add_column("Avg Raw Score", justify="right", style="green")
    table_late.add_column("Avg Late Penalty", justify="right", style="red")
    table_late.add_column("Avg Final Score", justify="right", style="magenta")

    q_late = """
    SELECT 
        s.is_late,
        COUNT(*),
        ROUND(AVG(g.raw_score), 2),
        ROUND(AVG(g.late_penalty_applied), 2),
        ROUND(AVG(g.final_score), 2)
    FROM submissions s
    JOIN grades g ON s.submission_id = g.submission_id
    GROUP BY s.is_late
    """
    total_subs = cur.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
    for row in cur.execute(q_late).fetchall():
        is_late_str, cnt, avg_raw, avg_pen, avg_final = row
        cat = "Late Submissions" if is_late_str in ("True", "1") else "On-Time Submissions"
        pct = f"{(cnt / total_subs) * 100:.1f}%" if total_subs > 0 else "0.0%"
        table_late.add_row(cat, f"{cnt:,}", pct, f"{avg_raw:.2f}", f"{avg_pen:.2f}", f"{avg_final:.2f}")
    console.print(table_late)

    # Query 3: Resubmission Score Improvements (v1 vs v2)
    table_resub = Table(title="3. Resubmission Score Delta (v1 vs v2)", show_lines=True)
    table_resub.add_column("Metric", style="cyan")
    table_resub.add_column("Value", justify="right", style="magenta")

    q_resub = """
    SELECT 
        COUNT(*),
        ROUND(AVG(g1.final_score), 2),
        ROUND(AVG(g2.final_score), 2),
        ROUND(AVG(g2.final_score - g1.final_score), 2)
    FROM resubmissions r
    JOIN grades g1 ON r.previous_submission_id = g1.submission_id
    JOIN grades g2 ON r.new_submission_id = g2.submission_id
    """
    resub_row = cur.execute(q_resub).fetchone()
    if resub_row and resub_row[0] > 0:
        table_resub.add_row("Total Resubmission Draft Pairs", f"{resub_row[0]:,}")
        table_resub.add_row("Avg Draft 1 Final Score", f"{resub_row[1]:.2f}")
        table_resub.add_row("Avg Draft 2 Final Score", f"{resub_row[2]:.2f}")
        table_resub.add_row("Avg Score Improvement Delta", f"+{resub_row[3]:.2f} pts")
    console.print(table_resub)

    # Query 4: Appeal Outcomes & Audit Trail Compliance
    table_appeal = Table(title="4. Grade Appeal Outcomes & Security Audit Status", show_lines=True)
    table_appeal.add_column("Appeal Status", style="yellow")
    table_appeal.add_column("Count", justify="right", style="cyan")
    table_appeal.add_column("Avg Original Score", justify="right", style="green")
    table_appeal.add_column("Avg Updated Score", justify="right", style="magenta")
    table_appeal.add_column("Audited Count (audit_logged=True)", justify="right", style="blue")

    q_appeal = """
    SELECT 
        status,
        COUNT(*),
        ROUND(AVG(original_score), 2),
        ROUND(AVG(CASE WHEN updated_score IS NOT NULL THEN updated_score ELSE NULL END), 2),
        SUM(CASE WHEN audit_logged IN ('True', '1') THEN 1 ELSE 0 END)
    FROM appeals
    GROUP BY status
    """
    for row in cur.execute(q_appeal).fetchall():
        st, cnt, avg_orig, avg_upd, aud_cnt = row
        upd_str = f"{avg_upd:.2f}" if avg_upd is not None else "N/A"
        table_appeal.add_row(st, str(cnt), f"{avg_orig:.2f}", upd_str, f"{aud_cnt} / {cnt}")
    console.print(table_appeal)

    conn.close()


if __name__ == "__main__":
    run_analytics_queries(SQLITE_DB_PATH)
