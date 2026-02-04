import json
from datetime import datetime
from zoneinfo import ZoneInfo
from langchain_core.tools import tool


@tool
def verify_channel_consent(channel: str, consent_record: str) -> str:
    """
    Verifies if a specific channel has opt-in consent based on the record.

    Args:
        channel: 'email', 'sms', or 'voice'
        consent_record: JSON string of the consent object e.g. '{"email_opt_in": true...}'
    """
    try:
        data = json.loads(consent_record)
        key_map = {
            "email": "email_opt_in",
            "sms": "sms_opt_in",
            "voice": "voice_opt_in",
        }

        if channel not in key_map:
            return f"Error: Unknown channel '{channel}'"

        is_opted_in = data.get(key_map[channel], False)
        status = "GRANTED" if is_opted_in else "DENIED"
        return f"Consent for {channel}: {status}"
    except Exception as e:
        return f"Error verifying consent: {str(e)}"


@tool
def check_compliance_rules(message_body: str, channel: str) -> str:
    """
    Checks message content for regulatory compliance (Fair Housing, Opt-out).
    """
    issues = []
    body_lower = message_body.lower()

    # Check 1: Opt-out instructions
    if channel == "sms":
        if "stop" not in body_lower:
            issues.append("SMS must include 'STOP' for opt-out")
    elif channel == "email":
        if (
            "unsubscribe" not in body_lower
            and "opt" not in body_lower
            and "reply stop" not in body_lower
        ):
            issues.append("Email must include unsubscribe/opt-out instructions")

    # Check 2: Fair Housing (Basic keyword check)
    discriminatory_terms = [
        "adults only",
        "no children",
        "christian",
        "white",
        "bachelor",
    ]
    for term in discriminatory_terms:
        if term in body_lower:
            issues.append(f"Potential Fair Housing violation found: '{term}'")

    if not issues:
        return "Compliance Check: PASSED"
    else:
        return f"Compliance Check: FAILED. Issues: {'; '.join(issues)}"


@tool
def get_current_time(timezone: str) -> str:
    """Returns the current time in the specified timezone."""
    try:
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
        return now.isoformat()
    except Exception as e:
        return f"Error getting time: {str(e)}"
