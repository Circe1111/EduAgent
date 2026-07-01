import json
from typing import List

from app.agents.base import BaseAgent
from app.core.llm import LLMClient
from app.models.plan import LearningPath, PathNode
from app.models.session_context import SessionContext


class LearningPathAgent(BaseAgent):
    """
    Agent that generates a personalised learning path based on the
    student's current mastery, target knowledge points, and history.
    """

    name = "learning_path"

    SYSTEM_PROMPT = (
        "你是一位专业的Python学习路径规划专家。请根据学生的当前水平和目标，"
        "生成个性化的学习路径。\n\n"
        "输出要求（JSON格式）：\n"
        '{\n'
        '    "nodes": [\n'
        '        {\n'
        '            "knowledge_point": "知识点名称",\n'
        '            "order": 1,\n'
        '            "resources": ["资源ID或参考链接"],\n'
        '            "estimated_time": "30m",\n'
        '            "prerequisites": ["前置知识点1", "前置知识点2"]\n'
        '        }\n'
        '    ],\n'
        '    "total_estimated_time": "总时长"\n'
        '}\n\n'
        "规则：\n"
        "1. 节点按order从小到大排序\n"
        "2. 每个知识点的prerequisites必须在nodes中且order小于当前节点\n"
        "3. 不要出现循环依赖\n"
        "4. 根据学生已掌握的知识点调整路径：已掌握的可以跳过或快速复习\n"
        "5. 时间估计要合理，格式如\"15m\", \"1h\", \"2h30m\"\n"
        "6. 只输出JSON，不要其他文字"
    )

    def __init__(self) -> None:
        self.llm = LLMClient()

    async def process(self, context: SessionContext) -> SessionContext:
        if not await self.validate_input(context):
            return context.add_error("LearningPathAgent: invalid input context")

        try:
            profile = context.student_profile

            # New user with no data -> default intro path
            if profile is None or not profile.knowledge_points:
                context.learning_plan = self._default_intro_path()
                return context

            target_kps = context.knowledge_points
            if context.task_intent is not None and context.task_intent.knowledge_points:
                target_kps = context.task_intent.knowledge_points

            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": self._build_planning_prompt(profile, target_kps),
                },
            ]

            # Use routed model and temperature from intent analysis
            selected_model = context.metadata.get("selected_model")
            temperature = context.metadata.get("temperature", 0.5)

            response = await self.llm.chat(
                messages,
                model=selected_model,
                temperature=temperature,
                max_tokens=2048,
            )
            raw = response.get("content", "")

            path = self._parse_path(raw)
            path = self._validate_path(path)

            context.learning_plan = path

        except Exception as exc:
            context = await self.handle_error(context, exc)
            context.learning_plan = self._default_intro_path()

        return context

    def _build_planning_prompt(
        self, profile, target_kps: List[str]
    ) -> str:
        """Build the planning prompt from profile and targets."""
        parts: list[str] = []
        parts.append(f"学生已掌握知识点及熟练度：{profile.knowledge_points}")
        parts.append(f"整体难度偏好：{profile.overall_difficulty}")
        parts.append(f"学习风格：{profile.learning_style}")
        parts.append(f"目标知识点：{target_kps}")
        return "\n\n".join(parts)

    def _parse_path(self, raw: str) -> LearningPath:
        """Parse LLM JSON output into LearningPath."""
        try:
            json_str = raw
            if "```json" in raw:
                json_str = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                json_str = raw.split("```")[1].split("```")[0].strip()

            data = json.loads(json_str)
            nodes_data = data.get("nodes", [])
            nodes: List[PathNode] = []
            for n in nodes_data:
                nodes.append(
                    PathNode(
                        knowledge_point=n.get("knowledge_point", "未知"),
                        order=n.get("order", 0),
                        resources=n.get("resources", []),
                        estimated_time=n.get("estimated_time", "30m"),
                        prerequisites=n.get("prerequisites", []),
                    )
                )

            return LearningPath(
                nodes=nodes,
                total_estimated_time=data.get("total_estimated_time", "未知"),
            )

        except Exception:
            return self._default_intro_path()

    def _validate_path(self, path: LearningPath) -> LearningPath:
        """
        Validate and repair the learning path:
        - Ensure no cycles
        - Ensure prerequisites appear before dependents
        """
        if not path.nodes:
            return path

        sorted_nodes = sorted(path.nodes, key=lambda n: n.order)
        kp_set = {n.knowledge_point for n in sorted_nodes}

        validated: List[PathNode] = []
        for node in sorted_nodes:
            # Keep only prerequisites that exist in the path
            valid_prereqs = [p for p in node.prerequisites if p in kp_set]

            # Ensure each prerequisite has a lower order
            for p in valid_prereqs:
                prereq_nodes = [n for n in sorted_nodes if n.knowledge_point == p]
                if prereq_nodes and prereq_nodes[0].order >= node.order:
                    node.order = prereq_nodes[0].order + 1

            validated.append(node)

        validated.sort(key=lambda n: n.order)
        return LearningPath(
            nodes=validated,
            total_estimated_time=path.total_estimated_time,
        )

    def _default_intro_path(self) -> LearningPath:
        """Default introductory path for brand-new users."""
        return LearningPath(
            nodes=[
                PathNode(
                    knowledge_point="Python基础语法",
                    order=1,
                    resources=["intro_python"],
                    estimated_time="1h",
                    prerequisites=[],
                ),
                PathNode(
                    knowledge_point="变量与数据类型",
                    order=2,
                    resources=["variables_types"],
                    estimated_time="45m",
                    prerequisites=["Python基础语法"],
                ),
                PathNode(
                    knowledge_point="控制流",
                    order=3,
                    resources=["control_flow"],
                    estimated_time="1h",
                    prerequisites=["变量与数据类型"],
                ),
            ],
            total_estimated_time="2h45m",
        )
