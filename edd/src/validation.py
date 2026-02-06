from typing import Dict, List


def validate_response(expected: Dict, actual: Dict) -> List[str]:
    """Compare critical fields between expected and actual output."""
    errors = []

    # Safe retrieval
    exp_msg = expected.get("next_message", {}) or {}
    act_msg = actual.get("next_message", {}) or {}

    # 1. Channel Validation
    if exp_msg.get("channel") != act_msg.get("channel"):
        errors.append(
            f"Channel mismatch: Expected '{exp_msg.get('channel')}', got '{act_msg.get('channel')}'"
        )

    # 2. Opt-out Instruction Validation
    body = (act_msg.get("body") or "").lower()
    channel = act_msg.get("channel")

    if channel == "sms" and "stop" not in body:
        errors.append("SMS missing opt-out 'STOP'")

    if channel == "email":
        has_opt_out = any(
            phrase in body for phrase in ["opt", "unsubscribe", "reply stop"]
        )
        if not has_opt_out:
            errors.append("Email missing opt-out instructions")

    return errors
