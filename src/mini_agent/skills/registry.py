"""Skills registry — local ClawHub-style index for MiniAgent G4."""

import json
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class SkillSpec:
    """Metadata for a registered skill."""
    name: str
    description: str
    path: Path
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    author: str = "unknown"
    version: str = "1.0.0"


class SkillsRegistry:
    """Local skills registry — indexes, searches and serves skills."""

    def __init__(self, skills_dir: Optional[Path] = None):
        self.skills_dir = skills_dir or Path("my_skills")
        self._skills: dict[str, SkillSpec] = {}
        self._indexed = False

    def index(self) -> dict[str, SkillSpec]:
        """Scan skills_dir and build the index."""
        self._skills.clear()
        if not self.skills_dir.exists():
            self._indexed = True
            return self._skills

        for skill_path in self.skills_dir.iterdir():
            if not skill_path.is_dir():
                continue
            spec = self._load_skill(skill_path)
            if spec:
                self._skills[spec.name] = spec

        self._indexed = True
        return self._skills

    def _load_skill(self, path: Path) -> Optional[SkillSpec]:
        """Load SKILL.md frontmatter from a skill directory."""
        skill_md = path / "SKILL.md"
        if not skill_md.exists():
            return None

        try:
            content = skill_md.read_text(encoding="utf-8")
        except Exception:
            return None

        # Parse YAML frontmatter
        name = path.name
        description = ""
        category = "general"
        tags = []
        author = "unknown"
        version = "1.0.0"

        fm_match = re.match(r"^---\n(.*?)---", content, re.DOTALL)
        if fm_match:
            for line in fm_match.group(1).splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    key = key.strip()
                    val = val.strip()
                    if key == "name":
                        name = val
                    elif key == "description":
                        description = val
                    elif key == "category":
                        category = val
                    elif key == "tags":
                        tags = [t.strip() for t in val.split(",")]
                    elif key == "author":
                        author = val
                    elif key == "version":
                        version = val

        if not description:
            # Fallback: first non-heading line after frontmatter
            body = content[fm_match.end():].lstrip() if fm_match else content
            first_lines = [l.strip() for l in body.splitlines() if l.strip() and not l.strip().startswith("#")]
            description = first_lines[0][:200] if first_lines else ""

        return SkillSpec(
            name=name,
            description=description,
            path=path,
            category=category,
            tags=tags,
            author=author,
            version=version,
        )

    def search(self, query: str, limit: int = 10) -> list[SkillSpec]:
        """Full-text search across skill names, descriptions, and tags."""
        if not self._indexed:
            self.index()

        query_lower = query.lower()
        scored: list[tuple[float, SkillSpec]] = []

        for skill in self._skills.values():
            score = 0.0
            if query_lower in skill.name.lower():
                score += 10.0
            if query_lower in skill.description.lower():
                score += 5.0
            if any(query_lower in tag.lower() for tag in skill.tags):
                score += 3.0
            if query_lower in skill.category.lower():
                score += 2.0
            if score > 0:
                scored.append((score, skill))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:limit]]

    def list_by_category(self, category: str) -> list[SkillSpec]:
        """List all skills in a category."""
        if not self._indexed:
            self.index()
        return [s for s in self._skills.values() if s.category == category]

    def get(self, name: str) -> Optional[SkillSpec]:
        """Get a skill by name."""
        if not self._indexed:
            self.index()
        return self._skills.get(name)

    def all(self) -> list[SkillSpec]:
        """List all registered skills."""
        if not self._indexed:
            self.index()
        return list(self._skills.values())

    def categories(self) -> list[str]:
        """List all unique categories."""
        if not self._indexed:
            self.index()
        return sorted(set(s.category for s in self._skills.values()))

    def register_skill(self, spec: SkillSpec) -> None:
        """Register or update a skill manually."""
        self._skills[spec.name] = spec
        self._indexed = True

    def export_index(self) -> dict:
        """Export the full index as a dict."""
        if not self._indexed:
            self.index()
        return {
            "total": len(self._skills),
            "categories": self.categories(),
            "skills": [
                {
                    "name": s.name,
                    "description": s.description,
                    "category": s.category,
                    "tags": s.tags,
                    "author": s.author,
                    "version": s.version,
                    "path": str(s.path),
                }
                for s in self._skills.values()
            ],
        }
