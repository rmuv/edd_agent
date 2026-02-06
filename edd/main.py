import json
import logging
import time
import os
from pathlib import Path
from dotenv import load_dotenv

from src.agent import AutonomousAgent
from src.validation import validate_response
from eval_runner import EvalRunner

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    print("\n" + "=" * 60)
    print("🤖 STARTING AUTONOMOUS AGENT RUN (Orchestrator Mode)")
    print("=" * 60)

    # Load Evals
    evals_path = Path("evals.jsonl")
    if not evals_path.exists():
        print("Error: evals.jsonl not found.")
        return

    records = []
    with open(evals_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"📂 Loaded {len(records)} eval records\n")

    agent = AutonomousAgent()
    eval_runner = EvalRunner()
    results = []
    eval_findings = []
    passed_count = 0

    for idx, record in enumerate(records, 1):
        task_id = record.get("task_id", "unknown")
        print(f"🔹 Processing Task {idx}/{len(records)}: {task_id}")

        try:
            # Throttling
            time.sleep(1)

            # Execute agent
            start_time = time.time()
            output = agent.run_with_retries(record)
            end_time = time.time()
            
            # Calculate metrics
            latency_ms = (end_time - start_time) * 1000
            
            # Get token stats from tracer if available
            metrics = {
                "latency_ms": latency_ms,
                "personalization_score": 0,  # Will be calculated by eval_runner
                "locale_accuracy": 0,  # Will be calculated by eval_runner
                "safety_violations": 0
            }

            # Run comprehensive evaluation
            findings = eval_runner.run_eval(record, output or {}, metrics)
            eval_findings.append(findings)
            
            # Legacy validation for backward compatibility
            expected = record.get("expected", {})
            errors = validate_response(expected, output or {})

            status = findings["overall_status"]
            if status in ["passed", "passed_with_warnings"]:
                passed_count += 1

            results.append(
                {
                    "task_id": task_id,
                    "status": status,
                    "output": output,
                    "errors": errors,
                    "eval_findings": findings
                }
            )

        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            results.append(
                {
                    "task_id": task_id,
                    "status": "error",
                    "output": None,
                    "errors": [str(e)],
                    "eval_findings": None
                }
            )

    print("\n" + "=" * 60)
    print(f"📊 FINAL RESULTS: {passed_count}/{len(records)} Passed")
    print("=" * 60)

    # Save Results
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    with open(output_dir / "results_orchestrator.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Save detailed evaluation report
    report_text = eval_runner.generate_report(eval_findings)
    with open(output_dir / "eval_report.txt", "w", encoding="utf-8") as f:
        f.write(report_text)
    
    # Save structured eval findings
    with open(output_dir / "eval_findings.json", "w", encoding="utf-8") as f:
        json.dump(eval_findings, f, indent=2, ensure_ascii=False)

    print("✅ Results saved to output/results_orchestrator.json")
    print("📋 Detailed evaluation report saved to output/eval_report.txt")
    print("📊 Structured findings saved to output/eval_findings.json")
    print("🔍 Trace report generated at output/logs/trace_report.html")


if __name__ == "__main__":
    main()
