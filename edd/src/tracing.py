import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any


class TraceLogger:
    def __init__(self, log_dir="output/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_trace = []

    def start_trace(self, task_id: str, input_data: Dict[str, Any] = None):
        self.current_trace = {
            "task_id": task_id,
            "start_time": datetime.now().isoformat(),
            "input_data": input_data,
            "steps": [],
            "token_stats": [],
        }

    def log_turn(self, turn_data: Dict[str, Any]):
        """
        Logs a full turn of execution.
        turn_data structure:
        {
            "turn_id": 1,
            "latency_ms": 1200,
            "ai_content": "...",
            "tool_calls": [
                {"name": "...", "args": {...}, "output": "...", "latency_ms": 300}
            ],
            "token_stats": { ... }
        }
        """
        self.current_trace["steps"].append(
            {
                "type": "turn",
                "timestamp": datetime.now().isoformat(),
                "content": turn_data,
            }
        )

    def save_trace(self):
        if not self.current_trace:
            return

        task_id = self.current_trace["task_id"]
        filename = self.log_dir / f"trace_{task_id}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.current_trace, f, indent=2, default=str)

        self.generate_html_report()

    def generate_html_report(self):
        """Generates a consolidated HTML report of all traces."""
        traces = []
        for f in self.log_dir.glob("trace_*.json"):
            try:
                traces.append(json.loads(f.read_text(encoding="utf-8")))
            except:
                continue

        # Sort by start time newest first
        traces.sort(key=lambda x: x["start_time"], reverse=True)

        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; padding: 20px; background: #f0f2f5; color: #1c1e21; }
                h1 { color: #333; text-align: center; }
                
                details.trace-card { 
                    background: white; margin-bottom: 20px; border-radius: 8px; 
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid #e0e0e0;
                    overflow: hidden;
                }
                details.trace-card > summary {
                    padding: 15px; background: #fff; cursor: pointer; font-weight: 600;
                    display: flex; justify-content: space-between; align-items: center;
                }
                details.trace-card > summary:hover { background: #f8f9fa; }
                
                .turn-container { 
                    border: 1px solid #e0e0e0; 
                    border-radius: 6px; 
                    margin: 10px 15px; 
                    padding: 15px; 
                    background: #fff;
                }
                .turn-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 8px; }
                .turn-title { font-weight: bold; color: #1976D2; font-size: 15px; }
                .turn-latency { font-size: 12px; color: #666; background: #f5f5f5; padding: 2px 8px; border-radius: 12px; border: 1px solid #ddd; }
                
                .ai-content { background: #E3F2FD; padding: 12px; border-radius: 6px; margin-bottom: 10px; white-space: pre-wrap; font-size: 13px; border: 1px solid #BBDEFB; color: #0D47A1; }
                
                .tools-section { margin-top: 15px; border-top: 1px dashed #ddd; padding-top: 10px; }
                .tools-title { font-size: 12px; font-weight: bold; color: #555; text-transform: uppercase; margin-bottom: 8px; }
                
                .tool-item { background: #FFF3E0; border: 1px solid #FFCC80; border-radius: 6px; margin-bottom: 8px; overflow: hidden; }
                .tool-header { padding: 6px 10px; background: #FFE0B2; font-size: 12px; font-weight: bold; border-bottom: 1px solid #FFCC80; display: flex; justify-content: space-between; color: #E65100; }
                .tool-body { padding: 8px 10px; font-family: 'Consolas', monospace; font-size: 11px; color: #333; }
                
                .token-box { margin-top: 15px; padding: 10px; background: #FAFAFA; border-radius: 4px; border: 1px solid #EEEEEE; }
                .token-header { font-size: 11px; font-weight: bold; margin-bottom: 5px; color: #777; display: flex; justify-content: space-between; }
                
                .token-bar-container { height: 18px; display: flex; border-radius: 4px; overflow: hidden; background: #EEEEEE; margin-bottom: 5px; }
                .token-seg { height: 100%; display: flex; align-items: center; justify-content: center; color: white; font-size: 9px; font-weight: bold; overflow: hidden; }
                
                .input-data { margin: 10px 15px; padding: 10px; background: #263238; color: #ECEFF1; border-radius: 4px; font-family: 'Consolas', monospace; font-size: 11px; overflow-x: auto; }
                
                /* Colors for Token Breakdown */
                .bg-system { background-color: #607D8B; }
                .bg-tools { background-color: #795548; }
                .bg-human { background-color: #9C27B0; }
                .bg-ai { background-color: #2196F3; }
                .bg-tool-output { background-color: #4CAF50; }
                .bg-tool-call { background-color: #FF9800; }
                
                .legend { display: flex; gap: 10px; font-size: 10px; color: #666; margin-top: 5px; flex-wrap: wrap; }
                .legend-item { display: flex; align-items: center; gap: 4px; }
                .legend-box { width: 8px; height: 8px; border-radius: 2px; }

            </style>
        </head>
        <body>
            <h1>🤖 Agent Execution Traces</h1>
        """

        for t in traces:
            start_iso = t["start_time"]
            total_latency_str = "?"

            # Simple latency calc
            try:
                start_dt = datetime.fromisoformat(start_iso)
                if t.get("steps"):
                    last_step = t["steps"][-1]
                    end_iso = last_step.get("timestamp", start_iso)
                    end_dt = datetime.fromisoformat(end_iso)
                    total_latency = (end_dt - start_dt).total_seconds()
                    total_latency_str = f"{total_latency:.2f}s"
            except:
                pass

            html += f"""
            <details class='trace-card' open>
                <summary>
                    <span style="font-size: 16px;">{t.get('task_id', 'Unknown Task')}</span>
                    <span style="color: #666; font-size: 13px;">Total Latency: <strong>{total_latency_str}</strong></span>
                </summary>
                
                <!-- Input Data View -->
                <details>
                    <summary style="margin: 0 15px; padding: 10px 0; font-size: 12px; color: #78909C; cursor: pointer; outline: none;">▶ View Task Input</summary>
                    <div class="input-data"><pre>{json.dumps(t.get('input_data', {}), indent=2)}</pre></div>
                </details>
            """

            # Process "Turn" Steps
            for step in t.get("steps", []):
                if step["type"] != "turn":
                    continue

                data = step["content"]
                turn_id = data.get("turn_id", "?")
                latency_s = data.get("latency_s", 0)
                ai_text = data.get("ai_content", "")
                tools = data.get("tool_calls", [])
                tokens = data.get("token_stats", {})

                html += f"""
                <div class='turn-container'>
                    <div class='turn-header'>
                        <span class='turn-title'>Step {turn_id}: LLM Call</span>
                        <span class='turn-latency'>⏱ {latency_s:.2f}s</span>
                    </div>
                """

                if ai_text:
                    html += f"<div class='ai-content'>{ai_text}</div>"

                if tools:
                    html += """
                    <div class='tools-section'>
                        <div class='tools-title'>Sub-steps: Tool Calls</div>
                    """
                    for tool in tools:
                        t_lat = tool.get("latency_s", 0)
                        html += f"""
                        <div class='tool-item'>
                            <div class='tool-header'>
                                <span>🛠 {tool['name']}</span>
                                <span>{t_lat:.3f}s</span>
                            </div>
                            <div class='tool-body'>
                                <div><strong>Args:</strong> {json.dumps(tool.get('args', {}))}</div>
                                <div style='margin-top:4px; border-top:1px dotted #FFCC80; padding-top:4px;'><strong>Result:</strong> {str(tool.get('output', ''))[:300]}</div>
                            </div>
                        </div>
                        """
                    html += "</div>"

                # Token Viz for this turn
                if tokens:
                    breakdown = tokens.get("breakdown", {})
                    total_ctx = tokens.get("total_context", 0)

                    if total_ctx > 0:
                        colors = {
                            "system": "#607D8B",
                            "tools": "#795548",
                            "human": "#9C27B0",
                            "ai": "#2196F3",
                            "tool_output": "#4CAF50",
                            "tool_call": "#FF9800",
                        }

                        html += f"""
                        <div class='token-box'>
                            <div class='token-header'>
                                <span>Context Window Utilization</span>
                                <span><strong>{total_ctx}</strong> / 128,000 tokens ({(total_ctx/128000*100):.1f}%)</span>
                            </div>
                            <div class='token-bar-container'>
                        """

                        for k, v in breakdown.items():
                            if v > 0:
                                pct = (v / total_ctx) * 100
                                c = colors.get(k, "#ccc")
                                title = f"{k}: {v} ({pct:.1f}%)"
                                # Only show text if segment is wide enough
                                label = str(v) if pct > 5 else ""
                                html += f"<div class='token-seg' style='width:{pct}%; background-color:{c}' title='{title}'>{label}</div>"
                        html += "</div>"

                        # Legend
                        html += "<div class='legend'>"
                        for k, v in breakdown.items():
                            if v > 0:
                                c = colors.get(k, "#ccc")
                                html += f"<div class='legend-item'><div class='legend-box' style='background:{c}'></div>{k}: {v}</div>"
                        html += "</div></div>"

                html += "</div>"  # Close turn-container

            html += "</details>"

        html += "</body></html>"
        (self.log_dir / "trace_report.html").write_text(html, encoding="utf-8")
