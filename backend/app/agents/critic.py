import json
from typing import List

from app.agents.base import BaseAgent
from app.core.llm import LLMClient
from app.models.content import CritiqueResult
from app.models.session_context import SessionContext


class CritiqueAgent(BaseAgent):
    """
    Agent that reviews generated content against quality criteria
    and produces structured critique results.
    """

    name = "critique"

    SYSTEM_PROMPT = (
        "你是一位严格的Python教育内容质量评审专家。请对生成的教学内容进行系统性评审。\n\n"
        "评审维度：\n"
        "1. 准确性(accuracy)：代码和概念是否正确无误\n"
        "2. 难度匹配(difficulty_match)：内容难度是否适合学生水平\n"
        "3. 教学品质(pedagogical)：解释是否清晰，示例是否恰当\n"
        "4. 格式合规(format)：是否遵循了要求的章节标记\n"
        "5. 完整性(completeness)：是否覆盖了请求的知识范围\n\n"
        "输出要求（JSON格式）：\n"
        '{\n'
        '    "passed": true/false,\n'
        '    "issues": ["问题1：具体位置和描述", "问题2..."],\n'
        '    "issue_types": ["accuracy", "difficulty_match", ...],\n'
        '    "fix_suggestions": ["建议1", "建议2..."]\n'
        '}\n\n'
        "规则：\n"
        "- 如果内容有明显事实错误、代码无法运行、或严重偏离学生水平，passed设为false\n"
        "- issues必须具体，指出问题所在的位置（如\"第3行代码\"、\"===EXAMPLE===部分\"）\n"
        "- 如果内容基本可用但有小瑕疵，passed可设为true但列出改进建议\n"
        "- 如果不确定内容准确性，passed设为true，在metadata中注明\"uncertain\"\n"
        "- 只输出JSON，不要其他文字"
    )

    def __init__(self) -> None:
        self.llm = LLMClient()

    async def process(self, context: SessionContext) -> SessionContext:
        if not await self.validate_input(context):
            return context.add_error("CritiqueAgent: invalid input context")

        if context.generated_content is None:
            return context.add_error("CritiqueAgent: missing generated_content")

        try:
            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": self._build_review_prompt(context),
                },
            ]

            # Use routed model from intent analysis
            selected_model = context.metadata.get("selected_model")
            temperature = context.metadata.get("temperature", 0.3)

            response = await self.llm.chat(
                messages,
                model=selected_model,
                temperature=temperature,
                max_tokens=2048,
            )
            raw = response.get("content", "")

            critique = self._parse_critique(raw)
            context.critique_result = critique

            retry_count = context.metadata.get("critique_retry_count", 0)
            context.metadata["critique_retry_count"] = retry_count

        except Exception as exc:
            context = await self.handle_error(context, exc)
            context.critique_result = CritiqueResult(
                passed=True,
                issues=[f"评审过程出错：{str(exc)}"],
                issue_types=["system_error"],
                fix_suggestions=["请人工复核内容质量"],
            )
            context.metadata["critique_uncertain"] = True

        return context

    def _build_review_prompt(self, context: SessionContext) -> str:
        """Build the prompt sent to the critique LLM."""
        parts: list[str] = []

        task_type = (
            context.task_intent.task_type.value
            if context.task_intent is not None
            else "unknown"
        )
        parts.append(f"任务类型：{task_type}")
        parts.append(f"目标知识点：{context.knowledge_points}")
        parts.append(f"学生难度：{context.difficulty}")

        gc = context.generated_content
        if gc is not None:
            parts.append(f"内容类型：{gc.content_type}")
            parts.append(f"生成内容：\n{gc.content}")

        return "\n\n".join(parts)

    def _parse_critique(self, raw: str) -> CritiqueResult:
        """Parse LLM critique output into CritiqueResult."""
        try:
            json_str = raw
            if "```json" in raw:
                json_str = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                json_str = raw.split("```")[1].split("```")[0].strip()

            data = json.loads(json_str)
            passed = bool(data.get("passed", True))
            issues = data.get("issues", [])
            issue_types = data.get("issue_types", [])
            fix_suggestions = data.get("fix_suggestions", [])

            # Detect uncertainty flag in issues text
            if any("不确定" in i or "uncertain" in i.lower() for i in issues):
                pass  # uncertainty is implicit in the issues list

            return CritiqueResult(
                passed=passed,
                issues=issues if isinstance(issues, list) else [],
                issue_types=issue_types if isinstance(issue_types, list) else [],
                fix_suggestions=fix_suggestions
                if isinstance(fix_suggestions, list)
                else [],
            )

        except Exception:
            return CritiqueResult(
                passed=True,
                issues=["评审输出解析失败，无法自动判定质量"],
                issue_types=["parse_error"],
                fix_suggestions=["建议人工检查"],
            )
