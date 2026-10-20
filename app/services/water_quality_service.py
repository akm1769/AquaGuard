"""Water quality analysis service for AquaGuard.

Evaluates aquaculture water quality parameters (pH, dissolved oxygen,
ammonia, temperature) and produces a risk assessment with actionable
recommendations for small-scale fish/shrimp farms.
"""


class WaterQualityService:
    """Analyzes water quality readings and returns a risk assessment."""

    # Ideal ranges for warm-water aquaculture (tilapia / shrimp).
    PARAM_RANGES = {
        "ph": (6.5, 9.0),
        "dissolved_oxygen": (4.0, 8.0),   # mg/L
        "ammonia": (0.0, 0.5),            # mg/L (non-ionized NH3-N)
        "temperature": (20.0, 32.0),      # °C
    }

    # How many points each parameter contributes to the risk score.
    PARAM_WEIGHTS = {
        "ph": 2,
        "dissolved_oxygen": 3,
        "ammonia": 3,
        "temperature": 2,
    }

    def __init__(self):
        pass

    def _score_param(self, param: str, value: float) -> int:
        """Return the risk contribution (0-3) for a single parameter."""
        lo, hi = self.PARAM_RANGES[param]
        if lo <= value <= hi:
            return 0
        # Distance outside the acceptable band, normalized.
        if value < lo:
            distance = (lo - value) / (hi - lo)
        else:
            distance = (value - hi) / (hi - lo)
        if distance < 0.25:
            return 1
        if distance < 0.75:
            return 2
        return 3

    def _recommendation(self, param: str, value: float) -> str:
        """Return a human-readable recommendation for an out-of-range value."""
        lo, hi = self.PARAM_RANGES[param]
        messages = {
            "ph": (
                "pH is too low (acidic). Add agricultural lime or crushed oyster "
                "shell to raise alkalinity gradually; test every 2 hours."
                if value < lo else
                "pH is too high (alkaline). Add peat moss or perform partial "
                "water change with dechlorinated water; monitor closely."
            ),
            "dissolved_oxygen": (
                "Dissolved oxygen is critically low. Increase aeration immediately "
                "- raise air-stone output, add water agitation, or reduce feeding "
                "rates until levels recover above 4 mg/L."
                if value < lo else
                "Dissolved oxygen is elevated. Reduce aeration intensity and verify "
                "no pure-oxygen injection is running uncontrolled."
            ),
            "ammonia": (
                "Ammonia is accumulating. Stop feeding for 24-48 hours, increase "
                "water changes (25-50%), and verify biofilter is functioning. "
                "Add nitrifying bacteria supplement if available."
                if value < lo else
                "Ammonia is dangerously high. Perform immediate large water change "
                "(50%), add ammonia detoxifier, and aerate heavily. Evacuate stock "
                "if mortality is observed."
            ),
            "temperature": (
                "Water temperature is too cold. Add insulation, reduce water flow "
                "through pond, or use a heater for sensitive species."
                if value < lo else
                "Water temperature is too hot. Shade the pond, increase water "
                "flow/aeration, and consider ice blocks for emergency cooling."
            ),
        }
        return messages[param]

    def analyze(self, readings: dict) -> dict:
        """Analyze water quality readings and return a risk assessment.

        Args:
            readings: dict with keys ph, dissolved_oxygen, ammonia, temperature.

        Returns:
            dict with keys risk_level, risk_score, recommendations.
        """
        # Validate inputs; default missing values to neutral.
        validated = {}
        for param in self.PARAM_RANGES:
            try:
                validated[param] = float(readings.get(param, 0.0))
            except (TypeError, ValueError):
                validated[param] = 0.0

        # Compute weighted risk score.
        total_weight = sum(self.PARAM_WEIGHTS.values())
        max_score = total_weight * 3
        score = 0
        recommendations = []

        for param, weight in self.PARAM_WEIGHTS.items():
            contribution = self._score_param(param, validated[param])
            score += contribution * weight
            if contribution > 0:
                recommendations.append(self._recommendation(param, validated[param]))

        # Normalize to a 0-8 scale (matching demo.py's "Risk Score: .../8").
        normalized = round((score / max_score) * 8)

        if normalized <= 2:
            risk_level = "low"
        elif normalized <= 5:
            risk_level = "medium"
        elif normalized <= 7:
            risk_level = "high"
        else:
            risk_level = "critical"

        if not recommendations:
            recommendations.append(
                "All water quality parameters are within acceptable ranges. "
                "Continue routine monitoring and maintain current management."
            )

        return {
            "risk_level": risk_level,
            "risk_score": normalized,
            "recommendations": recommendations,
            "parameters": validated,
        }