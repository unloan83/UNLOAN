import json
from pathlib import Path
from typing import List, Dict, Any


class LocalStorageService:
    def __init__(self, file_path: str):
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def save(self, record: Dict[str, Any]) -> None:
        records = self.list_all()
        records.append(record)
        self.path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    def list_all(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return []
