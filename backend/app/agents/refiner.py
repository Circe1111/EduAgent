from app.agents.base import BaseAgent
from app.core.llm import LLMClient
from app.models.content import GeneratedContent
from app.models.session_context import SessionContext


class RefinerAgent(BaseAgent):
    """
    Agent that performs targeted content repair based on critique feedback.

    Instead of regenerating the entire content, this agent focuses on fixing
    only the problematic sections identified by the critic, preserving all
    correct content to save tokens and improve iteration speed.
    """

    name = "refiner"

    SYSTEM_PROMPT = (
        "你是一位精准的教育内容修复专家。你的任务是根据评审反馈，"
        "对教学内容进行局部、精准的修改。\n\n"
        "核心原则：\n"
        "1. 只修改有问题的部分，保留所有正确的内容\n"
        "2. 针对每个问题，按照对应的修改建议进行修复\n"
        "3. 保持原有的格式、标记和整体结构不变\n"
        "4. 修复后的内容必须准确、完整、适合学生水平\n\n"
        "输出要求：\n"
        "只修改有问题的部分，保留所有正确的内容。输出完整的、修改后的内容，而不仅仅是修改的部分。\n"
        "- 保持原有的章节标记（如 ===QUESTION===, ===EXAMPLE=== 等）\n"
        "- 不要添加额外的解释或总结，只输出修改后的内容本身\n"
        "- 如果某个问题无法确定如何修复，保留原内容并在metadata中注明"
    )

    def __init__(self) -> None:
        self.llm = LLMClient()

    async def process(self, context: SessionContext) -> SessionContext:
        if not await self.validate_input(context):
            context.add_error("RefinerAgent: missing generated_content or critique_result")
            return context

        original_content = context.generated_content

        try:
            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": self._build_refinement_prompt(context),
                },
            ]

            response = await self.llm.chat(
                messages,
                temperature=0.3,
                max_tokens=4096,
            )

            refined_text = response.get("content", "")

            if not refined_text or not refined_text.strip():
                raise ValueError("Refiner returned empty content")

            context.generated_content = GeneratedContent(
                content=refined_text.strip(),
                content_type=original_content.content_type,
                metadata={
                    **original_content.metadata,
                    "refined": True,
                    "refiner_model": response.get("model"),
                },
                confidence=original_content.confidence,
            )

        except Exception as exc:
            context = await self.handle_error(context, exc)
            context.metadata["low_confidence"] = True
            context.metadata["refiner_failed"] = True

        return context

    async def validate_input(self, context: SessionContext) -> bool:
        """
        Validate that the context has both generated_content and critique_result.
        """
        base_valid = await super().validate_input(context)
        if not base_valid:
            return False
        return (
            context.generated_content is not None
            and context.critique_result is not None
        )

    def _build_refinement_prompt(self, context: SessionContext) -> str:
        """Build the focused refinement prompt from context."""
        parts: list[str] = []

        # Original context
        if context.task_intent is not None:
            parts.append(f"任务类型：{context.task_intent.task_type.value}")
            parts.append(f"目标知识点：{context.task_intent.knowledge_points}")
            parts.append(f"期望难度：{context.task_intent.difficulty}")

        if context.student_profile is not None:
            parts.append(
                f"学生水平：难度偏好 {context.student_profile.overall_difficulty:.1f}"
            )
            parts.append(f"学习风格：{context.student_profile.learning_style}")

        if context.retrieval_results:
            parts.append("参考资料：")
            for idx, r in enumerate(context.retrieval_results, start=1):
                parts.append(
                    f"[{idx}] 来源：{r.get('source', '未知')} - "
                    f"{r.get('chapter', '未知')}"
                )
                text = r.get("text", "")
                parts.append(f"内容：{text[:500]}")

        # Original generated content
        gc = context.generated_content
        if gc is not None:
            parts.append(f"内容类型：{gc.content_type}")
            parts.append(f"原始内容：\n{gc.content}")

        # Critique feedback (only failed sections)
        critique = context.critique_result
        if critique is not None and not critique.passed:
            parts.append("【评审反馈 - 需要修改的问题】")
            if critique.issues:
                parts.append("问题列表：")
                for issue in critique.issues:
                    parts.append(f"  - {issue}")
            if critique.fix_suggestions:
                parts.append("修改建议：")
                for suggestion in critique.fix_suggestions:
                    parts.append(f"  - {suggestion}")
            if critique.issue_types:
                parts.append(f"问题类型：{', '.join(critique.issue_types)}")

        parts.append(
            "\n请根据以上评审反馈，对原始内容进行精准修改。"
            "只修改有问题的部分，保留所有正确的内容。"
            "输出完整的、修改后的内容，而不仅仅是修改的部分。"
        )

        return "\n\n".join(parts)
