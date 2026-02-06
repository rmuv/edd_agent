# EDD - Eval-Driven Development Agent

An autonomous LangGraph agent that processes multi-channel messaging evals for property management communication.

## Overview

This agent implements **Eval-Driven Development (EDD)** - a methodology where the agent reads evaluation records and autonomously determines the correct behavior to match expected outputs.

### What the Agent Does

The agent processes each eval record and:

1. **Verifies Consent** - Ensures the person has opted in to the selected channel
2. **Selects Channel** - Chooses SMS, email, or voice based on preferences and consent
3. **Composes Messages** - Creates personalized messages with:
   - First name personalization
   - Property-specific context
   - Opt-out instructions (STOP for SMS, unsubscribe for email)
   - Appropriate CTAs (call-to-action)
   - Language/locale support
4. **Handles Special Cases**:
   - Fallback when preferred channel lacks consent
   - No-contact scenarios (all channels opted out)
   - Spanish locale support
   - Fair housing compliance
5. **Validates Output** - Compares generated output against expected results
### test
## Architecture

The agent is built using a **ReAct-style Autonomous Orchestrator** pattern:

```
[Eval Record] -> (Think) -> (Act: Check Consent/Rules) -> (Observe) -> [Final Decision]
```

### Components

1.  **Core Orchestrator (`AutonomousAgent`)**:
    - Maintains conversation history (Memory).
    - Uses a robust **System Prompt** to define behavior and rules.
    - Executes a "Thought -> Action -> Observation" loop.

2.  **Tools**:
    - `verify_channel_consent`: Checks if the user allowed a specific channel.
    - 'check_compliance_rules`: Validates message content against Fair Housing and strict Opt-out rules.
    - `get_current_time`: Provides timezone-aware timestamps.

3.  **Validation**:
    - The agent's final JSON output is strictly validated against the expected results in the eval file to ensure accuracy.

## Eval Records

Each eval in `evals.jsonl` contains:

- **task_id**: Unique identifier
- **persona**: prospect or resident
- **lifecycle_stage**: new, open, no_show, renewal_window, etc.
- **consent**: Email, SMS, voice opt-in status
- **channel_preferences**: Ordered list of preferred channels
- **input**: Context data (property, dates, profile, etc.)
- **assertions**: Required states and constraints
- **thresholds**: Performance requirements
- **expected**: Expected output to validate against

## Observability

The agent includes a built-in **Trace Visualizer**.

Each run generates:

- JSON traces for each task in `logs/trace_*.json`.
- A consolidated HTML report at `logs/trace_report.html`.

You can open `logs/trace_report.html` in your browser to see the step-by-step reasoning, tool calls, and final outputs for every test case.

## 📁 Project Structure

```
projects/edd/
├── src/
│   ├── agent.py            # AutonomousAgent class
│   ├── tools.py            # Tool definitions
│   ├── validation.py       # Validation logic
│   └── tracing.py          # HTML trace generator
│
├── docs/                   # Documentation
│   ├── QUICKSTART.md
│   ├── SUMMARY.md
│   └── INDEX.md
│
├── output/                 # Generated artifacts (Ignored in git)
│   ├── results_orchestrator.json
│   └── logs/               # Trace reports
│
├── main.py                 # Entry point
├── evals.jsonl             # Test cases
├── requirements.txt        # Dependencies
└── README.md               # Main docs
```

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set OpenAI API key
export OPENAI_API_KEY=""
```

## Usage

```bash
# Run all evals
python edd.py
```

The agent will:

1. Load all 9 eval records
2. Process each one through the graph
3. Validate outputs against expected results
4. Generate a summary report
5. Save results to `results.json`

## Example Output

```json
{
  "task_id": "prospect_welcome_day0",
  "status": "success",
  "next_message": {
    "channel": "sms",
    "send_at": "2025-12-09T09:00:00-06:00",
    "subject": null,
    "body": "Hi Taylor—welcome to Oak Ridge! Tours are available this week. Would you like to book a time on Thursday or Friday? Reply 1 for Thu, 2 for Fri. Reply STOP to opt out.",
    "cta": {
      "type": "schedule_tour",
      "options": ["Thu", "Fri"]
    }
  },
  "next_action": {
    "type": "start_cadence",
    "name": "prospect_welcome_short_horizon"
  },
  "validation": {
    "passed": true,
    "errors": []
  }
}
```

## Key Features

### 🔒 Consent Management

- Respects opt-out preferences
- Never sends to channels without consent
- Automatic fallback to consented channels

### 📡 Channel Selection

- Priority-based selection (preferences + consent)
- Intelligent fallback logic
- Handles "no contact" scenarios

### ✍️ Message Composition

- LLM-powered personalization
- Opt-out instructions included
- Channel-appropriate formatting
- Fair housing compliant

### ✅ Validation

- Compares output to expected results
- Validates consent, channel, message structure
- Checks for opt-out instructions
- Ensures CTA is present

## Eval Scenarios

The 9 evals cover:

1. **Prospect Welcome** (Day 0, SMS preferred)
2. **Long Horizon Follow-up** (Day 3, email fallback due to no SMS consent)
3. **No-Show Re-engagement** (SMS)
4. **Cancellation Cross-sell** (Email only)
5. **Consent Block Fallback** (SMS → Email fallback)
6. **Resident Renewal** (90-day notice, email)
7. **Renewal Follow-up** (SMS, intent capture)
8. **Resident Welcome** (Email)
9. **Loyalty Engagement** (Email)

## Success Criteria

The agent passes an eval when:

- ✅ Correct channel selected
- ✅ Message includes personalization
- ✅ Opt-out instructions present
- ✅ Appropriate CTA included
- ✅ Consent respected
- ✅ Fair housing compliant

## Future Enhancements

- [ ] Spanish language support
- [ ] A/B testing framework
- [ ] Sentiment analysis
- [ ] Multi-turn conversations
- [ ] Voice channel implementation
- [ ] Real-time scheduling optimization

## License

MIT
