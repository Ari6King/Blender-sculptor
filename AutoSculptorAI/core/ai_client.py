import json
import urllib.request
import urllib.error
import base64
import os
import ssl


class AIClient:
    """Unified AI client supporting OpenAI, Anthropic, and Ollama."""

    def __init__(self, config):
        self.provider = config.get("provider", "OPENAI")
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "gpt-4o")
        self.ollama_url = config.get("ollama_url", "http://localhost:11434")

    def generate_sculpt_instructions(self, prompt, reference_analysis=None, knowledge_context=None):
        system_prompt = self._build_sculpt_system_prompt(knowledge_context)
        user_message = self._build_sculpt_user_message(prompt, reference_analysis)

        response = self._chat(system_prompt, user_message)
        return self._parse_sculpt_response(response)

    def analyze_image(self, image_path):
        if self.provider == "OPENAI":
            return self._openai_vision(image_path)
        elif self.provider == "ANTHROPIC":
            return self._anthropic_vision(image_path)
        elif self.provider == "OLLAMA":
            return self._ollama_vision(image_path)
        return None

    def analyze_texture(self, image_path):
        system_prompt = (
            "You are a texture analysis expert. Analyze the provided image and describe "
            "the surface material properties in detail. Return a JSON object with these fields:\n"
            "- base_color: [r, g, b] normalized 0-1\n"
            "- roughness: float 0-1\n"
            "- metallic: float 0-1\n"
            "- specular: float 0-1\n"
            "- normal_strength: float 0-2\n"
            "- description: brief material description\n"
            "- texture_type: one of [organic, metal, stone, wood, fabric, plastic, glass, skin]\n"
            "- color_variation: float 0-1 (how much color varies across the surface)\n"
            "Return ONLY valid JSON."
        )

        if self.provider == "OPENAI":
            return self._openai_vision_with_prompt(image_path, system_prompt)
        elif self.provider == "ANTHROPIC":
            return self._anthropic_vision_with_prompt(image_path, system_prompt)
        elif self.provider == "OLLAMA":
            return self._ollama_vision_with_prompt(image_path, system_prompt)
        return None

    def _build_sculpt_system_prompt(self, knowledge_context=None):
        base = (
            "You are an expert 3D sculptor AI assistant for Blender. You generate precise mesh "
            "data instructions that can be used to create 3D sculpted models programmatically.\n\n"
            "You MUST respond with a valid JSON object containing the following structure:\n"
            "{\n"
            '  "name": "object name",\n'
            '  "description": "brief description of the sculpt",\n'
            '  "base_shape": "sphere|cube|cylinder|cone|torus|icosphere|monkey",\n'
            '  "scale": [x, y, z],\n'
            '  "deformations": [\n'
            "    {\n"
            '      "type": "proportional_edit|displace|wave|twist|bend|taper|stretch|inflate",\n'
            '      "axis": "X|Y|Z",\n'
            '      "strength": float (-2.0 to 2.0),\n'
            '      "falloff": float (0.1 to 5.0),\n'
            '      "offset": [x, y, z] (normalized -1 to 1),\n'
            '      "params": {} (type-specific parameters)\n'
            "    }\n"
            "  ],\n"
            '  "sculpt_strokes": [\n'
            "    {\n"
            '      "brush": "draw|clay|clay_strips|inflate|grab|smooth|crease|pinch|flatten|scrape|snake_hook",\n'
            '      "points": [[x, y, z], ...],\n'
            '      "strength": float (0.0 to 1.0),\n'
            '      "radius": float (0.01 to 0.5),\n'
            '      "direction": "add|subtract"\n'
            "    }\n"
            "  ],\n"
            '  "modifiers": [\n'
            "    {\n"
            '      "type": "SUBSURF|MIRROR|SOLIDIFY|BEVEL|DISPLACE|SMOOTH|DECIMATE|REMESH",\n'
            '      "params": {}\n'
            "    }\n"
            "  ],\n"
            '  "vertex_groups": [\n'
            "    {\n"
            '      "name": "group name",\n'
            '      "vertex_weight_rule": "description of which vertices to include and weight"\n'
            "    }\n"
            "  ],\n"
            '  "material": {\n'
            '    "base_color": [r, g, b, a],\n'
            '    "roughness": float,\n'
            '    "metallic": float,\n'
            '    "specular": float\n'
            "  }\n"
            "}\n\n"
            "Guidelines:\n"
            "- Choose the base_shape that best matches the overall form\n"
            "- Use deformations to shape the overall silhouette\n"
            "- Use sculpt_strokes for fine details and surface features\n"
            "- Use modifiers for structural changes (mirror for symmetry, subsurf for smoothness)\n"
            "- Points in sculpt_strokes should be in normalized space (-1 to 1)\n"
            "- Be creative and detailed — the more sculpt_strokes, the more detailed the result\n"
            "- For organic forms, use many overlapping strokes with varying brush types\n"
            "- Return ONLY the JSON, no markdown formatting or extra text\n"
        )

        if knowledge_context:
            base += f"\n\nAdditional sculpting knowledge from Blender tutorials:\n{knowledge_context}\n"

        return base

    def _build_sculpt_user_message(self, prompt, reference_analysis=None):
        msg = f"Create a detailed 3D sculpt of: {prompt}"
        if reference_analysis:
            msg += f"\n\nReference image analysis: {reference_analysis}"
        return msg

    def _parse_sculpt_response(self, response):
        if not response:
            return None

        text = response.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
        return None

    def _chat(self, system_prompt, user_message):
        if self.provider == "OPENAI":
            return self._openai_chat(system_prompt, user_message)
        elif self.provider == "ANTHROPIC":
            return self._anthropic_chat(system_prompt, user_message)
        elif self.provider == "OLLAMA":
            return self._ollama_chat(system_prompt, user_message)
        return None

    def _openai_chat(self, system_prompt, user_message):
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.7,
            "max_tokens": 4096,
        }
        return self._http_post(url, headers, payload, extract_path=["choices", 0, "message", "content"])

    def _anthropic_chat(self, system_prompt, user_message):
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }
        return self._http_post(url, headers, payload, extract_path=["content", 0, "text"])

    def _ollama_chat(self, system_prompt, user_message):
        url = f"{self.ollama_url}/api/chat"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
        }
        return self._http_post(url, headers, payload, extract_path=["message", "content"])

    def _openai_vision(self, image_path):
        prompt = (
            "Analyze this image for 3D sculpting reference. Describe:\n"
            "1. The overall shape and silhouette\n"
            "2. Key structural features and proportions\n"
            "3. Surface details and textures\n"
            "4. Any symmetry or patterns\n"
            "5. Suggested base shape (sphere, cube, cylinder, etc.)\n"
            "Be specific and technical — this will be used to guide 3D mesh generation."
        )
        return self._openai_vision_with_prompt(image_path, prompt)

    def _openai_vision_with_prompt(self, image_path, prompt):
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        ext = os.path.splitext(image_path)[1].lower()
        mime_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                      ".webp": "image/webp", ".gif": "image/gif"}
        mime = mime_types.get(ext, "image/png")

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model if "gpt-4" in self.model else "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{image_data}"},
                        },
                    ],
                }
            ],
            "max_tokens": 2048,
        }
        return self._http_post(url, headers, payload, extract_path=["choices", 0, "message", "content"])

    def _anthropic_vision(self, image_path):
        prompt = (
            "Analyze this image for 3D sculpting reference. Describe the shape, "
            "structure, proportions, surface details, and suggest a base 3D shape."
        )
        return self._anthropic_vision_with_prompt(image_path, prompt)

    def _anthropic_vision_with_prompt(self, image_path, prompt):
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        ext = os.path.splitext(image_path)[1].lower()
        mime_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                      ".webp": "image/webp", ".gif": "image/gif"}
        mime = mime_types.get(ext, "image/png")

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": self.model,
            "max_tokens": 2048,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime,
                                "data": image_data,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        return self._http_post(url, headers, payload, extract_path=["content", 0, "text"])

    def _ollama_vision(self, image_path):
        return self._ollama_vision_with_prompt(
            image_path,
            "Analyze this image for 3D sculpting. Describe shape, structure, and details.",
        )

    def _ollama_vision_with_prompt(self, image_path, prompt):
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        url = f"{self.ollama_url}/api/chat"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": "llava",
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_data],
                }
            ],
            "stream": False,
        }
        return self._http_post(url, headers, payload, extract_path=["message", "content"])

    def _http_post(self, url, headers, payload, extract_path=None):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        ctx = ssl.create_default_context()

        try:
            with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))
                if extract_path:
                    result = response_data
                    for key in extract_path:
                        if isinstance(result, list):
                            result = result[key]
                        elif isinstance(result, dict):
                            result = result[key]
                        else:
                            return None
                    return result
                return response_data
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"API request failed ({e.code}): {error_body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Connection error: {e.reason}")
        except Exception as e:
            raise RuntimeError(f"Request failed: {str(e)}")
