"""Action config: `.github/bug-checker.yml` in the checked repository.

Every key is optional. A wrong key or value stops the Action with a message that
names it, instead of silently checking with a setting the team did not mean.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from bug_report_checker.core import TRIGGER_STATES
from bug_report_checker.github import BUG_LABELS

FILE = ".github/bug-checker.yml"
# Run 2's confidence max(p, 1 - p) peaks at 0.8635 on 3,794 answers; at 0.85 the bot
# still decides 59% of them, at 0.86 only 0.4%.
MAX_THRESHOLD = 0.85


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    bug_labels: tuple[str, ...] = BUG_LABELS
    status_labels: tuple[str, ...] = TRIGGER_STATES
    threshold: float = 0.85  # below this confidence a check says "not sure" (T3.4)
    comment_on_success: bool = True
    build_version_pattern: str | None = None  # the team's build format, if any
    environments: tuple[str, ...] = ()  # names of test stands, such as "staging"


def _labels(key: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(v, str) and v.strip() for v in value
    ):
        raise ConfigError(f"{FILE}: '{key}' must be a list of non-empty strings")
    return tuple(value)


def _threshold(key: str, value: object) -> float:
    # bool is an int in Python; `threshold: true` is a typo, not 1.
    number = isinstance(value, int | float) and not isinstance(value, bool)
    if not number or not 0.5 <= value <= MAX_THRESHOLD:
        raise ConfigError(
            f"{FILE}: '{key}' must be a number from 0.5 to {MAX_THRESHOLD}: the"
            " model's confidence tops out at about 0.86 (it was trained on soft"
            " labels), so a higher threshold makes almost every check 'not sure'"
        )
    return float(value)


def _flag(key: str, value: object) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{FILE}: '{key}' must be true or false")
    return value


def _pattern(key: str, value: object) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{FILE}: '{key}' must be a string")
    try:
        re.compile(value)
    except re.error as e:
        raise ConfigError(f"{FILE}: '{key}' is not a valid regex: {e}") from None
    return value


_PARSERS = {
    "bug_labels": _labels,
    "status_labels": _labels,
    "threshold": _threshold,
    "comment_on_success": _flag,
    "build_version_pattern": _pattern,
    "environments": _labels,
}


def parse_config(text: str) -> Config:
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise ConfigError(f"{FILE}: not valid YAML: {e}") from None
    if raw is None:
        return Config()
    if not isinstance(raw, dict):
        raise ConfigError(f"{FILE}: must be a mapping of keys to values")
    for key in raw:
        if key not in _PARSERS:
            known = ", ".join(_PARSERS)
            raise ConfigError(f"{FILE}: unknown key '{key}' (known: {known})")
    config = Config(**{k: _PARSERS[k](k, v) for k, v in raw.items()})
    if not config.status_labels:
        raise ConfigError(f"{FILE}: 'status_labels' must list at least one status")
    return config


def load_config(path: str | Path) -> Config:
    """Defaults when the repository has no config file."""
    path = Path(path)
    return parse_config(path.read_text("utf-8")) if path.exists() else Config()
