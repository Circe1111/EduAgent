from typing import Optional

from app.core.config import get_settings


class ModelRouter:
    """
    Selects the appropriate LLM model for a given task based on
    task complexity, student profile, and confidence level.
    """

    LIGHT_TASKS = {"explanation", "notes"}
    HEAVY_TASKS = {"quiz", "code_review", "path_planning"}

    def __init__(self) -> None:
        settings = get_settings()
        self.main_model = settings.LLM_MODEL
        self.light_model = getattr(settings, "LIGHT_LLM_MODEL", None) or self.main_model

    def get_model_for_intent(self, intent, profile) -> str:
        """
        Returns model name based on:
        - task_type: light -> light model, heavy -> main model
        - knowledge_points complexity
        - student difficulty (beginner vs advanced)
        - confidence level (low -> main model for reliability)

        Routing logic:
        - explanation + low complexity + beginner -> light
        - explanation + low complexity + advanced -> light
        - explanation + high complexity + beginner -> main
        - explanation + high complexity + advanced -> light
        - quiz / code_review / path_planning -> main (accuracy critical)
        - notes -> light
        - low confidence intent -> main
        """
        task_type = intent.task_type.value if intent else "explanation"
        output_type = intent.output_type if intent else "notes"
        confidence = intent.confidence if intent else 0.5
        difficulty = intent.difficulty if intent else 0.5
        knowledge_points = intent.knowledge_points if intent else []

        # Low confidence intent -> main model for reliability
        if confidence < 0.6:
            return self.main_model

        # Accuracy-critical tasks always use main model
        if task_type in self.HEAVY_TASKS:
            return self.main_model

        # Notes output type -> light model
        if output_type == "notes":
            return self.light_model

        # Explanation tasks: route based on complexity and student level
        if task_type == "explanation":
            is_high_complexity = len(knowledge_points) > 2 or difficulty >= 0.6
            is_beginner = (
                profile.overall_difficulty < 0.5 if profile else True
            )

            if is_high_complexity and is_beginner:
                # High complexity + beginner needs main model for clarity
                return self.main_model
            # All other explanation cases -> light model
            return self.light_model

        # Default to main model for any unhandled task types
        return self.main_model

    def get_temperature_for_task(self, task_type: str) -> float:
        """
        Returns recommended temperature based on task type.
        - quiz / code_review: 0.5 (lower creativity, higher accuracy)
        - explanation / path_planning: 0.7 (balanced creativity)
        - default: 0.7
        """
        if task_type in {"quiz", "code_review"}:
            return 0.5
        if task_type in {"explanation", "path_planning"}:
            return 0.7
        return 0.7
