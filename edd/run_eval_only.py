#!/usr/bin/env python3
"""
Standalone evaluation script - runs evaluation on existing agent outputs
without re-executing the agent.

Usage:
    python run_eval_only.py
    python run_eval_only.py --results output/results_orchestrator.json
"""

import json
import argparse
from pathlib import Path
from eval_runner import EvalRunner


def main():
    parser = argparse.ArgumentParser(description="Evaluate existing agent results")
    parser.add_argument(
        "--results",
        default="output/results_orchestrator.json",
        help="Path to agent results JSON file",
    )
    parser.add_argument(
        "--evals",
        default="evals.jsonl",
        help="Path to evaluation JSONL file",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory to save evaluation reports",
    )
    args = parser.parse_args()

    # Load evaluation records
    evals_path = Path(args.evals)
    if not evals_path.exists():
        print(f"❌ Error: {args.evals} not found.")
        return

    eval_records = {}
    with open(evals_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                record = json.loads(line)
                eval_records[record["task_id"]] = record

    # Load agent results
    results_path = Path(args.results)
    if not results_path.exists():
        print(f"❌ Error: {args.results} not found.")
        return

    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    print("\n" + "=" * 60)
    print("🔍 RUNNING EVALUATION ON EXISTING RESULTS")
    print("=" * 60)
    print(f"📂 Eval records: {len(eval_records)}")
    print(f"📊 Results found: {len(results)}")
    print()

    # Run evaluation
    eval_runner = EvalRunner()
    eval_findings = []

    for result in results:
        task_id = result["task_id"]
        output = result.get("output")

        if task_id not in eval_records:
            print(f"⚠️  Warning: No eval record found for {task_id}")
            continue

        eval_record = eval_records[task_id]

        # Extract metrics if available
        metrics = {
            "latency_ms": 0,  # Not available in offline eval
            "personalization_score": 0,
            "locale_accuracy": 0,
            "safety_violations": 0,
        }

        # Run comprehensive evaluation
        findings = eval_runner.run_eval(eval_record, output or {}, metrics)
        eval_findings.append(findings)

        # Print quick status
        status_emoji = (
            "✅"
            if findings["overall_status"] == "passed"
            else "⚠️"
            if findings["overall_status"] == "passed_with_warnings"
            else "❌"
        )
        print(f"{status_emoji} {task_id}: {findings['overall_status'].upper()}")

    # Generate and save reports
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    report_text = eval_runner.generate_report(eval_findings)
    with open(output_dir / "eval_report.txt", "w", encoding="utf-8") as f:
        f.write(report_text)

    with open(output_dir / "eval_findings.json", "w", encoding="utf-8") as f:
        json.dump(eval_findings, f, indent=2, ensure_ascii=False)

    # Print summary
    passed = sum(1 for f in eval_findings if f["overall_status"] == "passed")
    warnings = sum(
        1 for f in eval_findings if f["overall_status"] == "passed_with_warnings"
    )
    failed = sum(1 for f in eval_findings if f["overall_status"] == "failed")

    print("\n" + "=" * 60)
    print("📊 EVALUATION SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {passed}/{len(eval_findings)}")
    print(f"⚠️  Warnings: {warnings}/{len(eval_findings)}")
    print(f"❌ Failed: {failed}/{len(eval_findings)}")
    print()
    print(f"📋 Detailed report: {output_dir / 'eval_report.txt'}")
    print(f"📊 Structured findings: {output_dir / 'eval_findings.json'}")


if __name__ == "__main__":
    main()
