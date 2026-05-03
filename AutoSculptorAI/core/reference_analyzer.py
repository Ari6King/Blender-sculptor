import os
from .ai_client import AIClient


class ReferenceAnalyzer:
    """Analyzes reference images using AI vision to extract 3D sculpting guidance."""

    def __init__(self, config):
        self.config = config
        self.ai_client = AIClient(config)

    def analyze(self, image_path):
        if not image_path or not os.path.isfile(image_path):
            return None

        valid_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"}
        ext = os.path.splitext(image_path)[1].lower()
        if ext not in valid_extensions:
            return None

        try:
            analysis = self.ai_client.analyze_image(image_path)
            return analysis
        except Exception as e:
            print(f"Auto Sculptor AI: Reference analysis error: {e}")
            return None

    def analyze_for_shape(self, image_path):
        if not image_path or not os.path.isfile(image_path):
            return None

        prompt = (
            "Analyze this image and determine the best 3D sculpting approach. Return a JSON with:\n"
            "1. suggested_base_shape: sphere, cube, cylinder, cone, torus, icosphere\n"
            "2. proportions: [width, height, depth] relative ratios\n"
            "3. symmetry: {x: bool, y: bool, z: bool}\n"
            "4. key_features: list of main visual features to sculpt\n"
            "5. surface_type: smooth, rough, organic, hard_surface, mixed\n"
            "6. complexity: low, medium, high\n"
            "7. sculpting_notes: brief professional sculpting advice\n"
            "Return ONLY valid JSON."
        )

        try:
            if self.config.get("provider") == "OPENAI":
                result = self.ai_client._openai_vision_with_prompt(image_path, prompt)
            elif self.config.get("provider") == "ANTHROPIC":
                result = self.ai_client._anthropic_vision_with_prompt(image_path, prompt)
            else:
                result = self.ai_client.analyze_image(image_path)
            return result
        except Exception as e:
            print(f"Auto Sculptor AI: Shape analysis error: {e}")
            return None
