import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from threading import Lock

from app.config import SETTINGS_FILE, DOWNLOADS_DIR
from app.models.rule import Rule, RuleCreate, RuleUpdate


class RuleRepository:
    def __init__(self, settings_path: Optional[Path] = None):
        self.settings_path = settings_path or SETTINGS_FILE
        self._lock = Lock()
        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        with self._lock:
            if not self.settings_path.exists():
                self.settings_path.parent.mkdir(parents=True, exist_ok=True)
                initial_data = {
                    "destination_path": str(DOWNLOADS_DIR.resolve()),
                    "rules": []
                }
                with open(self.settings_path, "w", encoding="utf-8") as f:
                    json.dump(initial_data, f, indent=2, ensure_ascii=False)
            else:
                try:
                    with open(self.settings_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if "destination_path" not in data or not data["destination_path"]:
                        data["destination_path"] = str(DOWNLOADS_DIR.resolve())
                        with open(self.settings_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                except Exception:
                    initial_data = {
                        "destination_path": str(DOWNLOADS_DIR.resolve()),
                        "rules": []
                    }
                    with open(self.settings_path, "w", encoding="utf-8") as f:
                        json.dump(initial_data, f, indent=2, ensure_ascii=False)

    def _load_data(self) -> dict:
        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"destination_path": str(DOWNLOADS_DIR.resolve()), "rules": []}

    def _save_data(self, data: dict) -> None:
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_destination_path(self) -> str:
        with self._lock:
            data = self._load_data()
            path = data.get("destination_path", "")
            if not path:
                path = str(DOWNLOADS_DIR.resolve())
            return path

    def set_destination_path(self, path: str) -> str:
        with self._lock:
            data = self._load_data()
            data["destination_path"] = path
            self._save_data(data)
            return path

    def list_rules(self) -> List[Rule]:
        with self._lock:
            data = self._load_data()
            rules_raw = data.get("rules", [])
            return [Rule(**r) for r in rules_raw]

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        with self._lock:
            data = self._load_data()
            for r in data.get("rules", []):
                if r.get("id") == rule_id:
                    return Rule(**r)
            return None

    def create_rule(self, rule_in: RuleCreate) -> Rule:
        with self._lock:
            data = self._load_data()
            now = datetime.now().isoformat()
            new_id = f"rule-{uuid.uuid4().hex[:8]}"
            rule_dict = rule_in.model_dump()
            rule_dict["id"] = new_id
            rule_dict["created_at"] = now
            rule_dict["updated_at"] = now
            
            rules = data.get("rules", [])
            rules.append(rule_dict)
            data["rules"] = rules
            self._save_data(data)
            return Rule(**rule_dict)

    def update_rule(self, rule_id: str, rule_in: RuleUpdate) -> Optional[Rule]:
        with self._lock:
            data = self._load_data()
            rules = data.get("rules", [])
            for idx, r in enumerate(rules):
                if r.get("id") == rule_id:
                    update_data = rule_in.model_dump(exclude_unset=True)
                    r.update(update_data)
                    r["updated_at"] = datetime.now().isoformat()
                    rules[idx] = r
                    data["rules"] = rules
                    self._save_data(data)
                    return Rule(**r)
            return None

    def delete_rule(self, rule_id: str) -> bool:
        with self._lock:
            data = self._load_data()
            rules = data.get("rules", [])
            initial_len = len(rules)
            data["rules"] = [r for r in rules if r.get("id") != rule_id]
            if len(data["rules"]) < initial_len:
                self._save_data(data)
                return True
            return False

    def toggle_rule(self, rule_id: str, is_active: Optional[bool] = None) -> Optional[Rule]:
        with self._lock:
            data = self._load_data()
            rules = data.get("rules", [])
            for idx, r in enumerate(rules):
                if r.get("id") == rule_id:
                    if is_active is None:
                        r["is_active"] = not r.get("is_active", True)
                    else:
                        r["is_active"] = is_active
                    r["updated_at"] = datetime.now().isoformat()
                    rules[idx] = r
                    data["rules"] = rules
                    self._save_data(data)
                    return Rule(**r)
            return None
