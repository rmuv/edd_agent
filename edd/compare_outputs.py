#!/usr/bin/env python3
"""
Output comparison tool - shows side-by-side comparison of expected vs actual outputs.

Usage:
    python compare_outputs.py
    python compare_outputs.py --task prospect_welcome_day0
"""

import json
import argparse
from pathlib import Path
from difflib import unified_diff, SequenceMatcher


class OutputComparer:
    def __init__(self, evals_path="evals.jsonl", results_path="output/results_orchestrator.json"):
        self.evals_path = Path(evals_path)
        self.results_path = Path(results_path)
        self.eval_records = {}
        self.results = {}
        
    def load_data(self):
        """Load evaluation records and agent results."""
        # Load eval records
        with open(self.evals_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    self.eval_records[record["task_id"]] = record
        
        # Load results
        with open(self.results_path, "r", encoding="utf-8") as f:
            results_list = json.load(f)
            for result in results_list:
                self.results[result["task_id"]] = result
    
    def compare_task(self, task_id: str) -> str:
        """Generate detailed comparison for a specific task."""
        if task_id not in self.eval_records:
            return f"❌ Task '{task_id}' not found in eval records."
        
        if task_id not in self.results:
            return f"❌ Task '{task_id}' not found in results."
        
        eval_record = self.eval_records[task_id]
        result = self.results[task_id]
        
        expected = eval_record.get("expected", {})
        actual = result.get("output", {})
        
        lines = []
        lines.append("=" * 80)
        lines.append(f"TASK: {task_id}")
        lines.append("=" * 80)
        lines.append("")
        
        # Compare next_message
        exp_msg = expected.get("next_message", {}) or {}
        act_msg = actual.get("next_message", {}) or {}
        
        lines.append("📧 NEXT MESSAGE")
        lines.append("-" * 80)
        
        # Channel
        lines.append("\n🔹 Channel:")
        lines.append(f"  Expected: {exp_msg.get('channel')}")
        lines.append(f"  Actual:   {act_msg.get('channel')}")
        match = exp_msg.get('channel') == act_msg.get('channel')
        lines.append(f"  Status:   {'✅ MATCH' if match else '❌ MISMATCH'}")
        
        # Subject (if email)
        if exp_msg.get('subject') or act_msg.get('subject'):
            lines.append("\n🔹 Subject:")
            lines.append(f"  Expected: {exp_msg.get('subject')}")
            lines.append(f"  Actual:   {act_msg.get('subject')}")
            similarity = self._calculate_similarity(exp_msg.get('subject', ''), act_msg.get('subject', ''))
            lines.append(f"  Similarity: {similarity:.1%}")
        
        # Body
        lines.append("\n🔹 Body:")
        exp_body = exp_msg.get('body')
        act_body = act_msg.get('body')
        
        if exp_body is None and act_body is None:
            lines.append("  Both: null (no message)")
        else:
            lines.append("  Expected:")
            lines.append(f"    {self._format_multiline(exp_body or 'null', indent=4)}")
            lines.append("  Actual:")
            lines.append(f"    {self._format_multiline(act_body or 'null', indent=4)}")
            
            if exp_body and act_body:
                similarity = self._calculate_similarity(exp_body, act_body)
                lines.append(f"  Similarity: {similarity:.1%}")
                
                if similarity < 1.0:
                    lines.append("\n  📝 Differences:")
                    diff = self._generate_diff(exp_body, act_body)
                    lines.append(diff)
        
        # CTA
        exp_cta = exp_msg.get('cta', {}) or {}
        act_cta = act_msg.get('cta', {}) or {}
        
        if exp_cta or act_cta:
            lines.append("\n🔹 CTA:")
            lines.append(f"  Expected: {json.dumps(exp_cta, ensure_ascii=False)}")
            lines.append(f"  Actual:   {json.dumps(act_cta, ensure_ascii=False)}")
            match = exp_cta.get('type') == act_cta.get('type')
            lines.append(f"  Type Match: {'✅' if match else '❌'}")
        
        # Next action
        exp_action = expected.get("next_action", {}) or {}
        act_action = actual.get("next_action", {}) or {}
        
        lines.append("\n⚡ NEXT ACTION")
        lines.append("-" * 80)
        lines.append(f"  Expected: {json.dumps(exp_action, ensure_ascii=False)}")
        lines.append(f"  Actual:   {json.dumps(act_action, ensure_ascii=False)}")
        match = exp_action.get('type') == act_action.get('type')
        lines.append(f"  Type Match: {'✅' if match else '❌'}")
        
        # Thresholds
        thresholds = eval_record.get("thresholds", {})
        if thresholds:
            lines.append("\n📊 THRESHOLDS")
            lines.append("-" * 80)
            for key, value in thresholds.items():
                lines.append(f"  • {key}: {value}")
        
        lines.append("\n" + "=" * 80)
        
        return "\n".join(lines)
    
    def compare_all(self) -> str:
        """Generate summary comparison for all tasks."""
        lines = []
        lines.append("=" * 80)
        lines.append("ALL TASKS COMPARISON SUMMARY")
        lines.append("=" * 80)
        lines.append("")
        
        for task_id in self.eval_records.keys():
            if task_id not in self.results:
                lines.append(f"⚠️  {task_id}: No result found")
                continue
            
            expected = self.eval_records[task_id].get("expected", {})
            actual = self.results[task_id].get("output", {})
            
            exp_msg = expected.get("next_message", {}) or {}
            act_msg = actual.get("next_message", {}) or {}
            
            channel_match = exp_msg.get('channel') == act_msg.get('channel')
            
            exp_body = exp_msg.get('body')
            act_body = act_msg.get('body')
            
            if exp_body and act_body:
                body_sim = self._calculate_similarity(exp_body, act_body)
            else:
                body_sim = 1.0 if (exp_body is None and act_body is None) else 0.0
            
            action_match = expected.get("next_action", {}).get('type') == actual.get("next_action", {}).get('type')
            
            status = "✅" if (channel_match and body_sim > 0.85 and action_match) else "⚠️" if body_sim > 0.7 else "❌"
            
            lines.append(f"{status} {task_id}:")
            lines.append(f"    Channel: {'✓' if channel_match else '✗'} | Body: {body_sim:.0%} | Action: {'✓' if action_match else '✗'}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity ratio between two strings."""
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _format_multiline(self, text: str, indent: int = 0) -> str:
        """Format multiline text with indentation."""
        if not text or text == 'null':
            return text
        prefix = " " * indent
        lines = text.split('\n')
        return f"\n{prefix}".join(lines)
    
    def _generate_diff(self, text1: str, text2: str) -> str:
        """Generate unified diff between two texts."""
        lines1 = text1.splitlines(keepends=True)
        lines2 = text2.splitlines(keepends=True)
        
        diff = unified_diff(lines1, lines2, lineterm='', fromfile='expected', tofile='actual')
        diff_lines = list(diff)
        
        if not diff_lines:
            return "    (No character-level differences)"
        
        formatted = []
        for line in diff_lines[:20]:  # Limit to first 20 lines
            if line.startswith('---') or line.startswith('+++'):
                continue
            formatted.append(f"    {line.rstrip()}")
        
        if len(diff_lines) > 20:
            formatted.append("    ... (diff truncated)")
        
        return "\n".join(formatted)


def main():
    parser = argparse.ArgumentParser(description="Compare expected vs actual outputs")
    parser.add_argument(
        "--task",
        help="Specific task ID to compare (optional, compares all if not specified)",
    )
    parser.add_argument(
        "--evals",
        default="evals.jsonl",
        help="Path to evaluation JSONL file",
    )
    parser.add_argument(
        "--results",
        default="output/results_orchestrator.json",
        help="Path to results JSON file",
    )
    args = parser.parse_args()
    
    comparer = OutputComparer(args.evals, args.results)
    
    try:
        comparer.load_data()
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        return
    
    if args.task:
        # Compare specific task
        print(comparer.compare_task(args.task))
    else:
        # Compare all tasks
        print(comparer.compare_all())
        print("\n💡 Tip: Use --task <task_id> to see detailed comparison for a specific task")


if __name__ == "__main__":
    main()
