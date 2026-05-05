import json
import math
import os
import re


# (C) Structured categories with semantic keywords for auto-tagging
CATEGORY_KEYWORDS = {
    "organic_sculpting": {
        "keywords": ["organic", "creature", "character", "body", "head", "face",
                      "anatomy", "skin", "muscle", "flesh", "animal", "human",
                      "dragon", "monster", "beast", "skull", "torso", "limb"],
        "label": "Organic Sculpting",
    },
    "hard_surface": {
        "keywords": ["hard", "surface", "mechanical", "robot", "armor", "weapon",
                      "sword", "shield", "vehicle", "architecture", "building",
                      "metal", "panel", "bolt", "rivet", "edge", "bevel"],
        "label": "Hard Surface Modeling",
    },
    "brush_technique": {
        "keywords": ["brush", "stroke", "draw", "clay", "inflate", "grab",
                      "smooth", "crease", "pinch", "flatten", "scrape",
                      "snake", "hook", "mask", "trim"],
        "label": "Brush Techniques",
    },
    "topology": {
        "keywords": ["topology", "retopo", "remesh", "quad", "polygon", "mesh",
                      "vertex", "edge", "face", "loop", "flow", "subdivision",
                      "multires", "decimate", "wireframe"],
        "label": "Topology & Mesh",
    },
    "materials_textures": {
        "keywords": ["material", "texture", "uv", "unwrap", "bsdf", "shader",
                      "color", "roughness", "metallic", "normal", "bump",
                      "paint", "bake", "pbr", "specular", "emission"],
        "label": "Materials & Textures",
    },
    "workflow": {
        "keywords": ["workflow", "pipeline", "process", "step", "stage",
                      "blockout", "refine", "polish", "export", "import",
                      "render", "setup", "modifier", "mirror", "symmetry"],
        "label": "Workflow & Pipeline",
    },
    "anatomy": {
        "keywords": ["anatomy", "proportion", "skeleton", "bone", "joint",
                      "eye", "nose", "mouth", "ear", "hand", "foot",
                      "finger", "arm", "leg", "spine", "rib"],
        "label": "Anatomy & Proportions",
    },
}


def auto_categorize(text):
    """Determine the best category for a piece of text based on keyword density."""
    text_lower = text.lower()
    scores = {}
    for cat_id, cat_data in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in cat_data["keywords"] if kw in text_lower)
        if score > 0:
            scores[cat_id] = score
    if scores:
        return max(scores, key=scores.get)
    return "general"


def _tokenize(text):
    """Split text into lowercase word tokens (3+ chars)."""
    return re.findall(r"\b[a-z]{3,}\b", text.lower())


def _compute_idf(all_entries):
    """Compute inverse document frequency for all terms across entries."""
    n_docs = len(all_entries)
    if n_docs == 0:
        return {}
    doc_freq = {}
    for entry in all_entries:
        entry_text = f"{entry.get('topic', '')} {entry.get('content', '')}"
        terms = set(_tokenize(entry_text))
        for term in terms:
            doc_freq[term] = doc_freq.get(term, 0) + 1
    idf = {}
    for term, df in doc_freq.items():
        idf[term] = math.log((n_docs + 1) / (df + 1)) + 1
    return idf


def _score_entry(entry, query_tokens, query_token_set, idf):
    """Score an entry against a query using TF-IDF style weighting."""
    entry_text = f"{entry.get('topic', '')} {entry.get('content', '')}"
    entry_tokens = _tokenize(entry_text)
    if not entry_tokens:
        return 0.0

    entry_token_counts = {}
    for t in entry_tokens:
        entry_token_counts[t] = entry_token_counts.get(t, 0) + 1

    topic_tokens = set(_tokenize(entry.get("topic", "")))
    max_tf = max(entry_token_counts.values()) if entry_token_counts else 1

    score = 0.0
    matched_terms = 0
    for qt in query_token_set:
        tf = entry_token_counts.get(qt, 0)
        if tf == 0:
            continue
        matched_terms += 1
        normalized_tf = 0.5 + 0.5 * (tf / max_tf)
        term_idf = idf.get(qt, 1.0)
        term_score = normalized_tf * term_idf
        if qt in topic_tokens:
            term_score *= 3.0
        score += term_score

    if matched_terms > 0:
        coverage = matched_terms / max(len(query_token_set), 1)
        score *= (0.5 + 0.5 * coverage)

    return score


class KnowledgeBase:
    """Stores and retrieves sculpting knowledge with TF-IDF ranking and structured categories."""

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
            self._save({"entries": [], "scraped_sources": [], "metadata": {"version": 2, "total_entries": 0}})

    def _load(self):
        try:
            with open(self.db_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"entries": [], "scraped_sources": [], "metadata": {"version": 2, "total_entries": 0}}

    def _save(self, data):
        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def store(self, topic, content, category="general", source="manual"):
        """Store knowledge with auto-categorization if category is 'general'."""
        data = self._load()

        if category == "general":
            category = auto_categorize(f"{topic} {content}")

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

    def store_distilled(self, topic, raw_content, category="general", source="manual"):
        """Store content after distilling it into concise, actionable knowledge.

        Extracts key techniques, tips, and instructions from raw content
        (e.g. YouTube transcripts, documentation pages) and stores a
        condensed version.
        """
        distilled = self._distill_content(topic, raw_content)
        if category == "general":
            category = auto_categorize(f"{topic} {distilled}")
        self.store(topic, distilled, category=category, source=source)

    def _distill_content(self, topic, raw_content):
        """Distill raw content into concise, actionable sculpting knowledge."""
        sentences = re.split(r'[.!?]+', raw_content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 15]

        action_patterns = [
            r'\b(use|apply|create|add|set|enable|disable|adjust|increase|decrease)\b',
            r'\b(start with|begin by|first|then|next|finally|make sure)\b',
            r'\b(tip|trick|important|key|best practice|recommend|should|avoid)\b',
            r'\b(brush|stroke|mesh|vertex|edge|face|modifier|sculpt|texture)\b',
            r'\b(strength|radius|detail|subdivision|smooth|mirror|symmetry)\b',
        ]

        scored_sentences = []
        for sent in sentences:
            sent_lower = sent.lower()
            score = 0
            for pattern in action_patterns:
                matches = re.findall(pattern, sent_lower)
                score += len(matches) * 2

            filler_patterns = [
                r'\b(um|uh|like|you know|basically|actually|literally)\b',
                r'\b(hey guys|welcome|subscribe|click|notification|bell)\b',
                r'\b(patreon|sponsor|link in description)\b',
            ]
            for pattern in filler_patterns:
                if re.search(pattern, sent_lower):
                    score -= 5

            if len(sent) > 20:
                score += 1

            scored_sentences.append((score, sent))

        scored_sentences.sort(key=lambda x: x[0], reverse=True)

        kept = []
        char_count = 0
        max_chars = 800
        for score, sent in scored_sentences:
            if score <= 0:
                continue
            if char_count + len(sent) > max_chars:
                continue
            kept.append(sent)
            char_count += len(sent)

        if not kept:
            kept = [s for _, s in scored_sentences[:3]]

        return ". ".join(kept) + "."

    def get_relevant_knowledge(self, prompt, max_results=5):
        """Retrieve knowledge ranked by TF-IDF relevance to the prompt."""
        data = self._load()
        entries = data.get("entries", [])

        if not entries:
            return None

        query_tokens = _tokenize(prompt)
        query_token_set = set(query_tokens)

        if not query_token_set:
            return None

        idf = _compute_idf(entries)

        prompt_category = auto_categorize(prompt)

        scored_entries = []
        for entry in entries:
            score = _score_entry(entry, query_tokens, query_token_set, idf)
            if entry.get("category") == prompt_category:
                score *= 1.5
            if score > 0:
                scored_entries.append((score, entry))

        scored_entries.sort(key=lambda x: x[0], reverse=True)
        top_entries = scored_entries[:max_results]

        if not top_entries:
            cat_entries = [e for e in entries if e.get("category") == prompt_category]
            if cat_entries:
                top_entries = [(1.0, e) for e in cat_entries[:max_results]]

        if not top_entries:
            tech_entries = [e for e in entries
                           if e.get("category") in {"brush_technique", "workflow", "technique"}]
            if tech_entries:
                top_entries = [(1.0, e) for e in tech_entries[:max_results]]

        if not top_entries:
            return None

        context_parts = []
        for score, entry in top_entries:
            cat_label = CATEGORY_KEYWORDS.get(entry.get("category", ""), {}).get("label", entry.get("category", ""))
            context_parts.append(f"[{entry['topic']}] ({cat_label}): {entry['content']}")

        return "\n\n".join(context_parts)

    def get_all_entries(self):
        data = self._load()
        return data.get("entries", [])

    def get_by_category(self, category):
        data = self._load()
        return [e for e in data.get("entries", []) if e.get("category") == category]

    def is_source_scraped(self, source_url):
        """Check if a URL or video ID has already been scraped."""
        data = self._load()
        return source_url in data.get("scraped_sources", [])

    def mark_source_scraped(self, source_url):
        """Record that a URL or video ID has been scraped."""
        data = self._load()
        scraped = data.get("scraped_sources", [])
        if source_url not in scraped:
            scraped.append(source_url)
            data["scraped_sources"] = scraped
            self._save(data)

    def clear(self):
        self._save({"entries": [], "scraped_sources": [], "metadata": {"version": 2, "total_entries": 0}})

    BUILTIN_KNOWLEDGE = [
        {
            "topic": "Base Mesh Selection",
            "content": (
                "Use a sphere for heads and organic round forms. Use a cube for hard-surface "
                "objects. Use a cylinder for limbs and elongated forms. Use an icosphere for "
                "uniform topology. Use Suzanne for character head practice."
            ),
            "category": "topology",
        },
        {
            "topic": "Subdivision Workflow",
            "content": (
                "Start at levels 1-2 for blocking major forms. Increase to 3-4 for secondary "
                "forms. Use levels 5-6 for fine details like pores and wrinkles. Use Multires "
                "modifier for non-destructive subdivision sculpting."
            ),
            "category": "workflow",
        },
        {
            "topic": "Brush Techniques",
            "content": (
                "Draw brush: add/remove volume. Clay Strips: broad flat strokes for muscle "
                "definition. Inflate: push vertices outward along normals. Crease: sharp "
                "creases and wrinkles. Grab: move vertices for major form adjustments. "
                "Smooth: blend and soften surface. Pinch: sharpen edges. Flatten: level "
                "surfaces. Snake Hook: drag surface for tentacles, horns, flowing shapes."
            ),
            "category": "brush_technique",
        },
        {
            "topic": "Symmetry in Sculpting",
            "content": (
                "Enable X-axis symmetry for character and creature sculpting. Use Mirror "
                "modifier for perfect symmetry. Break symmetry only after main forms are "
                "established. Use Radial symmetry for flowers, eyes, circular patterns."
            ),
            "category": "workflow",
        },
        {
            "topic": "Retopology Workflow",
            "content": (
                "After sculpting, create clean topology using Remesh. Voxel Remesh creates "
                "uniform quads. QuadriFlow creates flow-following quads. Use Shrinkwrap "
                "modifier to project retopo mesh onto sculpt."
            ),
            "category": "topology",
        },
        {
            "topic": "Texture Painting",
            "content": (
                "UV unwrap before texture painting. Use Smart UV Project for quick unwrapping. "
                "Projection painting allows painting from multiple angles. Use stencil mapping "
                "to project reference images onto surfaces. Bake high-poly details to normal "
                "maps for low-poly meshes."
            ),
            "category": "materials_textures",
        },
        {
            "topic": "Material Setup for Sculpts",
            "content": (
                "Use Principled BSDF for PBR materials. Set base color from reference images. "
                "Use roughness maps for surface variation. Add normal maps for micro-detail. "
                "Use subsurface scattering for skin and organic materials. Use metallic for "
                "armors, weapons, and metal objects."
            ),
            "category": "materials_textures",
        },
        {
            "topic": "Procedural Deformation",
            "content": (
                "Simple Deform: Twist rotates around axis, Bend curves around a point, Taper "
                "scales along axis, Stretch elongates along axis. Displace modifier pushes "
                "vertices using texture. Lattice provides broad deformation control."
            ),
            "category": "workflow",
        },
        {
            "topic": "Organic Form Sculpting",
            "content": (
                "Start with a base sphere and use Grab brush for major proportions. Block out "
                "primary masses first (head, torso, limbs). Add secondary forms with Clay "
                "Strips and Draw. Use Crease brush for wrinkles and folds. Apply Smooth brush "
                "between passes. Build up details progressively from large to small forms."
            ),
            "category": "organic_sculpting",
        },
        {
            "topic": "Hard Surface Sculpting",
            "content": (
                "Use Trim and Flatten brushes for clean surfaces. Enable Face Sets for "
                "isolating sections. Use Mesh Filter for uniform operations. Apply Boolean "
                "operations for mechanical details. Use Crease brush with high strength for "
                "sharp panel lines. Keep edges clean with Pinch brush."
            ),
            "category": "hard_surface",
        },
        {
            "topic": "Character Head Proportions",
            "content": (
                "Eyes sit at the vertical midpoint of the head. The face divides into thirds: "
                "hairline to brow, brow to nose base, nose base to chin. Ears align from brow "
                "to nose base. The head is roughly 5 eyes wide. The mouth sits one-third "
                "between nose and chin. Start with these landmarks before adding detail."
            ),
            "category": "anatomy",
        },
        {
            "topic": "Creature Design Principles",
            "content": (
                "Ground creatures in real anatomy for believability. Combine features from "
                "multiple real animals. Exaggerate key features for visual impact. Maintain "
                "consistent surface quality. Add asymmetry for organic feel. Use overlapping "
                "forms (scales, plates, feathers) for surface interest."
            ),
            "category": "organic_sculpting",
        },
    ]

    def get_builtin_knowledge(self, prompt, max_results=5):
        """Retrieve built-in knowledge ranked by TF-IDF relevance."""
        query_tokens = _tokenize(prompt)
        query_token_set = set(query_tokens)

        if not query_token_set:
            return "\n\n".join(
                f"[{e['topic']}]: {e['content']}"
                for e in self.BUILTIN_KNOWLEDGE[:max_results]
            )

        idf = _compute_idf(self.BUILTIN_KNOWLEDGE)
        prompt_category = auto_categorize(prompt)

        scored = []
        for entry in self.BUILTIN_KNOWLEDGE:
            score = _score_entry(entry, query_tokens, query_token_set, idf)
            if entry.get("category") == prompt_category:
                score *= 1.5
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:max_results]

        if not top:
            fallback = [e for e in self.BUILTIN_KNOWLEDGE
                        if e.get("category") in {"brush_technique", "workflow"}]
            top = [(1.0, e) for e in fallback[:max_results]]

        parts = []
        for _, entry in top:
            cat_label = CATEGORY_KEYWORDS.get(entry.get("category", ""), {}).get("label", entry.get("category", ""))
            parts.append(f"[{entry['topic']}] ({cat_label}): {entry['content']}")
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
