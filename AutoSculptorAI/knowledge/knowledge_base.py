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
