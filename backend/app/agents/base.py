from abc import ABC, abstractmethod

from app.models.session_context import SessionContext


class BaseAgent(ABC):
    """
    Abstract base class for all EduAgent 2.0 pipeline agents.
    """

    name: str = "base_agent"

    @abstractmethod
    async def process(self, context: SessionContext) -> SessionContext:
        """
        Process the session context and return an updated context.

        Args:
            context: The current session state.

        Returns:
            Updated SessionContext after agent processing.
        """
        pass

    async def validate_input(self, context: SessionContext) -> bool:
        """
        Validate that the context has the minimum required fields.

        Args:
            context: The session context to validate.

        Returns:
            True if valid, False otherwise.
        """
        return context is not None and bool(context.session_id) and bool(context.user_id)

    async def handle_error(self, context: SessionContext, error: Exception) -> SessionContext:
        """
        Handle agent errors gracefully by recording them in context.

        Args:
            context: The current session context.
            error: The exception that occurred.

        Returns:
            The context with the error recorded.
        """
        context.add_error(f"[{self.name}] {type(error).__name__}: {str(error)}")
        return context
