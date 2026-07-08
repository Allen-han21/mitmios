"""Mock response addon - intercepts requests and returns configured mock responses.

Loaded automatically by mitmios. Rules are managed via the web UI (/mock-rules API).
Rules are persisted to ~/.config/mitmios/mock_responses.yaml.
"""

import json
import logging
from pathlib import Path

import yaml
from mitmproxy import ctx, http

logger = logging.getLogger(__name__)

CONFIG_PATH = Path.home() / ".config" / "mitmios" / "mock_responses.yaml"

# Singleton instance for access from API handlers
_instance: "MockResponseAddon | None" = None


def get_instance() -> "MockResponseAddon | None":
    return _instance


class MockResponseAddon:
    def __init__(self):
        global _instance
        _instance = self
        self.rules: list[dict] = []
        self._load_from_disk()

    def _load_from_disk(self):
        if not CONFIG_PATH.exists():
            self.rules = []
            return
        try:
            data = yaml.safe_load(CONFIG_PATH.read_text())
            self.rules = data.get("rules", []) if data else []
        except Exception as e:
            logger.warning(f"[mock] Failed to load rules: {e}")
            self.rules = []

    def _save_to_disk(self):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {"rules": self.rules}
        CONFIG_PATH.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False))

    def get_rules(self) -> list[dict]:
        return self.rules

    def set_rules(self, rules: list[dict]):
        self.rules = rules
        self._save_to_disk()

    def request(self, flow: http.HTTPFlow) -> None:
        for rule in self.rules:
            if not rule.get("enabled", True):
                continue
            if rule.get("url_pattern", "") in flow.request.pretty_url:
                status = rule.get("status_code", 500)
                body = rule.get("body", "")
                flow.response = http.Response.make(
                    status,
                    body.encode(),
                    {"Content-Type": "application/json"},
                )
                logger.info(f"[mock] {flow.request.pretty_url} -> {status}")
                return
