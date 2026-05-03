import json
import os
from .ai_client import AIClient
from .reference_analyzer import ReferenceAnalyzer
from ..knowledge.knowledge_base import KnowledgeBase


class SculptEngine:
    """Orchestrates AI-driven sculpting: prompt analysis, reference processing, and mesh generation."""

    def __init__(self, config):
        self.config = config
        self.ai_client = AIClient(config)
        self.prompt = config.get("prompt", "")
        self.detail_level = config.get("detail_level", "MEDIUM")
        self.subdivisions = config.get("subdivisions", 4)
        self.smooth_iterations = config.get("smooth_iterations", 3)
        self.symmetry = config.get("symmetry", True)
        self.ref_image_path = config.get("ref_image_path")
        self.use_knowledge = config.get("use_knowledge", False)
        self.knowledge_db_path = config.get("knowledge_db_path")

    def generate(self):
        try:
            reference_analysis = None
            if self.ref_image_path and os.path.isfile(self.ref_image_path):
                analyzer = ReferenceAnalyzer(self.config)
                reference_analysis = analyzer.analyze(self.ref_image_path)

            knowledge_context = None
            if self.use_knowledge:
                kb = KnowledgeBase(db_path=self.knowledge_db_path)
                knowledge_context = kb.get_relevant_knowledge(self.prompt)

            enhanced_prompt = self._enhance_prompt(self.prompt)

            mesh_data = self.ai_client.generate_sculpt_instructions(
                enhanced_prompt,
                reference_analysis=reference_analysis,
                knowledge_context=knowledge_context,
            )

            if not mesh_data:
                return {"success": False, "error": "AI did not return valid sculpting data"}

            mesh_data = self._apply_detail_level(mesh_data)

            if self.symmetry and not any(
                m.get("type") == "MIRROR" for m in mesh_data.get("modifiers", [])
            ):
                mesh_data.setdefault("modifiers", []).insert(
                    0, {"type": "MIRROR", "params": {"use_axis": [True, False, False], "use_clip": True}}
                )

            return {
                "success": True,
                "mesh_data": mesh_data,
                "api_key": self.config.get("api_key", ""),
                "model": self.config.get("model", ""),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _enhance_prompt(self, prompt):
        detail_hints = {
            "LOW": "Keep the model simple with minimal detail. Use broad strokes and basic shapes.",
            "MEDIUM": "Create a model with moderate detail. Include key features and some surface detail.",
            "HIGH": "Create a highly detailed model with fine surface details, defined edges, and nuanced forms.",
            "ULTRA": (
                "Create an extremely detailed model with maximum surface detail, micro-details, "
                "sharp creases, fine wrinkles, intricate patterns, and professional-quality sculpting."
            ),
        }

        hint = detail_hints.get(self.detail_level, detail_hints["MEDIUM"])
        enhanced = f"{prompt}\n\nDetail level: {hint}"

        if self.symmetry:
            enhanced += "\nThe model should be symmetrical along the X axis where appropriate."

        return enhanced

    def _apply_detail_level(self, mesh_data):
        stroke_multipliers = {"LOW": 0.5, "MEDIUM": 1.0, "HIGH": 2.0, "ULTRA": 3.0}
        multiplier = stroke_multipliers.get(self.detail_level, 1.0)

        if multiplier != 1.0 and "sculpt_strokes" in mesh_data:
            strokes = mesh_data["sculpt_strokes"]
            if multiplier < 1.0:
                mesh_data["sculpt_strokes"] = strokes[: max(1, int(len(strokes) * multiplier))]
            elif multiplier > 1.0:
                extra_strokes = []
                for stroke in strokes:
                    for i in range(int(multiplier) - 1):
                        new_stroke = stroke.copy()
                        new_stroke["strength"] = stroke.get("strength", 0.5) * (0.5 + i * 0.2)
                        new_stroke["radius"] = stroke.get("radius", 0.1) * (0.8 - i * 0.1)
                        if "points" in new_stroke:
                            offset = 0.02 * (i + 1)
                            new_stroke["points"] = [
                                [p[0] + offset, p[1] + offset, p[2]]
                                for p in stroke["points"]
                            ]
                        extra_strokes.append(new_stroke)
                mesh_data["sculpt_strokes"] = strokes + extra_strokes

        subdiv_levels = {"LOW": max(1, self.subdivisions - 2), "MEDIUM": self.subdivisions,
                         "HIGH": min(6, self.subdivisions + 1), "ULTRA": min(8, self.subdivisions + 2)}
        actual_subdivisions = subdiv_levels.get(self.detail_level, self.subdivisions)

        has_subsurf = False
        for mod in mesh_data.get("modifiers", []):
            if mod.get("type") == "SUBSURF":
                mod.setdefault("params", {})["levels"] = actual_subdivisions
                mod["params"]["render_levels"] = actual_subdivisions
                has_subsurf = True

        if not has_subsurf:
            mesh_data.setdefault("modifiers", []).append(
                {
                    "type": "SUBSURF",
                    "params": {"levels": actual_subdivisions, "render_levels": actual_subdivisions},
                }
            )

        return mesh_data
