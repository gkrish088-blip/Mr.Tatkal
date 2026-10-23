"""Central redaction for structured logs; screenshots must be masked at capture."""
import re


class Redactor:
    SENSITIVE = re.compile(r"password|passwd|secret|(?:^|[_-])token(?:$|[_-])|api[_-]?key|authorization|upi|mobile|phone|passenger|id_details", re.I)
    PATTERNS = (
        re.compile(r"\b(?:sk|ghp|github_pat)[-_][A-Za-z0-9_-]{12,}\b"),
        re.compile(r"(?i)\bBearer\s+[^\s\"']+"),
        re.compile(r"(?i)(?:password|api[_-]?key|token|secret)\s*[=:]\s*[^\s,;\"']+"),
    )

    def __init__(self, secrets=()):
        self.secrets = set()
        for secret in secrets:
            self.register(secret)

    def register(self, secret):
        if secret is not None and str(secret):
            self.secrets.add(str(secret))

    def redact(self, value):
        if isinstance(value, dict):
            return {self.redact(str(k)): "[REDACTED]" if self.SENSITIVE.search(str(k)) else self.redact(v)
                    for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.redact(v) for v in value]
        if isinstance(value, str):
            for secret in sorted(self.secrets, key=len, reverse=True):
                if len(secret) < 4:
                    value = re.sub(r"(?<![A-Za-z0-9])" + re.escape(secret) + r"(?![A-Za-z0-9])", "[REDACTED]", value)
                else:
                    value = value.replace(secret, "[REDACTED]")
            for pattern in self.PATTERNS:
                value = pattern.sub("[REDACTED]", value)
        return value
