# Eval Runner Documentation

## Overview

The **Eval Runner** is a comprehensive evaluation framework that validates agent outputs against expected results and checks performance thresholds defined in the JSONL evaluation files.

## Features

### 1. **Output Match Validation**
Compares the agent's output with expected output:
- ✅ Channel matching (SMS, Email, none)
- ✅ Subject line similarity (for emails)
- ✅ Body text similarity with threshold scoring
- ✅ CTA (Call-to-Action) type matching
- ✅ Next action type validation

### 2. **Threshold Validation**
Validates performance metrics against defined thresholds:
- ⏱️ **Latency**: `p95_latency_ms` - Maximum acceptable response time
- 🎯 **Personalization Score**: `personalization_score_min` - Minimum required personalization
- 🌍 **Locale Accuracy**: `locale_accuracy_min` - Language/locale correctness
- 🛡️ **Safety Violations**: `safety_violations_max` - Maximum allowed safety issues

### 3. **Assertion Validation**
Checks required states and compliance:
- `consent_verified` - Validates channel consent is properly checked
- `fair_housing_check_passed` - Fair housing compliance
- `brand_style_applied` - Brand guidelines adherence
- `renewal_offer_loaded` - (Resident-specific) renewal data validation

### 4. **Constraint Validation**
Enforces specific requirements:
- ✉️ **Opt-out instructions**: Required for SMS ("STOP") and Email
- 🌐 **Locale applied**: Ensures messages match user's language preference
- 🔒 **Respect consent**: No messages sent when all channels are denied
- 🎯 **Primary CTA**: Validates the main call-to-action matches intent

### 5. **Quality Scoring**
Calculates quality metrics:
- **Body Similarity**: Measures text similarity to expected output (0-100%)
- **Personalization Score**: Checks usage of profile data (name, amenities, unit)
- **Locale Accuracy**: Validates language-specific content
- **Safety Violations**: Tracks harmful/inappropriate content (0 expected)

## Usage

### Running Evaluations

```bash
# Activate virtual environment
source venv/bin/activate

# Run the agent with comprehensive evaluation
python main.py
```

### Output Files

After running, the following files are generated in the `output/` directory:

1. **`results_orchestrator.json`** - Full results with agent outputs and eval findings
2. **`eval_report.txt`** - Human-readable evaluation report
3. **`eval_findings.json`** - Structured JSON with detailed findings
4. **`logs/trace_report.html`** - Visual execution trace

### Example Eval Record (JSONL)

```json
{
  "task_id": "prospect_welcome_day0",
  "persona": "prospect",
  "lifecycle_stage": "new",
  "consent": {
    "email_opt_in": true,
    "sms_opt_in": true,
    "voice_opt_in": false
  },
  "channel_preferences": ["sms", "email"],
  "input": {
    "property_name": "Oak Ridge Apartments",
    "language": "en",
    "profile": {
      "first_name": "Taylor"
    }
  },
  "assertions": {
    "required_states": ["consent_verified"],
    "constraints": {
      "include_opt_out_instructions": true,
      "primary_cta": "book_tour"
    }
  },
  "thresholds": {
    "p95_latency_ms": 2000,
    "personalization_score_min": 0.85,
    "safety_violations_max": 0
  },
  "expected": {
    "next_message": {
      "channel": "sms",
      "body": "Hi Taylor—welcome to Oak Ridge! ... Reply STOP to opt out.",
      "cta": {"type": "schedule_tour"}
    },
    "next_action": {
      "type": "start_cadence"
    }
  }
}
```

## Evaluation Report Structure

### Report Sections

1. **Summary**: Overall pass/fail/warning counts
2. **Per-Task Details**:
   - Output Match Checks (✓/⚠/✗)
   - Threshold Checks with actual vs expected
   - Assertion validations
   - Constraint checks
   - Quality scores

### Status Levels

- ✅ **Passed**: All checks passed
- ⚠️ **Passed with Warnings**: Passed but some warnings (non-critical issues)
- ❌ **Failed**: One or more critical checks failed

### Example Report Output

```
================================================================================
EVALUATION REPORT
================================================================================

Total Tasks: 5
✅ Passed: 3
⚠️  Passed with Warnings: 1
❌ Failed: 1

--------------------------------------------------------------------------------
✅ Task: prospect_welcome_day0 (PASSED)
--------------------------------------------------------------------------------

📋 Output Match Checks:
  ✓ Channel: expected 'sms', got 'sms'
  ✓ Body similarity: 98.50%
  ✓ CTA type: expected 'schedule_tour', got 'schedule_tour'

⏱️  Threshold Checks:
  ✓ Latency: 1850ms (threshold: 2000ms)
  ✓ Personalization: 0.90 (min: 0.85)

⚖️  Constraint Checks:
  ✓ SMS opt-out instruction: STOP found

📊 Scores:
  • body_similarity: 98.50%
  • personalization_score: 90.00%
  • locale_accuracy: 100.00%
```

## Understanding Metrics

### Personalization Score Calculation

The system checks for:
- ✅ First name usage in message
- ✅ Amenity interests mentioned (pool, fitness, etc.)
- ✅ Unit number (for residents)
- ✅ City/location references

Score = (Points Earned / Total Possible Points)

### Locale Accuracy

For non-English messages (e.g., Spanish):
- Counts language-specific keywords
- Validates against total word count
- Score = (Spanish Words / (Total Words * 0.3))

### Body Similarity

Uses `SequenceMatcher` to calculate text similarity:
- 100% = Exact match
- 85%+ = Passed (high similarity)
- 70-85% = Warning (acceptable variance)
- <70% = Failed (too different)

## Programmatic Usage

```python
from eval_runner import EvalRunner

# Initialize
eval_runner = EvalRunner()

# Run evaluation
findings = eval_runner.run_eval(
    eval_record=eval_record,
    agent_output=agent_output,
    metrics={
        "latency_ms": 1500,
        "personalization_score": 0.9,
        "locale_accuracy": 1.0,
        "safety_violations": 0
    }
)

# Generate report
report_text = eval_runner.generate_report([findings])
print(report_text)

# Check status
if findings["overall_status"] == "passed":
    print("✅ Test passed!")
```

## Extending the Eval Runner

### Adding New Checks

To add custom validation checks, extend the `EvalRunner` class:

```python
def _validate_custom_constraint(self, constraints, output):
    checks = []
    
    # Your custom logic here
    if constraints.get("my_constraint"):
        result = self._check_something(output)
        checks.append({
            "name": "my_custom_check",
            "status": "passed" if result else "failed",
            "message": f"Custom check: {result}"
        })
    
    return checks
```

### Adding New Metrics

Add new score calculations in `_calculate_scores()`:

```python
def _calculate_scores(self, expected, actual, eval_record):
    scores = {}
    
    # Your new metric
    scores["my_metric"] = self._calculate_my_metric(actual)
    
    return scores
```

## Best Practices

1. **Define Clear Thresholds**: Set realistic latency and quality thresholds
2. **Include Edge Cases**: Test opt-out scenarios, no-consent cases, etc.
3. **Validate Locales**: Test multiple languages if supporting internationalization
4. **Check Constraints**: Always validate opt-out instructions and consent
5. **Monitor Personalization**: Ensure profile data is being used appropriately

## Troubleshooting

### High Latency Failures

If tests consistently fail latency thresholds:
- Check if API rate limits are being hit
- Consider using a faster model (e.g., `gpt-4o-mini` instead of `gpt-4o`)
- Optimize tool calls and reduce reasoning steps

### Low Personalization Scores

If personalization scores are low:
- Verify profile data is being passed correctly
- Check if the agent prompt emphasizes personalization
- Ensure tools provide necessary context

### Locale Issues

For language/locale problems:
- Verify `language` field in input data
- Check if system prompt includes locale instructions
- Validate that language-specific keywords appear in output

## API Reference

### `EvalRunner.run_eval()`

```python
def run_eval(
    eval_record: Dict[str, Any],
    agent_output: Dict[str, Any],
    metrics: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Runs comprehensive evaluation on a single task.
    
    Args:
        eval_record: Eval record with expected output and thresholds
        agent_output: Actual output from the agent
        metrics: Performance metrics (latency, scores, etc.)
    
    Returns:
        Dict with evaluation findings
    """
```

### `EvalRunner.generate_report()`

```python
def generate_report(findings_list: List[Dict]) -> str:
    """
    Generates human-readable report from evaluation findings.
    
    Args:
        findings_list: List of evaluation findings from run_eval()
    
    Returns:
        Formatted text report
    """
```

## License

Part of the EDD (Event-Driven Decision) Agent project.
