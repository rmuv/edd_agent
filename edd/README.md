# EDD Agent - Complete Evaluation Framework

## Overview

This project contains a comprehensive evaluation framework for testing an autonomous agent that generates personalized property management messages.

## 📁 Project Structure

```
edd/
├── main.py                      # Main agent runner with integrated evaluation
├── eval_runner.py               # Comprehensive evaluation framework
├── run_eval_only.py             # Standalone evaluation (no agent re-run)
├── compare_outputs.py           # Output comparison tool
├── evals.jsonl                  # Evaluation test cases
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (API keys)
├── EVAL_RUNNER_README.md        # Detailed eval runner documentation
│
├── src/
│   ├── agent.py                 # Agent logic (ReAct loop)
│   ├── tools.py                 # Agent tools (consent, compliance, time)
│   ├── validation.py            # Basic validation functions
│   └── tracing.py               # Execution tracing and HTML report generation
│
└── output/
    ├── results_orchestrator.json    # Full agent outputs
    ├── eval_report.txt              # Human-readable evaluation report
    ├── eval_findings.json           # Structured evaluation findings
    └── logs/
        ├── trace_*.json             # Per-task execution traces
        └── trace_report.html        # Visual trace report
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Activate virtual environment
source venv/bin/activate

# Verify installation
python --version  # Should be Python 3.12+
```

### 2. Configure API Keys

Edit `.env` file:
```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini  # or gpt-4o for better quality
```

### 3. Run Agent with Evaluation

```bash
# Run all eval tasks with comprehensive evaluation
python main.py
```

This will:
- ✅ Execute the agent on all tasks in `evals.jsonl`
- ✅ Validate outputs against expected results
- ✅ Check thresholds (latency, personalization, locale)
- ✅ Generate detailed reports

## 🛠️ Available Tools

### 1. Main Agent Runner (`main.py`)

Runs the agent and performs comprehensive evaluation.

```bash
python main.py
```

**Outputs:**
- `output/results_orchestrator.json` - Complete results
- `output/eval_report.txt` - Human-readable report
- `output/eval_findings.json` - Structured findings
- `output/logs/trace_report.html` - Visual trace

### 2. Standalone Evaluation (`run_eval_only.py`)

Re-evaluate existing results without re-running the agent.

```bash
# Evaluate existing results
python run_eval_only.py

# Custom paths
python run_eval_only.py --results output/results_orchestrator.json --evals evals.jsonl
```

**Use Cases:**
- Re-run evaluation after changing thresholds
- Quick validation of outputs
- Batch evaluation of multiple result files

### 3. Output Comparison (`compare_outputs.py`)

Side-by-side comparison of expected vs actual outputs.

```bash
# Summary of all tasks
python compare_outputs.py

# Detailed comparison for specific task
python compare_outputs.py --task prospect_welcome_day0
```

**Shows:**
- Channel, subject, body comparison
- Similarity scores
- Text diffs
- CTA and next action validation

## 📊 Evaluation Framework

### What Gets Checked?

#### 1. **Output Match Validation**
- ✅ Channel (SMS/Email/none)
- ✅ Subject line (emails)
- ✅ Message body similarity
- ✅ CTA type
- ✅ Next action

#### 2. **Threshold Validation**
- ⏱️ `p95_latency_ms` - Response time
- 🎯 `personalization_score_min` - Quality threshold
- 🌍 `locale_accuracy_min` - Language validation
- 🛡️ `safety_violations_max` - Safety checks

#### 3. **Assertion Validation**
- 🔒 Consent verified
- ⚖️ Fair housing compliance
- 🎨 Brand style applied
- 📋 Required data loaded

#### 4. **Constraint Validation**
- 📧 Opt-out instructions (STOP for SMS)
- 🌐 Locale/language matching
- 🚫 Consent respect
- 🎯 Primary CTA

### Evaluation Status Levels

- ✅ **Passed** - All checks passed
- ⚠️ **Passed with Warnings** - Passed with minor issues
- ❌ **Failed** - One or more critical failures

## 📝 Adding New Evaluation Cases

### 1. Add to `evals.jsonl`

```json
{
  "task_id": "your_new_test",
  "persona": "prospect",
  "consent": {
    "email_opt_in": true,
    "sms_opt_in": true
  },
  "channel_preferences": ["sms"],
  "input": {
    "property_name": "Your Property",
    "language": "en",
    "profile": {
      "first_name": "John"
    }
  },
  "assertions": {
    "required_states": ["consent_verified"],
    "constraints": {
      "include_opt_out_instructions": true
    }
  },
  "thresholds": {
    "p95_latency_ms": 2000,
    "personalization_score_min": 0.8
  },
  "expected": {
    "next_message": {
      "channel": "sms",
      "body": "Expected message text...",
      "cta": {"type": "schedule_tour"}
    },
    "next_action": {
      "type": "follow_up_in_days",
      "value": 2
    }
  }
}
```

### 2. Run Evaluation

```bash
python main.py
```

## 🔧 Customizing the Agent

### Update System Prompt

Edit `src/agent.py`:

```python
self.system_prompt = """Your custom prompt here..."""
```

### Add New Tools

1. Define tool in `src/tools.py`:

```python
@tool
def your_new_tool(param: str) -> str:
    """Tool description."""
    # Your logic here
    return result
```

2. Register in `src/agent.py`:

```python
self.tools = [
    verify_channel_consent,
    check_compliance_rules,
    get_current_time,
    your_new_tool  # Add here
]
```

## 📈 Understanding Results

### Evaluation Report Structure

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

⏱️  Threshold Checks:
  ✓ Latency: 1850ms (threshold: 2000ms)

📊 Scores:
  • body_similarity: 98.50%
  • personalization_score: 90.00%
```

### Common Issues & Solutions

#### High Latency

**Problem:** Tasks failing latency thresholds

**Solutions:**
- Use `gpt-4o-mini` instead of `gpt-4o`
- Reduce number of tool calls
- Optimize system prompt
- Check API rate limits

#### Low Personalization Scores

**Problem:** `personalization_score` below threshold

**Solutions:**
- Ensure profile data is in input
- Update prompt to emphasize personalization
- Verify tools return necessary context

#### Locale/Language Issues

**Problem:** Wrong language in output

**Solutions:**
- Check `language` field in input
- Add explicit language instruction in prompt
- Validate language-specific keywords

## 🧪 Testing Workflow

### 1. Development Testing

```bash
# Run agent
python main.py

# Check report
cat output/eval_report.txt

# Compare specific task
python compare_outputs.py --task prospect_welcome_day0
```

### 2. CI/CD Integration

```bash
# Run and check exit code
python main.py && python run_eval_only.py

# Parse JSON results
cat output/eval_findings.json | jq '.[] | select(.overall_status != "passed")'
```

### 3. Regression Testing

```bash
# Save baseline
cp output/results_orchestrator.json baseline_results.json

# After changes, compare
python run_eval_only.py --results baseline_results.json
python run_eval_only.py --results output/results_orchestrator.json
```

## 📚 Additional Resources

- **Eval Runner Details:** See `EVAL_RUNNER_README.md`
- **Agent Logic:** See `src/agent.py`
- **Tool Definitions:** See `src/tools.py`
- **Tracing System:** See `src/tracing.py`

## 🤝 Contributing

When adding new features:

1. Update `evals.jsonl` with test cases
2. Run full evaluation suite
3. Update documentation
4. Check all reports pass

## 📄 License

Part of the EDD (Event-Driven Decision) Agent project.
