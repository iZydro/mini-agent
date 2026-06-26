import json
import os
from datetime import datetime


class Transcript:
    def __init__(self, base_dir="data/conversations"):
        os.makedirs(base_dir, exist_ok=True)

        date = datetime.now().strftime("%Y-%m-%d")
        self.path = os.path.join(base_dir, f"{date}.jsonl")

    def write(self, event_type, data):
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data
        }

        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")