import json
import logging
import time
import os
from pathlib import Path
from dotenv import load_dotenv

from src.agent import AutonomousAgent
from src.validation import validate_response

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
    results = []
    passed_count = 0

    for idx, record in enumerate(records, 1):
        task_id = record.get("task_id", "unknown")
        print(f"🔹 Processing Task {idx}/{len(records)}: {task_id}")

        try:
            # Throttling
            time.sleep(1)

            # Execute
            output = agent.run_with_retries(record)

            # Final Validation for Stats
            expected = record.get("expected", {})
            errors = validate_response(expected, output or {})

            status = "passed" if not errors else "failed"
            if status == "passed":
                passed_count += 1

            results.append(
                {
                    "task_id": task_id,
                    "status": status,
                    "output": output,
                    "errors": errors,
                }
            )

        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")

    print("\n" + "=" * 60)
    print(f"📊 FINAL RESULTS: {passed_count}/{len(records)} Passed")
    print("=" * 60)

    # Save Results
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    with open(output_dir / "results_orchestrator.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("✅ Results saved to output/results_orchestrator.json")
    print("🔍 Trace report generated at output/logs/trace_report.html")


if __name__ == "__main__":
    main()
