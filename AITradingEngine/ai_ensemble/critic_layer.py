"""
AI Layer #2: Adversarial Critic.
Acts as devil's advocate to actively search for reasons to REJECT or PENALIZE the proposed trade thesis.
"""
from typing import Optional, Dict, Any, List
from AITradingEngine.core.enums import Direction, MarketRegime
from AITradingEngine.core.models import MarketSnapshot, CriticVerdict
from AITradingEngine.pattern_engine.price_action import detect_sr_levels, detect_pin_bar


class AdversarialCritic:
    """Adversarial Critic seeking trade invalidation."""

    def __init__(self, max_allowed_penalty: float = 0.25):
        self.max_allowed_penalty = max_allowed_penalty

    def critique(
        self,
        snapshot: MarketSnapshot,
        proposed_direction: Direction,
        setup_name: str
    ) -> CriticVerdict:
        """
        Rigorously evaluates the setup for hidden traps or unfavorable conditions.
        """
        if proposed_direction == Direction.NO_SIGNAL:
            return CriticVerdict(
                is_approved=False,
                veto_reason="NO_DIRECTION_PROPOSED",
                penalty_score=1.0,
                risk_notes="No active trade direction to critique."
            )

        penalties = 0.0
        risk_notes = []

        ind = snapshot.indicators
        rsi = ind.get("rsi", 50.0)
        atr = ind.get("atr", 0.0005)

        # 1. Counter Rejection Wick in latest candle
        if snapshot.candles:
            curr_candle = snapshot.candles[-1]
            is_pin, pin_dir = detect_pin_bar(curr_candle, atr)
            # If proposing CALL but latest candle is a bearish pin bar (upper rejection wick)
            if proposed_direction == Direction.CALL and pin_dir == Direction.PUT:
                return CriticVerdict(
                    is_approved=False,
                    veto_reason="ADVERSARIAL_VETO: Bearish rejection wick directly opposes CALL",
                    penalty_score=0.4,
                    risk_notes="Upper wick rejection indicates heavy supply capping upside."
                )
            # If proposing PUT but latest candle is a bullish pin bar (lower rejection wick)
            if proposed_direction == Direction.PUT and pin_dir == Direction.CALL:
                return CriticVerdict(
                    is_approved=False,
                    veto_reason="ADVERSARIAL_VETO: Bullish rejection wick directly opposes PUT",
                    penalty_score=0.4,
                    risk_notes="Lower wick rejection indicates aggressive buying floor."
                )

        # 2. Momentum Exhaustion Check
        # Buying into overbought territory
        if proposed_direction == Direction.CALL and rsi > 74.0 and setup_name != "BreakoutConfirm":
            penalties += 0.12
            risk_notes.append(f"RSI exhausted ({rsi:.1f} > 74)")
            if rsi > 80.0:
                return CriticVerdict(
                    is_approved=False,
                    veto_reason=f"ADVERSARIAL_VETO: Extreme overbought exhaustion (RSI={rsi:.1f})",
                    penalty_score=0.35,
                    risk_notes="High risk of sharp pullback against CALL."
                )

        # Selling into oversold territory
        if proposed_direction == Direction.PUT and rsi < 26.0 and setup_name != "BreakoutConfirm":
            penalties += 0.12
            risk_notes.append(f"RSI exhausted ({rsi:.1f} < 26)")
            if rsi < 20.0:
                return CriticVerdict(
                    is_approved=False,
                    veto_reason=f"ADVERSARIAL_VETO: Extreme oversold exhaustion (RSI={rsi:.1f})",
                    penalty_score=0.35,
                    risk_notes="High risk of sharp bounce against PUT."
                )

        # 3. Impending Support/Resistance Collision
        if len(snapshot.candles) >= 30:
            sr = detect_sr_levels(snapshot.candles, lookback=45)
            curr_price = snapshot.current_price
            proximity_buffer = 0.8 * atr if atr > 0 else 0.0003

            # Proposing CALL directly under major resistance
            if proposed_direction == Direction.CALL and setup_name != "BreakoutConfirm":
                for res in sr.get("resistance", []):
                    if 0 < (res - curr_price) <= proximity_buffer:
                        penalties += 0.15
                        risk_notes.append(f"Proximity to major resistance barrier ({res:.5f})")

            # Proposing PUT directly above major support
            if proposed_direction == Direction.PUT and setup_name != "BreakoutConfirm":
                for sup in sr.get("support", []):
                    if 0 < (curr_price - sup) <= proximity_buffer:
                        penalties += 0.15
                        risk_notes.append(f"Proximity to major support barrier ({sup:.5f})")

        # 4. Total penalty evaluation
        if penalties > self.max_allowed_penalty:
            return CriticVerdict(
                is_approved=False,
                veto_reason=f"ADVERSARIAL_VETO: Cumulative risk penalties exceeded ({penalties:.2f} > {self.max_allowed_penalty})",
                penalty_score=penalties,
                risk_notes="; ".join(risk_notes)
            )

        return CriticVerdict(
            is_approved=True,
            veto_reason=None,
            penalty_score=round(penalties, 3),
            risk_notes="; ".join(risk_notes) if risk_notes else "Setup cleared by adversarial critic."
        )
