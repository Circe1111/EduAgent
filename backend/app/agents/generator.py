from typing import Optional

from app.agents.base import BaseAgent
from app.core.llm import LLMClient
from app.models.content import GeneratedContent
from app.models.session_context import SessionContext


class ContentGenerationAgent(BaseAgent):
    """
    Agent that generates teaching content (quiz, lecture, explanation,
    code review) based on intent, profile, and retrieved chunks.
    """

    name = "content_generation"

    SYSTEM_PROMPT = (
        "你是一位专业的Python教育内容生成专家。你的目标是为中国大学生生成"
        "高质量、准确、难度匹配的Python学习内容。\n\n"
        "生成原则：\n"
        "1. 准确性：所有代码示例和概念解释必须准确无误\n"
        "2. 难度匹配：根据学生水平调整内容深度，避免过于简单或过于复杂\n"
        "3. 教学品质：使用清晰的解释、恰当的类比、完整的示例\n"
        "4. 中文输出：所有解释使用中文，代码保持英文\n"
        "5. 结构化输出：使用清晰的章节标记，方便后续评估\n\n"
        "输出格式要求：\n"
        "- 对于测验(quiz)：生成题目、选项、答案、解析，"
        "使用 ===QUESTION===, ===ANSWER===, ===EXPLANATION=== 标记\n"
        "- 对于讲义(lecture)：使用 ===CONCEPT===, ===EXAMPLE===, ===SUMMARY=== 标记\n"
        "- 对于解释(explanation)：使用 ===STEP===, ===ANALOGY===, ===CODE=== 标记\n"
        "- 对于代码审查(code_review)：使用 ===ISSUE===, ===SUGGESTION===, "
        "===IMPROVED_CODE=== 标记\n\n"
        "如果'参考资料'部分为空（【无参考资料可用】），请在开头注明："
        "【注意：以下内容未基于参考资料生成，仅供参考】。如果参考资料不为空，则不需要此标注。"
    )

    def __init__(self) -> None:
        self.llm = LLMClient()

    async def process(self, context: SessionContext) -> SessionContext:
        if not await self.validate_input(context):
            return context.add_error("ContentGenerationAgent: invalid input context")

        try:
            prompt = self._build_prompt(context)

            # Use routed model and temperature from intent analysis
            selected_model = context.metadata.get("selected_model")
            temperature = context.metadata.get("temperature", 0.7)

            response = await self.llm.chat(
                [
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                model=selected_model,
                temperature=temperature,
                max_tokens=4096,
            )

            content = response.get("content", "")
            # Post-process: strip the "no references" disclaimer if retrieval was successful
            if context.retrieval_results and "未基于参考资料生成" in content:
                content = content.replace(
                    "【注意：以下内容未基于参考资料生成，仅供参考】\n\n", ""
                ).replace(
                    "【注意：以下内容未基于参考资料生成，仅供参考】", ""
                ).strip()
            content_type = (
                context.task_intent.output_type
                if context.task_intent is not None
                else "notes"
            )

            confidence = (
                0.6
                if context.metadata.get("retrieval_empty")
                else 0.8
            )

            context.generated_content = GeneratedContent(
                content=content,
                content_type=content_type,
                metadata={
                    "model": response.get("model"),
                    "retrieval_empty": context.metadata.get("retrieval_empty", False),
                },
                confidence=confidence,
            )

        except Exception as exc:
            context = await self.handle_error(context, exc)

        return context

    def _build_prompt(self, context: SessionContext) -> str:
        """Assemble the generation prompt from all available context."""
        parts: list[str] = []

        # Student profile
        if context.student_profile is not None:
            parts.append(
                f"学生水平：难度偏好 {context.student_profile.overall_difficulty:.1f}"
            )
            parts.append(f"学习风格：{context.student_profile.learning_style}")
            parts.append(
                "已掌握知识点："
                f"{list(context.student_profile.knowledge_points.keys())}"
            )

        # Intent
        if context.task_intent is not None:
            parts.append(f"任务类型：{context.task_intent.task_type.value}")
            parts.append(f"目标知识点：{context.task_intent.knowledge_points}")
            parts.append(f"期望难度：{context.task_intent.difficulty}")
            parts.append(f"输出格式：{context.task_intent.output_type}")

        # History
        if context.history_summary:
            parts.append(f"历史摘要：{context.history_summary}")

        # Retrieved chunks
        if context.retrieval_results:
            parts.append("参考资料：")
            for idx, r in enumerate(context.retrieval_results, start=1):
                parts.append(
                    f"[{idx}] 来源：{r.get('source', '未知')} - "
                    f"{r.get('chapter', '未知')}"
                )
                text = r.get("text", "")
                parts.append(f"内容：{text[:500]}")
        else:
            parts.append("【无参考资料可用】")

        if context.critique_result is not None:
            parts.append("【上一轮评审反馈】")
            parts.append(f"通过状态：{'通过' if context.critique_result.passed else '未通过'}")
            if context.critique_result.issues:
                parts.append("问题列表：")
                for issue in context.critique_result.issues:
                    parts.append(f"  - {issue}")
            if context.critique_result.fix_suggestions:
                parts.append("修改建议：")
                for suggestion in context.critique_result.fix_suggestions:
                    parts.append(f"  - {suggestion}")

        # Original query
        if context.task_spec and isinstance(context.task_spec, dict):
            original_query = context.task_spec.get("query")
            if original_query:
                parts.append(f"学生原始问题：{original_query}")

        return "\n\n".join(parts)
