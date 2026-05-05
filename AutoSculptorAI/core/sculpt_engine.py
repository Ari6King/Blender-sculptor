import json
import os
from .ai_client import AIClient
from .reference_analyzer import ReferenceAnalyzer
from ..knowledge.knowledge_base import KnowledgeBase
from .learning_engine import LearningEngine


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
        self.knowledge_db_path = config.get("knowledge_db_path")
        self.meshy_api_key = config.get("meshy_api_key", "")
        self.generation_mode = config.get("generation_mode", "AUTO")
        self._progress_callback = None

    def set_progress_callback(self, callback):
        self._progress_callback = callback

    def _resolve_mode(self):
        """Decide which generation tool to use based on explicit user choice."""
        mode = self.generation_mode
        if mode == "MESHY":
            if not self.meshy_api_key:
                raise ValueError(
                    "Meshy 3D mode selected but no Meshy API key is set. "
                    "Add your key in addon preferences or switch to AI Sculpt mode."
                )
            return "meshy"
        elif mode == "SCULPT":
            return "llm"
        else:
            if self.meshy_api_key:
                return "meshy"
            return "llm"

    def generate(self):
        resolved = self._resolve_mode()
        if self._progress_callback:
            self._progress_callback(f"Using {'Meshy 3D' if resolved == 'meshy' else 'AI Sculpt'} mode...", 5.0)
        if resolved == "meshy":
            return self._generate_with_meshy()
        return self._generate_with_llm()

    def _generate_with_meshy(self):
        try:
            from .meshy_client import MeshyClient

            enhanced_prompt = self._build_meshy_prompt()

            client = MeshyClient(self.meshy_api_key)

            model_type = "standard"
            if self.detail_level == "LOW":
                model_type = "lowpoly"

            result = client.text_to_3d(
                prompt=enhanced_prompt,
                model_type=model_type,
                enable_pbr=True,
                target_format="glb",
                on_progress=self._progress_callback,
            )

            return {
                "success": True,
                "mode": "meshy",
                "file_path": result["file_path"],
                "format": result["format"],
                "texture_urls": result.get("texture_urls", {}),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _build_meshy_prompt(self):
        """Enrich the user prompt with knowledge and reference analysis for Meshy."""
        parts = [self.prompt]

        if self.ref_image_path and os.path.isfile(self.ref_image_path):
            try:
                analyzer = ReferenceAnalyzer(self.config)
                analysis = analyzer.analyze(self.ref_image_path)
                if analysis:
                    parts.append(f"Reference details: {analysis}")
            except Exception:
                pass

        kb = KnowledgeBase(db_path=self.knowledge_db_path)
        builtin = kb.get_builtin_knowledge(self.prompt)
        scraped = kb.get_relevant_knowledge(self.prompt)
        knowledge = ""
        if builtin and scraped:
            knowledge = builtin + " " + scraped
        elif builtin or scraped:
            knowledge = builtin or scraped
        if knowledge:
            parts.append(f"Style guidance: {knowledge[:200]}")

        return ". ".join(parts)[:600]

    def _generate_with_llm(self):
        try:
            reference_analysis = None
            if self.ref_image_path and os.path.isfile(self.ref_image_path):
                analyzer = ReferenceAnalyzer(self.config)
                reference_analysis = analyzer.analyze(self.ref_image_path)

            kb = KnowledgeBase(db_path=self.knowledge_db_path)
            builtin_context = kb.get_builtin_knowledge(self.prompt)
            scraped_context = kb.get_relevant_knowledge(self.prompt)

            if builtin_context and scraped_context:
                knowledge_context = builtin_context + "\n\n" + scraped_context
            else:
                knowledge_context = builtin_context or scraped_context

            le = LearningEngine(db_path=self.knowledge_db_path)
            learned_rules = le.format_rules_for_prompt(self.prompt)
            if learned_rules:
                if knowledge_context:
                    knowledge_context += "\n\n" + learned_rules
                else:
                    knowledge_context = learned_rules

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
                "mode": "llm",
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
                                if len(p) >= 3
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
