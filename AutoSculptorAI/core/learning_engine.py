"""Learning Engine — active training mode for Auto Sculptor AI.

Handles comprehension of scraped content, extraction of actionable rules,
self-validation of learned knowledge, and adjustment of generation parameters.
"""

import json
import os
import re
import time


RULE_CATEGORIES = {
    "brush_usage": "When and how to use specific brushes",
    "mesh_setup": "Base mesh selection, topology, subdivision strategy",
    "deformation": "Deformation techniques and modifier usage",
    "proportions": "Anatomical proportions and spatial relationships",
    "workflow_order": "Order of operations in a sculpting workflow",
    "surface_detail": "Surface treatment, textures, and micro-detail",
    "materials": "Material setup, shader configuration, PBR settings",
}

BRUSH_TERMS = {
    "draw", "clay", "clay_strips", "inflate", "grab", "smooth",
    "crease", "pinch", "flatten", "scrape", "snake_hook", "trim",
    "mask", "blob", "layer", "nudge", "thumb", "elastic_deform",
}

MODIFIER_TERMS = {
    "mirror", "subsurf", "subdivision", "solidify", "bevel",
    "displace", "smooth", "decimate", "remesh", "boolean",
    "lattice", "shrinkwrap", "array", "simple_deform",
}


class LearningEngine:
    """Actively studies content, extracts rules, validates understanding,
    and adjusts generation behavior."""

    RULES_FILE = "learned_rules.json"
    LEARNING_LOG_FILE = "learning_log.json"

    def __init__(self, db_path=None):
        self.db_dir = db_path or os.path.join(os.path.expanduser("~"), ".autosculptor_ai")
        os.makedirs(self.db_dir, exist_ok=True)
        self.rules_path = os.path.join(self.db_dir, self.RULES_FILE)
        self.log_path = os.path.join(self.db_dir, self.LEARNING_LOG_FILE)

    def _load_rules(self):
        if os.path.isfile(self.rules_path):
            try:
                with open(self.rules_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return {"rules": [], "parameter_adjustments": {}, "metadata": {"total_sessions": 0}}

    def _save_rules(self, data):
        with open(self.rules_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_log(self):
        if os.path.isfile(self.log_path):
            try:
                with open(self.log_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return {"sessions": []}

    def _save_log(self, data):
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def study(self, content, source_title, source_type="youtube"):
        """Study a piece of content: comprehend, extract rules, validate, adjust.

        Returns a learning report dict with what was learned and how behavior changed.
        """
        session = {
            "source_title": source_title,
            "source_type": source_type,
            "timestamp": time.time(),
            "techniques_found": [],
            "rules_extracted": [],
            "validations": [],
            "adjustments": [],
        }

        techniques = self._comprehend(content)
        session["techniques_found"] = techniques

        new_rules = self._extract_rules(techniques, source_title)
        session["rules_extracted"] = [r["rule"] for r in new_rules]

        validations = self._validate_rules(new_rules)
        session["validations"] = validations

        valid_rules = [r for r, v in zip(new_rules, validations) if v["passed"]]

        adjustments = self._adjust_parameters(valid_rules)
        session["adjustments"] = adjustments

        rules_data = self._load_rules()
        for rule in valid_rules:
            existing = next(
                (r for r in rules_data["rules"] if r["rule"] == rule["rule"]),
                None,
            )
            if existing:
                existing["confidence"] = min(1.0, existing["confidence"] + 0.1)
                existing["sources"].append(source_title)
                existing["sources"] = list(set(existing["sources"]))
            else:
                rules_data["rules"].append(rule)

        for key, value in adjustments.items():
            if key in rules_data["parameter_adjustments"]:
                old = rules_data["parameter_adjustments"][key]
                rules_data["parameter_adjustments"][key] = (old + value) / 2
            else:
                rules_data["parameter_adjustments"][key] = value

        rules_data["metadata"]["total_sessions"] = rules_data["metadata"].get("total_sessions", 0) + 1
        self._save_rules(rules_data)

        log_data = self._load_log()
        log_data["sessions"].append(session)
        if len(log_data["sessions"]) > 50:
            log_data["sessions"] = log_data["sessions"][-50:]
        self._save_log(log_data)

        return self._build_report(session)

    def _comprehend(self, content):
        """Extract sculpting techniques from raw content."""
        techniques = []
        sentences = re.split(r'(?<!\d)[.!?](?!\d)|\n', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 15]

        for sent in sentences:
            sent_lower = sent.lower()
            technique = {"text": sent, "type": None, "details": {}}

            found_brushes = [b for b in BRUSH_TERMS if b.replace("_", " ") in sent_lower or b in sent_lower]
            if found_brushes:
                technique["type"] = "brush_usage"
                technique["details"]["brushes"] = found_brushes
                strength = re.search(r'strength[:\s]+(\d*\.?\d+)', sent_lower)
                if strength:
                    technique["details"]["strength"] = float(strength.group(1))
                radius = re.search(r'radius[:\s]+(\d*\.?\d+)', sent_lower)
                if radius:
                    technique["details"]["radius"] = float(radius.group(1))

            found_mods = [m for m in MODIFIER_TERMS if m.replace("_", " ") in sent_lower or m in sent_lower]
            if found_mods:
                if not technique["type"]:
                    technique["type"] = "deformation"
                technique["details"]["modifiers"] = found_mods

            proportion_patterns = [
                r'(\w+)\s+(?:is|are|sits?|at)\s+(?:the\s+)?(?:about\s+)?(\d+(?:/\d+)?)\s*(?:of|from|between)',
                r'divide[sd]?\s+into\s+(\w+)',
                r'(\d+)\s+(?:eyes?|heads?)\s+(?:wide|tall|long)',
            ]
            for pat in proportion_patterns:
                if re.search(pat, sent_lower):
                    technique["type"] = "proportions"
                    break

            workflow_indicators = [
                r'\b(first|then|next|after|before|finally|step\s*\d+)\b',
                r'\b(start\s+with|begin\s+by|end\s+with|finish\s+by)\b',
                r'\b(block\s*out|rough\s+in|refine|polish|detail)\b',
            ]
            for pat in workflow_indicators:
                if re.search(pat, sent_lower) and not technique["type"]:
                    technique["type"] = "workflow_order"
                    break

            if any(w in sent_lower for w in ["texture", "material", "shader", "bsdf", "roughness", "metallic"]):
                if not technique["type"]:
                    technique["type"] = "materials"

            if any(w in sent_lower for w in ["detail", "pore", "wrinkle", "scale", "pattern", "surface"]):
                if not technique["type"]:
                    technique["type"] = "surface_detail"

            if any(w in sent_lower for w in ["mesh", "topology", "quad", "vertex", "base shape"]):
                if not technique["type"]:
                    technique["type"] = "mesh_setup"

            if technique["type"]:
                techniques.append(technique)

        return techniques

    def _extract_rules(self, techniques, source_title):
        """Convert comprehended techniques into actionable rules."""
        rules = []

        for tech in techniques:
            rule_text = self._technique_to_rule(tech)
            if not rule_text:
                continue

            rule = {
                "rule": rule_text,
                "category": tech["type"],
                "confidence": 0.5,
                "sources": [source_title],
                "details": tech.get("details", {}),
            }
            rules.append(rule)

        rules = self._deduplicate_rules(rules)
        return rules

    def _technique_to_rule(self, technique):
        """Convert a single technique into a rule string."""
        text = technique["text"]
        tech_type = technique["type"]
        details = technique.get("details", {})

        text = re.sub(r'\b(um|uh|like|you know|basically|actually)\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) < 15 or len(text) > 300:
            return None

        filler = [
            r'\b(hey guys|welcome|subscribe|click|notification|bell)\b',
            r'\b(patreon|sponsor|link in description)\b',
            r'\b(amazing|awesome|cool|great)\b',
        ]
        for pat in filler:
            if re.search(pat, text, re.IGNORECASE):
                return None

        if tech_type == "brush_usage" and details.get("brushes"):
            brushes = ", ".join(details["brushes"])
            strength_info = ""
            if details.get("strength"):
                strength_info = f" at strength {details['strength']}"
            return f"Use {brushes} brush{strength_info}: {text}"

        if tech_type == "workflow_order":
            return f"Workflow: {text}"

        if tech_type == "proportions":
            return f"Proportion rule: {text}"

        if tech_type == "deformation" and details.get("modifiers"):
            mods = ", ".join(details["modifiers"])
            return f"Use {mods} modifier: {text}"

        return f"{RULE_CATEGORIES.get(tech_type, tech_type)}: {text}"

    def _deduplicate_rules(self, rules):
        """Remove near-duplicate rules."""
        unique = []
        seen_texts = set()
        for rule in rules:
            normalized = re.sub(r'\s+', ' ', rule["rule"].lower().strip())
            words = set(normalized.split())
            is_dup = False
            for seen in seen_texts:
                seen_words = set(seen.split())
                overlap = len(words & seen_words) / max(len(words | seen_words), 1)
                if overlap > 0.7:
                    is_dup = True
                    break
            if not is_dup:
                seen_texts.add(normalized)
                unique.append(rule)
        return unique

    def _validate_rules(self, rules):
        """Validate extracted rules for consistency and sanity."""
        validations = []
        for rule in rules:
            result = {"passed": True, "issues": []}

            if len(rule["rule"]) < 20:
                result["passed"] = False
                result["issues"].append("Rule too short to be actionable")

            details = rule.get("details", {})
            if details.get("strength") is not None:
                s = details["strength"]
                if s < 0 or s > 1.0:
                    if s <= 2.0:
                        pass
                    else:
                        result["passed"] = False
                        result["issues"].append(f"Brush strength {s} out of range")

            if details.get("radius") is not None:
                r = details["radius"]
                if r < 0 or r > 1.0:
                    result["issues"].append(f"Brush radius {r} may be out of range")

            if rule.get("category") == "proportions":
                text_lower = rule["rule"].lower()
                has_numbers = bool(re.search(r'\d', text_lower))
                has_spatial = any(w in text_lower for w in [
                    "midpoint", "half", "third", "quarter", "between", "above", "below"
                ])
                if not has_numbers and not has_spatial:
                    result["issues"].append("Proportion rule lacks specific measurements")

            if details.get("brushes"):
                invalid = [b for b in details["brushes"] if b not in BRUSH_TERMS]
                if invalid:
                    result["passed"] = False
                    result["issues"].append(f"Unknown brush types: {invalid}")

            validations.append(result)
        return validations

    def _adjust_parameters(self, valid_rules):
        """Compute parameter adjustments based on validated rules."""
        adjustments = {}

        brush_counts = {}
        for rule in valid_rules:
            if rule.get("category") == "brush_usage":
                for brush in rule.get("details", {}).get("brushes", []):
                    brush_counts[brush] = brush_counts.get(brush, 0) + 1

        if brush_counts:
            total = sum(brush_counts.values())
            for brush, count in brush_counts.items():
                adjustments[f"brush_weight_{brush}"] = count / total

        workflow_steps = []
        for rule in valid_rules:
            if rule.get("category") == "workflow_order":
                workflow_steps.append(rule["rule"])

        if workflow_steps:
            adjustments["has_workflow_guidance"] = 1.0

        strength_values = []
        for rule in valid_rules:
            s = rule.get("details", {}).get("strength")
            if s is not None:
                strength_values.append(s)
        if strength_values:
            adjustments["avg_brush_strength"] = sum(strength_values) / len(strength_values)

        mod_counts = {}
        for rule in valid_rules:
            if rule.get("category") == "deformation":
                for mod in rule.get("details", {}).get("modifiers", []):
                    mod_counts[mod] = mod_counts.get(mod, 0) + 1
        if mod_counts:
            total = sum(mod_counts.values())
            for mod, count in mod_counts.items():
                adjustments[f"modifier_weight_{mod}"] = count / total

        return adjustments

    def _build_report(self, session):
        """Build a human-readable learning report."""
        techniques = session["techniques_found"]
        rules = session["rules_extracted"]
        validations = session["validations"]
        adjustments = session["adjustments"]

        report = {
            "source": session["source_title"],
            "techniques_found": len(techniques),
            "rules_learned": len([v for v in validations if v["passed"]]),
            "rules_rejected": len([v for v in validations if not v["passed"]]),
            "categories_learned": {},
            "key_rules": [],
            "behavior_changes": [],
        }

        for tech in techniques:
            cat = tech["type"]
            label = RULE_CATEGORIES.get(cat, cat)
            report["categories_learned"][label] = report["categories_learned"].get(label, 0) + 1

        for rule, validation in zip(rules, validations):
            if validation["passed"]:
                report["key_rules"].append(rule)
            if len(report["key_rules"]) >= 5:
                break

        if isinstance(adjustments, dict):
            for key, value in adjustments.items():
                if key.startswith("brush_weight_"):
                    brush = key.replace("brush_weight_", "")
                    report["behavior_changes"].append(
                        f"Will prioritize {brush} brush ({value:.0%} weight)"
                    )
                elif key == "avg_brush_strength":
                    report["behavior_changes"].append(
                        f"Adjusted default brush strength to {value:.2f}"
                    )
                elif key.startswith("modifier_weight_"):
                    mod = key.replace("modifier_weight_", "")
                    report["behavior_changes"].append(
                        f"Will use {mod} modifier more frequently"
                    )
                elif key == "has_workflow_guidance":
                    report["behavior_changes"].append(
                        "Learned new workflow ordering from tutorial"
                    )

        return report

    def get_learned_rules(self, category=None, min_confidence=0.3):
        """Get all learned rules, optionally filtered by category."""
        data = self._load_rules()
        rules = data.get("rules", [])
        if category:
            rules = [r for r in rules if r.get("category") == category]
        rules = [r for r in rules if r.get("confidence", 0) >= min_confidence]
        rules.sort(key=lambda r: r.get("confidence", 0), reverse=True)
        return rules

    def get_rules_for_prompt(self, prompt):
        """Get learned rules relevant to a specific prompt."""
        prompt_lower = prompt.lower()
        prompt_words = set(re.findall(r'\b\w{3,}\b', prompt_lower))

        all_rules = self.get_learned_rules()
        if not all_rules:
            return []

        scored = []
        for rule in all_rules:
            rule_words = set(re.findall(r'\b\w{3,}\b', rule["rule"].lower()))
            overlap = len(prompt_words & rule_words)
            score = overlap * rule.get("confidence", 0.5)

            category = rule.get("category", "")
            if category == "brush_usage":
                score += 0.3
            elif category == "workflow_order":
                score += 0.2
            elif category == "proportions":
                if any(w in prompt_lower for w in ["head", "face", "body", "character", "human"]):
                    score += 0.5
            elif category == "mesh_setup":
                score += 0.1

            if score > 0:
                scored.append((score, rule))

        if not scored:
            scored = [(r.get("confidence", 0.5), r) for r in all_rules[:10]]

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:10]]

    def format_rules_for_prompt(self, prompt):
        """Format learned rules as instructions for the AI prompt."""
        rules = self.get_rules_for_prompt(prompt)
        if not rules:
            return None

        parts = ["Apply these learned sculpting rules:"]
        for rule in rules:
            conf = rule.get("confidence", 0.5)
            marker = "MUST" if conf >= 0.8 else "SHOULD" if conf >= 0.5 else "CONSIDER"
            parts.append(f"- [{marker}] {rule['rule']}")

        return "\n".join(parts)

    def get_parameter_adjustments(self):
        """Get all learned parameter adjustments."""
        data = self._load_rules()
        return data.get("parameter_adjustments", {})

    def get_learning_stats(self):
        """Get statistics about what has been learned."""
        data = self._load_rules()
        rules = data.get("rules", [])

        stats = {
            "total_rules": len(rules),
            "total_sessions": data.get("metadata", {}).get("total_sessions", 0),
            "categories": {},
            "avg_confidence": 0.0,
            "parameter_adjustments": len(data.get("parameter_adjustments", {})),
        }

        if rules:
            stats["avg_confidence"] = sum(r.get("confidence", 0) for r in rules) / len(rules)
            for rule in rules:
                cat = RULE_CATEGORIES.get(rule.get("category", ""), rule.get("category", "unknown"))
                stats["categories"][cat] = stats["categories"].get(cat, 0) + 1

        return stats

    def clear_learned(self):
        """Clear all learned rules and adjustments."""
        self._save_rules({"rules": [], "parameter_adjustments": {}, "metadata": {"total_sessions": 0}})
        self._save_log({"sessions": []})
