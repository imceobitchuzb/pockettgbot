"""
Signal Quality Grader.
Maps calibrated probability and confluence parameters into institutional grades:
GRADE_A, GRADE_B, or NO_TRADE.
"""
from typing import Tuple
from AITradingEngine.core.enums import QualityGrade


class QualityGrader:
    """Classifies signal setups into institutional quality grades."""

    @staticmethod
    def grade(
        calibrated_prob: float,
        confluence_count: int,
        mtf_aligned: bool,
        critic_approved: bool,
        expected_value: float
    ) -> Tuple[QualityGrade, str]:
        """
        Grades candidate setup:
        - GRADE_A: Institutional High-Conviction. Prob >= 0.80, Confluence >= 4, MTF Concordant, Critic Approved, EV >= +0.15.
        - GRADE_B: Standard Favorable Setup. Prob >= 0.72, Confluence >= 3, Critic Approved, EV >= +0.05.
        - NO_TRADE: Disqualified due to insufficient edge or confluence.
        """
        if not critic_approved:
            return QualityGrade.NO_TRADE, "Critic vetoed candidate"

        if expected_value < 0.05:
            return QualityGrade.NO_TRADE, f"Insufficient mathematical edge (EV={expected_value:.3f} < +0.05)"

        if confluence_count < 3:
            return QualityGrade.NO_TRADE, f"Insufficient confluence factors ({confluence_count} < 3)"

        # Check for Grade A criteria
        if (
            calibrated_prob >= 0.80 and
            confluence_count >= 4 and
            mtf_aligned and
            expected_value >= 0.15
        ):
            return QualityGrade.GRADE_A, "Institutional Grade A: High-conviction confluence"

        # Check for Grade B criteria
        if calibrated_prob >= 0.72 and confluence_count >= 3:
            return QualityGrade.GRADE_B, "Institutional Grade B: Validated statistical edge"

        return QualityGrade.NO_TRADE, f"Probability ({calibrated_prob:.2f}) below threshold (0.72)"
