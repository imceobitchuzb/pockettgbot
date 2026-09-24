"""
Signal Configuration & Settings Management.
Provides persistent runtime configuration for the AI Signal Engine,
allowing seamless synchronization between the Frontend UI, Telegram Bot commands,
and backend quant evaluation parameters.
"""
import os
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

logger = logging.getLogger("AITradingEngine.SignalConfig")

DEFAULT_SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "signal_settings.json")


@dataclass
class SignalConfig:
    min_confidence: float = 0.75  # 0.60 to 0.90
    min_confluence: int = 3       # 2 to 5 strategies agreeing
    allowed_grades: List[str] = field(default_factory=lambda: ["GRADE_A", "GRADE_B"])
    active_timeframes: List[str] = field(default_factory=lambda: ["15s", "30s", "1m", "5m"])
    selected_expiration: str = "1m"  # 15s, 30s, 1m, 2m, 3m, 5m
    trading_mode: str = "STANDARD"   # CONSERVATIVE, STANDARD, AGGRESSIVE
    otc_enabled: bool = True
    real_market_enabled: bool = True
    min_payout_pct: float = 0.80     # Min broker payout to accept setup
    max_signals_per_hour: int = 15
    cooldown_seconds: int = 45       # Anti-overtrading per-asset cooldown
    strict_critic: bool = True       # Adversarial critic active
    auto_scan_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignalConfig":
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        # Type coercions & clamps
        if "min_confidence" in filtered:
            filtered["min_confidence"] = max(0.55, min(0.95, float(filtered["min_confidence"])))
        if "min_confluence" in filtered:
            filtered["min_confluence"] = max(1, min(6, int(filtered["min_confluence"])))
        if "min_payout_pct" in filtered:
            filtered["min_payout_pct"] = max(0.50, min(0.98, float(filtered["min_payout_pct"])))
        if "cooldown_seconds" in filtered:
            filtered["cooldown_seconds"] = max(10, min(600, int(filtered["cooldown_seconds"])))
        return cls(**filtered)


class SignalConfigManager:
    """Manages reading, writing, and pushing configuration to engine components."""

    def __init__(self, filepath: str = DEFAULT_SETTINGS_FILE):
        self.filepath = filepath
        self.config: SignalConfig = SignalConfig()
        self.load()

    def load(self) -> SignalConfig:
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.config = SignalConfig.from_dict(data)
                    logger.info(f"Loaded signal configuration from {self.filepath}")
            else:
                self.save()
        except Exception as e:
            logger.error(f"Failed to load signal configuration: {e}. Using defaults.")
            self.config = SignalConfig()
        return self.config

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.config.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"Saved signal configuration to {self.filepath}")
        except Exception as e:
            logger.error(f"Failed to save signal configuration: {e}")

    def update(self, new_data: Dict[str, Any], engine=None) -> SignalConfig:
        """Update settings and push directly to active engine."""
        self.config = SignalConfig.from_dict({**self.config.to_dict(), **new_data})
        self.save()
        if engine:
            self.apply_to_engine(engine)
        return self.config

    def reset_to_defaults(self, engine=None) -> SignalConfig:
        self.config = SignalConfig()
        self.save()
        if engine:
            self.apply_to_engine(engine)
        return self.config

    def apply_to_engine(self, engine):
        """Dynamic runtime injection of settings into engine components."""
        try:
            # 1. Trading mode presets
            if self.config.trading_mode == "CONSERVATIVE":
                conf_thresh = max(0.80, self.config.min_confidence)
                confl = max(3, self.config.min_confluence)
                cooldown = max(60, self.config.cooldown_seconds)
            elif self.config.trading_mode == "AGGRESSIVE":
                conf_thresh = min(0.70, self.config.min_confidence)
                confl = min(2, self.config.min_confluence)
                cooldown = min(30, self.config.cooldown_seconds)
            else:  # STANDARD
                conf_thresh = self.config.min_confidence
                confl = self.config.min_confluence
                cooldown = self.config.cooldown_seconds

            # 2. Risk engine settings
            if hasattr(engine, "anti_overtrading"):
                engine.anti_overtrading.cooldown_seconds = cooldown
                engine.anti_overtrading.max_signals_per_hour = self.config.max_signals_per_hour

            # 3. Confidence & Grader
            if hasattr(engine, "confidence_scorer"):
                engine.confidence_scorer.min_confidence = conf_thresh

            # 4. OTC Validator
            if hasattr(engine, "otc_validator"):
                engine.otc_validator.min_otc_payout = self.config.min_payout_pct
                engine.otc_validator.is_enabled = self.config.otc_enabled

            # 5. Critic strictness
            if hasattr(engine, "critic_layer"):
                engine.critic_layer.strict_mode = self.config.strict_critic

            logger.info("Signal configuration successfully propagated into engine runtime.")
        except Exception as e:
            logger.error(f"Error applying config to engine: {e}")


signal_config_manager = SignalConfigManager()
