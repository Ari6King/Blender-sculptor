import json
import os
import re


class KnowledgeBase:
    """Stores and retrieves sculpting knowledge for AI-enhanced generation."""

    DEFAULT_DB_DIR = os.path.join(os.path.expanduser("~"), ".autosculptor_ai")
    DEFAULT_DB_FILE = "knowledge.json"

    def __init__(self, db_path=None):
        if db_path:
            self.db_dir = db_path
        else:
            self.db_dir = self.DEFAULT_DB_DIR

        self.db_file = os.path.join(self.db_dir, self.DEFAULT_DB_FILE)
        self._ensure_db()

    def _ensure_db(self):
        os.makedirs(self.db_dir, exist_ok=True)
        if not os.path.isfile(self.db_file):
            self._save({"entries": [], "metadata": {"version": 1, "total_entries": 0}})

    def _load(self):
        try:
            with open(self.db_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"entries": [], "metadata": {"version": 1, "total_entries": 0}}

    def _save(self, data):
        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def store(self, topic, content, category="general", source="manual"):
        data = self._load()

        for entry in data["entries"]:
            if entry["topic"] == topic and entry["source"] == source:
                entry["content"] = content
                entry["category"] = category
                self._save(data)
                return

        entry = {
            "topic": topic,
            "content": content,
            "category": category,
            "source": source,
        }
        data["entries"].append(entry)
        data["metadata"]["total_entries"] = len(data["entries"])
        self._save(data)

    def get_relevant_knowledge(self, prompt, max_results=5):
        data = self._load()
        entries = data.get("entries", [])

        if not entries:
            return None

        prompt_lower = prompt.lower()
        keywords = set(re.findall(r"\b\w{3,}\b", prompt_lower))

        scored_entries = []
        for entry in entries:
            score = 0
            entry_text = f"{entry['topic']} {entry['content']}".lower()

            for keyword in keywords:
                if keyword in entry_text:
                    score += 1
                    if keyword in entry["topic"].lower():
                        score += 2

            sculpt_terms = {
                "sculpt", "mesh", "vertex", "face", "edge", "brush", "smooth",
                "detail", "subdivide", "remesh", "mirror", "symmetry", "texture",
                "material", "deform", "shape", "organic", "character", "creature",
                "head", "body", "armor", "weapon", "dragon", "skull",
            }
            for term in sculpt_terms:
                if term in prompt_lower and term in entry_text:
                    score += 1

            if score > 0:
                scored_entries.append((score, entry))

        scored_entries.sort(key=lambda x: x[0], reverse=True)
        top_entries = scored_entries[:max_results]

        if not top_entries:
            categories = {"technique", "workflow"}
            fallback = [e for e in entries if e.get("category") in categories][:max_results]
            if fallback:
                top_entries = [(1, e) for e in fallback]

        if not top_entries:
            return None

        context_parts = []
        for score, entry in top_entries:
            context_parts.append(f"[{entry['topic']}] ({entry['category']}): {entry['content']}")

        return "\n\n".join(context_parts)

    def get_all_entries(self):
        data = self._load()
        return data.get("entries", [])

    def get_by_category(self, category):
        data = self._load()
        return [e for e in data.get("entries", []) if e.get("category") == category]

    def clear(self):
        self._save({"entries": [], "metadata": {"version": 1, "total_entries": 0}})

    BUILTIN_KNOWLEDGE = [
        {
            "topic": "Base Mesh Selection",
            "content": (
                "Choosing the right base mesh is crucial for sculpting. Use a sphere for heads "
                "and organic round forms. Use a cube for hard-surface objects and architectural "
                "elements. Use a cylinder for limbs, columns, and elongated forms. Use an "
                "icosphere for uniform topology distribution. Use the Monkey (Suzanne) as a "
                "starting point for character heads."
            ),
            "category": "technique",
        },
        {
            "topic": "Subdivision Workflow",
            "content": (
                "Start with low subdivision for blocking out the major forms (levels 1-2). "
                "Increase subdivision for adding secondary forms (levels 3-4). Use high "
                "subdivision for fine details like pores and wrinkles (levels 5-6). Use "
                "Multires modifier for non-destructive subdivision sculpting."
            ),
            "category": "workflow",
        },
        {
            "topic": "Brush Techniques",
            "content": (
                "Draw brush: Build up form by adding/removing volume. Clay Strips: Add broad "
                "flat strokes for muscle/form definition. Inflate: Push vertices outward along "
                "normals for puffing up areas. Crease: Create sharp creases and wrinkles. "
                "Grab: Move vertices freely for major form adjustments. Smooth: Blend and "
                "soften surface details. Pinch: Sharpen edges and creases. Flatten: Level "
                "surfaces to a uniform height. Snake Hook: Drag and pull surface for tentacles, "
                "horns, and flowing shapes."
            ),
            "category": "technique",
        },
        {
            "topic": "Symmetry in Sculpting",
            "content": (
                "Enable X-axis symmetry for character and creature sculpting. Use the Mirror "
                "modifier for perfect symmetry. Break symmetry only after main forms are "
                "established. Use Radial symmetry for flowers, eyes, and circular patterns."
            ),
            "category": "technique",
        },
        {
            "topic": "Retopology",
            "content": (
                "After sculpting, create a clean topology mesh using Remesh or manual retopo. "
                "Voxel Remesh creates uniform quads. QuadriFlow Remesh creates flow-following "
                "quads. Use Shrinkwrap modifier to project retopo mesh onto sculpt."
            ),
            "category": "workflow",
        },
        {
            "topic": "Texture Painting",
            "content": (
                "UV unwrap the model before texture painting. Use Smart UV Project for quick "
                "unwrapping. Projection painting allows painting from multiple angles. Use "
                "stencil mapping to project reference images onto the surface. Bake high-poly "
                "details to normal maps for low-poly meshes."
            ),
            "category": "technique",
        },
        {
            "topic": "Material Setup for Sculpts",
            "content": (
                "Use Principled BSDF for physically-based materials. Set base color from "
                "reference images. Use roughness maps for surface variation. Add normal maps "
                "for micro-detail. Use subsurface scattering for skin and organic materials. "
                "Use metallic for armors, weapons, and metal objects."
            ),
            "category": "materials",
        },
        {
            "topic": "Procedural Deformation",
            "content": (
                "Simple Deform modifier types: Twist rotates mesh around an axis, Bend curves "
                "mesh around a point, Taper scales along an axis, Stretch elongates along an "
                "axis. Displace modifier pushes vertices along normals using a texture. Lattice "
                "provides broad deformation control. Use these for major shape adjustments "
                "before fine sculpting."
            ),
            "category": "technique",
        },
    ]

    def get_builtin_knowledge(self, prompt, max_results=5):
        prompt_lower = prompt.lower()
        keywords = set(re.findall(r"\b\w{3,}\b", prompt_lower))

        scored = []
        for entry in self.BUILTIN_KNOWLEDGE:
            score = 0
            entry_text = f"{entry['topic']} {entry['content']}".lower()
            for keyword in keywords:
                if keyword in entry_text:
                    score += 1
                    if keyword in entry["topic"].lower():
                        score += 2
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:max_results]

        if not top:
            top = [(1, e) for e in self.BUILTIN_KNOWLEDGE if e.get("category") in {"technique", "workflow"}][:max_results]

        parts = []
        for _, entry in top:
            parts.append(f"[{entry['topic']}] ({entry['category']}): {entry['content']}")
        return "\n\n".join(parts) if parts else None

    def get_stats(self):
        data = self._load()
        entries = data.get("entries", [])
        categories = {}
        sources = {}
        for entry in entries:
            cat = entry.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
            src = entry.get("source", "unknown")
            if src.startswith("http"):
                src = "web"
            sources[src] = sources.get(src, 0) + 1

        return {
            "total_entries": len(entries),
            "categories": categories,
            "sources": sources,
        }
