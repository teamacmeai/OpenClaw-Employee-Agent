import re
from typing import Any, Dict, Optional, Tuple

SENSITIVE_PATTERNS = [
    re.compile(r"(^|[/\\])\.env(\..+)?$", re.IGNORECASE),
    re.compile(r"\.pem$", re.IGNORECASE),
    re.compile(r"(^|[/\\])id_rsa(_\w+)?(\.pub)?$", re.IGNORECASE),
    re.compile(r"(credentials|secrets)\.(json|ya?ml|txt|ini)$", re.IGNORECASE),
    re.compile(r"(^|[/\\])\.aws[/\\]credentials$", re.IGNORECASE),
    re.compile(r"(^|[/\\])\.ssh[/\\]", re.IGNORECASE),
]

SECRET_VALUE_PATTERNS = [
    re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]{10,}", re.IGNORECASE),
    re.compile(r"(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}", re.IGNORECASE),
    re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9]{20,}", re.IGNORECASE),
    re.compile(r"ocl_[a-fA-F0-9]+_[a-fA-F0-9]+", re.IGNORECASE),
]


def is_sensitive_subject(subject: Optional[str]) -> bool:
    if not subject:
        return False
    return any(pattern.search(subject) for pattern in SENSITIVE_PATTERNS)


def scrub_string(value: str) -> str:
    scrubbed = value
    for pattern in SECRET_VALUE_PATTERNS:
        scrubbed = pattern.sub("[REDACTED_SECRET]", scrubbed)
    return scrubbed


def redact_attributes(attrs: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for k, v in attrs.items():
        if isinstance(v, str):
            cleaned[k] = scrub_string(v)
        else:
            cleaned[k] = v
    return cleaned


def redact_event_subject_and_attributes(
    subject: Optional[str], attributes: Dict[str, Any]
) -> Tuple[Optional[str], Dict[str, Any]]:
    if is_sensitive_subject(subject):
        return None, redact_attributes(attributes)
    return subject, redact_attributes(attributes)
