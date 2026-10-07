"""
Command Line Interface for NEXORA-8.
Provides beautiful terminal execution with live stage progress, diff previews, and evidence reporting.
"""

import argparse
import os
import sys
import time

# Ensure Windows UTF-8 stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

from nexora.config import Config
from nexora.agents.base import AgentEvent
from nexora.agents.orchestrator import OrchestratorAgent
from nexora.analyzer.repo_indexer import CodebaseIndexer
from nexora.server.app import create_app

console = Console(force_terminal=True, safe_box=True)


def run_repair_cli(args):
    repo_path = os.path.abspath(args.repo)
    task = args.task
    apply_changes = args.apply

    cfg = Config()
    if args.provider:
        cfg.model_provider = args.provider
    if args.model:
        cfg.model_name = args.model
    if args.max_attempts:
        cfg.max_repair_attempts = args.max_attempts
    if args.timeout:
        cfg.test_timeout_seconds = args.timeout

    console.print(Panel.fit(
        f"[bold cyan]NEXORA-8: AI Software Engineering Agent[/bold cyan]\n"
        f"[dim]HackNex 2026 Qualifier - Problem Statement HNX26PSI09[/dim]\n\n"
        f"[bold]Target Repo:[/bold] {repo_path}\n"
        f"[bold]Task:[/bold] {task}\n"
        f"[bold]Model Provider:[/bold] {cfg.model_provider} ({cfg.model_name})\n"
        f"[bold]Auto-Apply Changes:[/bold] {'[green]Yes[/green]' if apply_changes else '[yellow]Sandbox Only[/yellow]'}",
        border_style="cyan"
    ))

    orchestrator = OrchestratorAgent(cfg)

    def event_listener(event: AgentEvent):
        if event.event_type == "log":
            console.print(f"  [dim]{event.agent_name}:[/dim] {event.message}")
        elif event.event_type == "status_change":
            console.print(f"[bold magenta]> [{event.agent_name}][/bold magenta] {event.message}")

    orchestrator.add_event_listener(event_listener)

    def progress_cb(desc: str, pct: float):
        console.print(f"[cyan][{int(pct*100)}%][/cyan] {desc}")

    session = orchestrator.execute_task(
        repo_path=repo_path,
        task_description=task,
        apply_to_original=apply_changes,
        progress_callback=progress_cb,
    )

    console.print()
    if session.status == "success":
        console.print(Panel(
            f"[bold green][OK] REPAIR VERIFIED AND ACCEPTED (0 Regressions)[/bold green]\n"
            f"Passing Tests: {session.final_tests.passed_count}/{session.final_tests.total_tests}\n"
            f"Attempts: {session.attempts}/{session.max_attempts}",
            border_style="green"
        ))
    else:
        console.print(Panel(
            f"[bold red][FAIL] REPAIR FAILED VERIFICATION - ROLLED BACK[/bold red]\n"
            f"All sandbox modifications reverted to guarantee safety.",
            border_style="red"
        ))

    # Show Diffs
    if session.patches:
        console.print("\n[bold]Generated Code Patches:[/bold]")
        for p in session.patches:
            if p.diff_text:
                console.print(f"[bold yellow]File: {p.file_path}[/bold yellow] ({p.explanation})")
                syntax = Syntax(p.diff_text, "diff", theme="monokai", line_numbers=True)
                console.print(syntax)

    # Show Gates Table
    table = Table(title="Deterministic Verification Matrix", border_style="dim")
    table.add_column("Verification Gate", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")

    ast_ok = session.guard_report.passed if session.guard_report else False
    table.add_row("Python AST Syntax", "[green]PASSED[/green]" if ast_ok else "[red]FAILED[/red]", "AST parsed without syntax errors")
    table.add_row("Import Resolution", "[green]PASSED[/green]" if ast_ok else "[red]FAILED[/red]", "0 hallucinated imports detected")
    table.add_row("Undefined Name Scope", "[green]PASSED[/green]" if ast_ok else "[red]FAILED[/red]", "All identifiers resolved in scope")
    
    reg_ok = session.verification_verdict and not session.verification_verdict.has_regressions
    table.add_row("Zero Regressions", "[green]PASSED[/green]" if reg_ok else "[red]FAILED[/red]", "100% baseline tests preserved")

    if session.generated_tests:
        table.add_row("Generated Acceptance Test", "[green]PASSED[/green]" if session.generated_tests.passed else "[red]FAILED[/red]", f"{session.generated_tests.test_count} new test(s) verified")

    console.print(table)

    # Export report if requested
    if args.output_report:
        report_file = args.output_report
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(session.evidence_report.to_markdown() if session.evidence_report else "No report.")
        console.print(f"\n[green]Saved evidence report to {report_file}[/green]")

    sys.exit(0 if session.status == "success" else 1)


def serve_web_cli(args):
    cfg = Config()
    cfg.server_host = args.host
    cfg.server_port = args.port
    app = create_app(cfg)
    console.print(Panel.fit(
        f"[bold green]Starting NEXORA-8 Agent Monitoring Server[/bold green]\n"
        f"Dashboard URL: [cyan]http://localhost:{args.port}[/cyan]\n"
        f"REST API: [cyan]http://localhost:{args.port}/api/health[/cyan]\n"
        f"Press Ctrl+C to stop server.",
        border_style="green"
    ))
    app.run(host=args.host, port=args.port, debug=args.debug)


def index_repo_cli(args):
    repo_path = os.path.abspath(args.repo)
    console.print(f"[cyan]Indexing codebase at {repo_path}...[/cyan]")
    indexer = CodebaseIndexer(repo_path)
    index = indexer.index()

    table = Table(title=f"Codebase Index: {os.path.basename(repo_path)}")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="green")

    table.add_row("Total Python Files", str(index.total_files))
    table.add_row("Total Lines of Code", str(index.total_lines))
    table.add_row("Total Classes & Functions", str(index.total_symbols))
    table.add_row("Discovered Tests", str(index.total_tests))

    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="NEXORA-8: AI Software Engineering Agent CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run command
    run_p = subparsers.add_parser("run", help="Run autonomous bug fix or feature addition on a repository")
    run_p.add_argument("--repo", "-r", default=".", help="Path to target repository")
    run_p.add_argument("--task", "-t", required=True, help="Task description or bug report")
    run_p.add_argument("--apply", "-a", action="store_true", help="Apply verified changes back to repository")
    run_p.add_argument("--provider", "-p", default=None, help="LLM Provider (gemini, openai, anthropic, ollama, heuristic)")
    run_p.add_argument("--model", "-m", default=None, help="Model name")
    run_p.add_argument("--max-attempts", type=int, default=3, help="Max repair attempts")
    run_p.add_argument("--timeout", type=int, default=45, help="Test timeout in seconds")
    run_p.add_argument("--output-report", "-o", default=None, help="Path to save markdown evidence report")

    # Serve command
    serve_p = subparsers.add_parser("serve", help="Launch the Agent Monitor Web Server & Dashboard")
    serve_p.add_argument("--host", default="0.0.0.0", help="Host interface")
    serve_p.add_argument("--port", type=int, default=5000, help="Port number")
    serve_p.add_argument("--debug", action="store_true", help="Enable debug mode")

    # Index command
    idx_p = subparsers.add_parser("index", help="Analyze and index an existing codebase structure")
    idx_p.add_argument("--repo", "-r", default=".", help="Path to repository")

    args = parser.parse_args()

    if args.command == "run":
        run_repair_cli(args)
    elif args.command == "serve":
        serve_web_cli(args)
    elif args.command == "index":
        index_repo_cli(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
