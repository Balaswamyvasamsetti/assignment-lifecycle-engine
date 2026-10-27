import hashlib
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.config import DEFAULT_SEED
from src.generator.orchestrator import run_pipeline


def compute_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def count_lines(file_path: Path) -> int:
    with open(file_path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def main() -> None:
    console = Console()
    console.print(Panel.fit("[bold cyan]DETERMINISTIC REPRODUCIBILITY VERIFICATION[/bold cyan]", border_style="cyan"))
    console.print(f"Executing two independent generation cycles with seed: [bold green]{DEFAULT_SEED}[/bold green]...")

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        run1_dir = tmp_dir / "run1"
        run2_dir = tmp_dir / "run2"

        # Execution 1
        run_pipeline(
            scale="starter",
            seed=DEFAULT_SEED,
            out_dir=run1_dir / "raw",
            ground_truth_path=run1_dir / "ground_truth.csv",
            sqlite_db_path=run1_dir / "database.sqlite",
            export_json=True,
            json_out_dir=run1_dir / "json",
            manifest_path=run1_dir / "manifest.json",
        )

        # Execution 2
        run_pipeline(
            scale="starter",
            seed=DEFAULT_SEED,
            out_dir=run2_dir / "raw",
            ground_truth_path=run2_dir / "ground_truth.csv",
            sqlite_db_path=run2_dir / "database.sqlite",
            export_json=True,
            json_out_dir=run2_dir / "json",
            manifest_path=run2_dir / "manifest.json",
        )

        expected_files = [
            "courses.csv",
            "learners.csv",
            "enrollments.csv",
            "assignments.csv",
            "rubrics.csv",
            "rubric_criteria.csv",
            "submissions.csv",
            "submission_artifacts.csv",
            "grades.csv",
            "feedback.csv",
            "resubmissions.csv",
            "appeals.csv",
        ]

        table = Table(title="SHA-256 Checksum Verification Across Independent Runs", show_lines=True)
        table.add_column("Filename", style="yellow")
        table.add_column("Lines", justify="right", style="cyan")
        table.add_column("Run 1 SHA-256 (First 16 chars)", justify="center", style="magenta")
        table.add_column("Run 2 SHA-256 (First 16 chars)", justify="center", style="magenta")
        table.add_column("Status", justify="center", style="green")

        all_matched = True
        for fname in expected_files:
            f1 = run1_dir / "raw" / fname
            f2 = run2_dir / "raw" / fname

            h1 = compute_sha256(f1)
            h2 = compute_sha256(f2)
            lines = count_lines(f1)

            matched = (h1 == h2) and (lines == count_lines(f2))
            if not matched:
                all_matched = False

            status_str = "[bold green]MATCH (IDENTICAL)[/bold green]" if matched else "[bold red]MISMATCH[/bold red]"
            table.add_row(fname, str(lines), h1[:16] + "...", h2[:16] + "...", status_str)

        # Ground truth check
        gt1 = run1_dir / "ground_truth.csv"
        gt2 = run2_dir / "ground_truth.csv"
        h1_gt = compute_sha256(gt1)
        h2_gt = compute_sha256(gt2)
        gt_matched = (h1_gt == h2_gt)
        table.add_row(
            "ground_truth.csv",
            str(count_lines(gt1)),
            h1_gt[:16] + "...",
            h2_gt[:16] + "...",
            "[bold green]MATCH (IDENTICAL)[/bold green]" if gt_matched else "[bold red]MISMATCH[/bold red]",
        )

        console.print(table)

        if all_matched and gt_matched:
            console.print("[bold green]SUCCESS: 100% Bit-for-Bit Deterministic Reproducibility Confirmed![/bold green]")
        else:
            console.print("[bold red]FAILURE: Non-deterministic hashes detected![/bold red]")


if __name__ == "__main__":
    main()
