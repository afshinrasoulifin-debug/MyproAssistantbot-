
"""
terminal_emulator_pkg/f_s_entry.py — FSEntry
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class FSEntry:
    """Filesystem entry (file or directory)."""
    name: str
    entry_type: FileType
    content: str = ""
    permissions: str = "rwxr-xr-x"
    owner: str = "root"
    size: int = 0
    created: float = field(default_factory=time.time)
    modified: float = field(default_factory=time.time)
    children: Dict[str, "FSEntry"] = field(default_factory=dict)
    target: Optional[str] = None  # For symlinks

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "name": self.name,
            "type": self.entry_type.value,
            "permissions": self.permissions,
            "owner": self.owner,
            "size": self.size,
            "created": self.created,
            "modified": self.modified,
        }
        if self.entry_type == FileType.FILE:
            d["content"] = self.content
        elif self.entry_type == FileType.DIRECTORY:
            d["children"] = {
                k: v.to_dict() for k, v in self.children.items()
            }
        elif self.entry_type == FileType.SYMLINK:
            d["target"] = self.target
        return d




