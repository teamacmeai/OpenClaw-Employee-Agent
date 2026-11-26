import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class ContainerResolver:
    """Resolves container names using ordered prefix/regex rules."""

    def __init__(self, rules: Optional[List[Dict[str, Any]]] = None) -> None:
        self.rules = rules or []

    @classmethod
    def from_file(cls, path: Path | str) -> "ContainerResolver":
        p = Path(path)
        if not p.is_file():
            return cls([])
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        rules = data.get("rules", []) if isinstance(data, dict) else data
        return cls(rules)

    def resolve(self, source_type: str, subject: Optional[str]) -> Optional[str]:
        if not subject:
            return None

        for rule in self.rules:
            rule_source = rule.get("source_type", "*")
            if rule_source != "*" and rule_source != source_type:
                continue

            prefix = rule.get("prefix")
            if prefix and subject.startswith(prefix):
                return rule.get("container")

            regex = rule.get("regex")
            if regex and re.search(regex, subject):
                return rule.get("container")

        return None
