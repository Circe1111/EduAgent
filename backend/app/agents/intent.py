import json
import re
from typing import Optional

from app.agents.base import BaseAgent
from app.core.llm import LLMClient
from app.models.intent import IntentResult, TaskType
from app.models.session_context import SessionContext
from app.services.router_service import ModelRouter


class IntentAnalysisAgent(BaseAgent):
    """
    Agent that analyses a student's natural-language query and extracts
    structured intent information.
    """

    name = "intent_analysis"

    SYSTEM_PROMPT = (
        "你是一位专业的Python教育意图分析专家。你的任务是分析学生的学习请求，提取关键信息。\n\n"
        "请分析学生的自然语言查询，输出结构化结果。你必须以JSON格式输出，包含以下字段：\n"
        '- task_type: 任务类型，必须是以下之一："quiz"(测验)、"lecture"(讲义)、'
        '"explanation"(解释)、"path_planning"(路径规划)、"code_review"(代码审查)\n'
        '- knowledge_points: 提取的知识点列表，如["列表推导式", "字典操作"]\n'
        '- difficulty: 难度估计，0.0-1.0之间（根据学生用语判断：'
        "基础词汇=0.2-0.4，进阶词汇=0.5-0.7，高级/优化=0.8-1.0）\n"
        '- output_type: 期望输出格式，可选："exercises"(练习题)、"notes"(笔记)、'
        '"examples"(示例)、"path"(学习路径)\n'
        '- confidence: 你对意图分类的置信度，0.0-1.0\n\n'
        "注意：\n"
        "1. 只输出JSON，不要输出其他解释文字\n"
        "2. 如果请求模糊，给出最佳猜测但降低confidence\n"
        "3. 所有字段必须存在"
    )

    def __init__(self) -> None:
        self.llm = LLMClient()
        self.router = ModelRouter()

    async def process(self, context: SessionContext) -> SessionContext:
        if not await self.validate_input(context):
            return context.add_error("IntentAnalysisAgent: invalid input context")

        try:
            query_text = ""
            if context.task_spec and isinstance(context.task_spec, dict):
                query_text = context.task_spec.get("query", "") or ""

            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"历史摘要：{context.history_summary or '无'}\n"
                        f"当前请求：{query_text}"
                    ),
                },
            ]

            response = await self.llm.chat(
                messages,
                temperature=0.3,
                max_tokens=1024,
            )
            raw_content = response.get("content", "")

            intent = self._parse_intent(raw_content)
            context.task_intent = intent
            context.knowledge_points = intent.knowledge_points
            context.difficulty = intent.difficulty
            context.metadata["intent_confidence"] = intent.confidence

            # Route to appropriate model based on intent and profile
            selected_model = self.router.get_model_for_intent(
                intent, context.student_profile
            )
            context.metadata["selected_model"] = selected_model

            # Set recommended temperature based on task type
            temperature = self.router.get_temperature_for_task(intent.task_type.value)
            context.metadata["temperature"] = temperature

        except Exception as exc:
            context = await self.handle_error(context, exc)
            context.task_intent = self._fallback_intent()

        return context

    def _parse_intent(self, raw: str) -> IntentResult:
        """Parse LLM output into IntentResult with fallback extraction."""
        try:
            json_str = raw
            if "```json" in raw:
                json_str = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                json_str = raw.split("```")[1].split("```")[0].strip()

            data = json.loads(json_str)
            return IntentResult(
                task_type=TaskType(data.get("task_type", "explanation")),
                knowledge_points=data.get("knowledge_points", []),
                difficulty=float(data.get("difficulty", 0.5)),
                output_type=data.get("output_type", "notes"),
                confidence=float(data.get("confidence", 0.5)),
            )
        except Exception:
            return self._extract_intent_fallback(raw)

    def _extract_intent_fallback(self, raw: str) -> IntentResult:
        """Best-effort regex extraction when JSON parsing fails."""
        task_type = "explanation"
        for t in TaskType:
            if t.value in raw.lower():
                task_type = t.value
                break

        knowledge_points: list[str] = []
        kp_match = re.search(
            r'knowledge_points["\']?\s*[:=]\s*\[(.*?)\]', raw, re.DOTALL
        )
        if kp_match:
            knowledge_points = re.findall(r'["\'](.*?)["\']', kp_match.group(1))

        difficulty = 0.5
        diff_match = re.search(r'difficulty["\']?\s*[:=]\s*([0-9.]+)', raw)
        if diff_match:
            difficulty = float(diff_match.group(1))

        output_type = "notes"
        ot_match = re.search(r'output_type["\']?\s*[:=]\s*["\'](.*?)["\']', raw)
        if ot_match:
            output_type = ot_match.group(1)

        return IntentResult(
            task_type=TaskType(task_type),
            knowledge_points=knowledge_points,
            difficulty=difficulty,
            output_type=output_type,
            confidence=0.3,
        )

    def _fallback_intent(self) -> IntentResult:
        """Low-confidence fallback when everything fails."""
        return IntentResult(
            task_type=TaskType.explanation,
            knowledge_points=[],
            difficulty=0.5,
            output_type="notes",
            confidence=0.1,
        )
