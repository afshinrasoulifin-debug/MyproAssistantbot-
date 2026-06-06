
"""
plugin_system_pkg/sem_ver.py — SemVer
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class SemVer:
    """Semantic version (major.minor.patch)."""
    major: int
    minor: int
    patch: int
    prerelease: str = ""

    @classmethod
    def parse(cls, version: str) -> "SemVer":
        """Parse version string."""
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$", version.strip())
        if not m:
            raise ValueError(f"Invalid version: {version}")
        return cls(
            major=int(m.group(1)),
            minor=int(m.group(2)),
            patch=int(m.group(3)),
            prerelease=m.group(4) or "",
        )

    def __str__(self) -> str:
        v = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            v += f"-{self.prerelease}"
        return v

    def __lt__(self, other: "SemVer") -> bool:
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        return self.patch < other.patch

    def __le__(self, other: "SemVer") -> bool:
        return self == other or self < other

    def __gt__(self, other: "SemVer") -> bool:
        return not self <= other

    def __ge__(self, other: "SemVer") -> bool:
        return not self < other

    def satisfies(self, constraint: str) -> bool:
        """
        Check if version satisfies a constraint.

        Supports: ^1.2.3 (compatible), ~1.2.3 (approximate),
                  >=1.2.3, <=1.2.3, =1.2.3, >1.2.3, <1.2.3
        """
        constraint = constraint.strip()

        if constraint.startswith("^"):
            # Compatible: same major, >= minor.patch
            target = SemVer.parse(constraint[1:])
            return self.major == target.major and self >= target

        elif constraint.startswith("~"):
            # Approximate: same major.minor, >= patch
            target = SemVer.parse(constraint[1:])
            return (
                self.major == target.major
                and self.minor == target.minor
                and self.patch >= target.patch
            )

        elif constraint.startswith(">="):
            return self >= SemVer.parse(constraint[2:])
        elif constraint.startswith("<="):
            return self <= SemVer.parse(constraint[2:])
        elif constraint.startswith(">"):
            return self > SemVer.parse(constraint[1:])
        elif constraint.startswith("<"):
            return self < SemVer.parse(constraint[1:])
        elif constraint.startswith("="):
            return self == SemVer.parse(constraint[1:])
        else:
            return self == SemVer.parse(constraint)


# ═══════════════════════════════════════════════════════════════════
# Plugin Metadata
# ═══════════════════════════════════════════════════════════════════



# ══════════════════════════════════════════════════════════════
# v10.4 Advanced Plugin System
# ══════════════════════════════════════════════════════════════



