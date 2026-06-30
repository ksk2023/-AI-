"""Centralized configuration loader.

Loads API keys and settings from a local .env file into the environment.
Never hardcode keys in source files -- always read them from here.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

# Resolve repo root as the parent of this src/ directory.
REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"

if load_dotenv is not None and ENV_FILE.exists():
    load_dotenv(ENV_FILE)


def _require(key: str) -> str:
    """Return an env var or raise a clear error if it is missing."""
    val = os.environ.get(key, "").strip()
    if not val:
        raise RuntimeError(
            f"Missing required environment variable: {key}. "
            f"Add it to {ENV_FILE} (see .env.example)."
        )
    return val


def _optional(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


@dataclass(frozen=True)
class ApiConfig:
    """API credentials and endpoints for each data provider."""

    # Primary price-data source (high quality, adjusted, survivorship-aware).
    finance_hub_key: str
    finance_hub_base_url: str

    # Supplementary: fundamentals, macro, technical indicators.
    alpha_vantage_key: str
    alpha_vantage_base_url: str

    # Reserved for future providers.
    polygon_key: str
    alpaca_key: str
    alpaca_secret: str


def load_api_config() -> ApiConfig:
    """Build the ApiConfig from the current environment."""
    return ApiConfig(
        finance_hub_key=_require("FINANCE_HUB_API_KEY"),
        finance_hub_base_url=_optional(
            "FINANCE_HUB_BASE_URL", "https://api.financehub.example.com/v1"
        ),
        alpha_vantage_key=_require("ALPHA_VANTAGE_API_KEY"),
        alpha_vantage_base_url=_optional(
            "ALPHA_VANTAGE_BASE_URL", "https://www.alphavantage.co/query"
        ),
        polygon_key=_optional("POLYGON_API_KEY"),
        alpaca_key=_optional("ALPACA_API_KEY"),
        alpaca_secret=_optional("ALPACA_API_SECRET"),
    )


# Convenient module-level singleton for ad-hoc use.
CONFIG = load_api_config()