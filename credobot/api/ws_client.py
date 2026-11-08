"""Lightweight CLI client for testing the WebSocket chat endpoint."""
import argparse
import json
import sys
from websockets.sync.client import connect


def main() -> int:
    parser = argparse.ArgumentParser(description="CredoBot WebSocket chat client.")
    parser.add_argument(
        "--url",
        default="ws://127.0.0.1:8000/ws/chat",
        help="WebSocket endpoint URL.",
    )
    parser.add_argument(
        "--session",
        default="demo",
        help="Session identifier for multi-turn conversational context.",
    )
    args = parser.parse_args()

    full_url = f"{args.url}?session_id={args.session}"
    print(f"Connecting to {full_url} ... (Type 'exit' to quit)")

    try:
        with connect(full_url) as ws:
            print("Connected! Enter your loan support questions:")
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                if line.lower() in ("exit", "quit"):
                    break
                ws.send(json.dumps({"query": line}))
                reply = ws.recv()
                try:
                    data = json.loads(reply)
                    print(json.dumps(data, indent=2))
                except Exception:
                    print(reply)
    except Exception as exc:
        print(f"Connection error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

