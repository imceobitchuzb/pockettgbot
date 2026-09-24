"""
Real Market Hours & Session Engine.
Validates interbank forex market sessions and trading hours.
Rejects trades on weekends or during the illiquid 21:55-22:10 UTC bank rollover.
"""
from datetime import datetime, timezone
from typing import Tuple, Dict, Any


class RealMarketSessionManager:
    """Manages real interbank market trading hours and sessions."""

    @staticmethod
    def is_market_open(dt: datetime = None) -> Tuple[bool, str]:
        """
        Interbank Forex is closed from Friday 21:00 UTC to Sunday 21:00 UTC.
        """
        if dt is None:
            dt = datetime.now(timezone.utc)

        weekday = dt.weekday()  # Monday is 0, Sunday is 6
        hour = dt.hour
        minute = dt.minute

        # Weekend closure: Friday >= 21:00 UTC through Sunday < 21:00 UTC
        if weekday == 4 and hour >= 21:  # Friday night
            return False, "Real interbank market closed for the weekend (Friday night)"
        if weekday == 5:  # Saturday
            return False, "Real interbank market closed (Saturday)"
        if weekday == 6 and hour < 21:  # Sunday before open
            return False, "Real interbank market closed (Sunday pre-market)"

        # Rollover window: 21:55 - 22:15 UTC daily (spreads blow out)
        if hour == 21 and minute >= 55:
            return False, "Interbank rollover in progress (high spread volatility)"
        if hour == 22 and minute <= 15:
            return False, "Interbank rollover in progress (high spread volatility)"

        return True, "Real market open and liquid"

    @staticmethod
    def get_active_session(dt: datetime = None) -> str:
        """Determines active forex financial center session."""
        if dt is None:
            dt = datetime.now(timezone.utc)
        hour = dt.hour

        sessions = []
        if 0 <= hour < 9:
            sessions.append("TOKYO/ASIAN")
        if 7 <= hour < 16:
            sessions.append("LONDON/EUROPEAN")
        if 12 <= hour < 21:
            sessions.append("NEW YORK/US")
        if 21 <= hour <= 23:
            sessions.append("SYDNEY")

        return " + ".join(sessions) if sessions else "OFF_HOURS"
