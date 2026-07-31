from __future__ import annotations

from structlog import get_logger

from apps.api.app.core.config import settings

logger = get_logger()


class AiLogger:
    async def log_request(
        self,
        agent_type: str,
        user_id: str | None,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        duration_ms: float = 0.0,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        cost = self._estimate_cost(model, input_tokens, output_tokens)

        log_data = {
            "agent_type": agent_type,
            "user_id": user_id,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "estimated_cost": round(cost, 6),
            "duration_ms": round(duration_ms, 2),
            "success": success,
        }

        if error:
            log_data["error"] = error
            await logger.awarning("ai_request_failed", **log_data)
        else:
            await logger.ainfo("ai_request_succeeded", **log_data)

    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        rates = {
            "gpt-4o": (2.50, 10.00),
            "gpt-4o-mini": (0.15, 0.60),
            "gpt-4": (30.00, 60.00),
            "gemini-pro": (0.50, 1.50),
            "grok-beta": (5.00, 15.00),
        }

        input_rate, output_rate = rates.get(model, (1.00, 2.00))
        input_cost = (input_tokens / 1_000_000) * input_rate
        output_cost = (output_tokens / 1_000_000) * output_rate
        return input_cost + output_cost


ai_logger = AiLogger()