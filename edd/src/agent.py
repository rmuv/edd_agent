import json
import logging
import time
import random
import os
import tiktoken
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    HumanMessage,
    ToolMessage,
    AIMessage,
)
from .tools import verify_channel_consent, check_compliance_rules, get_current_time
from .validation import validate_response
from .tracing import TraceLogger

# Configure logger
logger = logging.getLogger(__name__)


class AutonomousAgent:
    def __init__(self):
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY is required.")

        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.tools = [verify_channel_consent, check_compliance_rules, get_current_time]
        self.tool_map = {t.name: t for t in self.tools}
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        self.tracer = TraceLogger()
        self.encoder = tiktoken.encoding_for_model("gpt-4o")

        self.system_prompt = """You are an Autonomous Messaging Orchestrator for a Property Management System.

Your goal is to process a "Task" (an eval record) and determine the correct message to send, the channel to use, and the next action to take.

### CORE RESPONSIBILITIES:
1. **Analyze** the input user profile, lifecycle stage, and task constraints.
2. **Verify Request**: Use tools to check consent and compliance. NEVER guess about consent.
3. **Decide Channel**: 
   - Prioritize user preferences BUT ONLY if consent is GRANTED.
   - If preferred channel is DENIED, allow fallback to other consented channels.
   - If NO channels are allowed, do not send a message.
4. **Draft Message**: 
   - Personalize using the profile data (First Namem , Unit, etc.).
   - Adhere strictly to tone (Professional yet friendly).
   - MUST include Opt-out instructions (STOP for SMS, link/text for Email).
5. **Output**: Produce a FINAL JSON response representing the decision.

### OPERATIONAL RULES:
- You operate in a loop: THOUGHT -> ACTION -> OBSERVATION.
- **THOUGHT**: Reason about what you know and what you need to verify.
- **ACTION**: Call a tool (like `verify_channel_consent`) to get facts.
- **OBSERVATION**: Read the tool output.
- When you have sufficient info, output the FINAL ANSWER.

### FORMAT FOR FINAL ANSWER:
You must output a single valid JSON block at the very end of your conversation matching this structure:
```json
{
  "next_message": {
    "channel": "sms|email",
    "send_at": "ISO-8601-TIMESTAMP",
    "subject": "Email Subject or null",
    "body": "The full message body",
    "cta": { "type": "...", "options": [...] or "link": "..." }
  },
  "next_action": {
    "type": "..."
  }
}
```
"""

    def run_with_retries(
        self, eval_record: Dict[str, Any], max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Attempts to solve the task up to `max_retries` times.
        """
        task_id = eval_record.get("task_id")
        logger.info(f"🚀 Starting Task: {task_id} (Max Retries: {max_retries})")

        # Start Trace
        self.tracer.start_trace(task_id, input_data=eval_record)

        last_error = None
        last_output = None

        for attempt in range(1, max_retries + 1):
            logger.info(f"--- Attempt {attempt}/{max_retries} for Task {task_id} ---")

            # We no longer log "step" here directly, but could add context to input if needed
            # self.tracer.log_step("thought", f"Starting Attempt {attempt}...")

            try:
                # 1. Execute ReAct Loop
                output = self._execute_react_loop(
                    eval_record, attempt_context=last_error
                )
                last_output = output

                if not output:
                    msg = "Agent failed to produce JSON output."
                    raise ValueError(msg)

                # 2. Validate
                expected = eval_record.get("expected", {})
                validation_errors = validate_response(expected, output)

                if not validation_errors:
                    logger.info(f"   ✅ Attempt {attempt} Succeeded!")
                    self.tracer.save_trace()
                    return output
                else:
                    error_msg = f"Validation Failed: {'; '.join(validation_errors)}"
                    logger.warning(f"   ❌ Attempt {attempt} Failed: {error_msg}")
                    last_error = error_msg

            except Exception as e:
                logger.error(f"   ❌ Attempt {attempt} Crashed: {str(e)}")
                last_error = f"Runtime Error: {str(e)}"

            # Delay before retry
            if attempt < max_retries:
                delay = 2 * attempt
                time.sleep(delay)

        logger.error(f"❌ All {max_retries} attempts failed for Task {task_id}")
        self.tracer.save_trace()
        return last_output

    def _execute_react_loop(
        self, eval_record: Dict[str, Any], attempt_context: str = None
    ) -> Optional[Dict]:
        """Core ReAct loop"""
        messages: List[BaseMessage] = [SystemMessage(content=self.system_prompt)]

        user_content = (
            f"Please process this Task Record:\n{json.dumps(eval_record, indent=2)}"
        )
        if attempt_context:
            user_content += f"\n\n🚨 PREVIOUS ATTEMPT FAILED. Errors:\n{attempt_context}\n\nPlease fix these issues in this new attempt."

        messages.append(HumanMessage(content=user_content))

        max_steps = 10
        for step in range(max_steps):

            step_start_time = time.time()

            # --- TOKEN COUNTING (Pre-Call) ---
            breakdown, total_prompt_tokens = self._calculate_context_tokens(messages)

            # Invoke LLM
            response = self._invoke_with_backoff(self.llm_with_tools, messages)
            messages.append(response)

            llm_end_time = time.time()
            llm_latency = llm_end_time - step_start_time

            # --- TOKEN USAGE ---
            usage = response.response_metadata.get("token_usage", {})
            prompt_tokens = usage.get("prompt_tokens", total_prompt_tokens)
            completion_tokens = usage.get("completion_tokens", 0)

            # Prepare Token Stats for this Turn
            token_stats = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "total_context": prompt_tokens,  # Synonymous here
                "breakdown": breakdown,
            }

            executed_tools = []

            # Check for Tool Calls
            if response.tool_calls:
                logger.info(
                    f"   Step {step+1}: Agent requested tools: {[tc['name'] for tc in response.tool_calls]}"
                )

                for tool_call in response.tool_calls:
                    tool_start = time.time()
                    tool_result = "Error: Tool not found"
                    try:
                        tool_func = self.tool_map.get(tool_call["name"])
                        if tool_func:
                            tool_result = tool_func.invoke(tool_call["args"])
                    except Exception as e:
                        tool_result = f"Error: {str(e)}"

                    tool_latency = time.time() - tool_start

                    # Add to executed list
                    executed_tools.append(
                        {
                            "name": tool_call["name"],
                            "args": tool_call["args"],
                            "output": str(tool_result),
                            "latency_s": tool_latency,
                        }
                    )

                    # Add to history
                    messages.append(
                        ToolMessage(
                            content=str(tool_result), tool_call_id=tool_call["id"]
                        )
                    )

            # Calculate Total Turn Latency (LLM + Tools)
            turn_latency = time.time() - step_start_time

            # Log formatted Turn
            self.tracer.log_turn(
                {
                    "turn_id": step + 1,
                    "latency_s": turn_latency,
                    "ai_content": response.content,
                    "tool_calls": executed_tools,
                    "token_stats": token_stats,
                }
            )

            # Check for JSON in response (Final Answer)
            content = response.content or ""
            if "```json" in content:
                try:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                    blob = json.loads(json_str)
                    return blob
                except Exception as e:
                    logger.warning(f"Agent produced malformed JSON: {e}")
                    messages.append(HumanMessage(content=f"Invalid JSON: {e}"))
            elif step == max_steps - 1:
                logger.error("Max steps reached without output.")

        return None

    def _invoke_with_backoff(self, runnable, input_data, max_retries=5):
        """Exponential backoff helper"""
        delay = 1
        for attempt in range(max_retries):
            try:
                return runnable.invoke(input_data)
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "rate_limit" in error_str.lower():
                    if attempt == max_retries - 1:
                        raise e
                    sleep_time = delay + random.uniform(0, 1)
                    logger.warning(
                        f"⚠️ Rate limit hit. Retrying in {sleep_time:.2f}s..."
                    )
                    time.sleep(sleep_time)
                    delay *= 2
                else:
                    raise e

    def _calculate_context_tokens(self, messages: List[BaseMessage]):
        """Calculates token value for each message type in context."""
        breakdown = {
            "system": 0,
            "tools": 0,
            "human": 0,
            "ai": 0,
            "tool_call": 0,
            "tool_output": 0,
        }

        # 1. Tools Def (Estimating schema size)
        tools_schema = [
            t.args_schema.schema() if t.args_schema else {} for t in self.tools
        ]
        tools_str = json.dumps(tools_schema)
        breakdown["tools"] = len(self.encoder.encode(tools_str))

        # 2. Messages
        for msg in messages:
            content_str = str(msg.content)
            count = len(self.encoder.encode(content_str))

            if isinstance(msg, SystemMessage):
                breakdown["system"] += count
            elif isinstance(msg, HumanMessage):
                breakdown["human"] += count
            elif isinstance(msg, AIMessage):
                breakdown["ai"] += count
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        tc_str = json.dumps(tc)
                        breakdown["tool_call"] += len(self.encoder.encode(tc_str))

            elif isinstance(msg, ToolMessage):
                breakdown["tool_output"] += count

        total = sum(breakdown.values())
        return breakdown, total
