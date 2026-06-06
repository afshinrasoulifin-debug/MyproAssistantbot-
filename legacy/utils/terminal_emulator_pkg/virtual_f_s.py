
"""
terminal_emulator_pkg/virtual_f_s.py — VirtualFS
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class VirtualFS:
    """
    In-memory virtual filesystem with POSIX-like operations.

    Supports: mkdir, touch, write, read, rm, ls, tree, mv, cp, find
    """

    def __init__(self) -> None:
        self.root = FSEntry(
            name="/",
            entry_type=FileType.DIRECTORY,
        )
        # Create standard directories
        for d in ["home", "tmp", "var", "etc", "bin"]:
            self.mkdir(f"/{d}")

    def _resolve_path(self, path: str) -> Tuple[FSEntry, str]:
        """Resolve a path to its parent entry and filename."""
        path = self._normalize_path(path)
        parts = [p for p in path.split("/") if p]

        if not parts:
            return self.root, ""

        current = self.root
        for part in parts[:-1]:
            if part not in current.children:
                raise FileNotFoundError(f"No such directory: {part}")
            child = current.children[part]
            if child.entry_type != FileType.DIRECTORY:
                raise NotADirectoryError(f"Not a directory: {part}")
            current = child

        return current, parts[-1]

    def _normalize_path(self, path: str) -> str:
        """Normalize a filesystem path."""
        if not path.startswith("/"):
            path = "/" + path
        # Resolve .. and .
        parts: List[str] = []
        for part in path.split("/"):
            if part == "..":
                if parts:
                    parts.pop()
            elif part and part != ".":
                parts.append(part)
        return "/" + "/".join(parts)

    def _get_entry(self, path: str) -> FSEntry:
        """Get entry at path."""
        path = self._normalize_path(path)
        if path == "/":
            return self.root

        parent, name = self._resolve_path(path)
        if name not in parent.children:
            raise FileNotFoundError(f"No such file or directory: {path}")
        return parent.children[name]

    def mkdir(self, path: str, parents: bool = True) -> None:
        """Create a directory."""
        path = self._normalize_path(path)
        parts = [p for p in path.split("/") if p]

        current = self.root
        for part in parts:
            if part not in current.children:
                if not parents and part != parts[-1]:
                    raise FileNotFoundError(f"Parent not found: {part}")
                current.children[part] = FSEntry(
                    name=part,
                    entry_type=FileType.DIRECTORY,
                )
            current = current.children[part]

    def touch(self, path: str, content: str = "") -> None:
        """Create or update a file."""
        parent, name = self._resolve_path(path)
        if name in parent.children:
            entry = parent.children[name]
            entry.modified = time.time()
            if content:
                entry.content = content
                entry.size = len(content)
        else:
            parent.children[name] = FSEntry(
                name=name,
                entry_type=FileType.FILE,
                content=content,
                size=len(content),
            )

    def write(self, path: str, content: str, append: bool = False) -> int:
        """Write content to a file."""
        parent, name = self._resolve_path(path)
        if name in parent.children:
            entry = parent.children[name]
            if entry.entry_type != FileType.FILE:
                raise IsADirectoryError(f"Is a directory: {path}")
            if append:
                entry.content += content
            else:
                entry.content = content
            entry.size = len(entry.content)
            entry.modified = time.time()
        else:
            self.touch(path, content)

        return len(content)

    def read(self, path: str) -> str:
        """Read content from a file."""
        entry = self._get_entry(path)
        if entry.entry_type != FileType.FILE:
            raise IsADirectoryError(f"Is a directory: {path}")
        return entry.content

    def rm(self, path: str, recursive: bool = False) -> None:
        """Remove a file or directory."""
        parent, name = self._resolve_path(path)
        if name not in parent.children:
            raise FileNotFoundError(f"No such file: {path}")

        entry = parent.children[name]
        if entry.entry_type == FileType.DIRECTORY and entry.children:
            if not recursive:
                raise OSError(f"Directory not empty: {path}")

        del parent.children[name]

    def ls(self, path: str = "/", details: bool = False) -> List[Dict[str, Any]]:
        """List directory contents."""
        entry = self._get_entry(path)
        if entry.entry_type != FileType.DIRECTORY:
            raise NotADirectoryError(f"Not a directory: {path}")

        items = []
        for name, child in sorted(entry.children.items()):
            if details:
                items.append({
                    "name": name,
                    "type": child.entry_type.value,
                    "size": child.size,
                    "permissions": child.permissions,
                    "modified": child.modified,
                })
            else:
                items.append({"name": name, "type": child.entry_type.value})

        return items

    def tree(self, path: str = "/", prefix: str = "",
             max_depth: int = 10) -> str:
        """Generate tree view of directory."""
        entry = self._get_entry(path)
        lines = [f"{entry.name}/"]
        self._tree_recursive(entry, "", lines, 0, max_depth)
        return "\n".join(lines)

    def _tree_recursive(self, entry: FSEntry, prefix: str,
                        lines: List[str], depth: int,
                        max_depth: int) -> None:
        if depth >= max_depth:
            return
        children = sorted(entry.children.items())
        for i, (name, child) in enumerate(children):
            is_last = i == len(children) - 1
            connector = "└── " if is_last else "├── "
            suffix = "/" if child.entry_type == FileType.DIRECTORY else ""
            lines.append(f"{prefix}{connector}{name}{suffix}")
            if child.entry_type == FileType.DIRECTORY:
                ext = "    " if is_last else "│   "
                self._tree_recursive(
                    child, prefix + ext, lines, depth + 1, max_depth,
                )

    def find(self, path: str = "/", pattern: str = "*",
             file_type: Optional[FileType] = None) -> List[str]:
        """Find files matching pattern."""
        results: List[str] = []
        regex = re.compile(
            pattern.replace("*", ".*").replace("?", "."),
        )
        self._find_recursive(path, self._get_entry(path), regex, file_type, results)
        return results

    def _find_recursive(self, path: str, entry: FSEntry,
                        pattern: re.Pattern, file_type: Optional[FileType],
                        results: List[str]) -> None:
        for name, child in entry.children.items():
            child_path = f"{path.rstrip('/')}/{name}"
            if pattern.match(name):
                if file_type is None or child.entry_type == file_type:
                    results.append(child_path)
            if child.entry_type == FileType.DIRECTORY:
                self._find_recursive(child_path, child, pattern, file_type, results)

    def stat(self, path: str) -> Dict[str, Any]:
        """Get file/directory status."""
        entry = self._get_entry(path)
        return {
            "name": entry.name,
            "type": entry.entry_type.value,
            "size": entry.size,
            "permissions": entry.permissions,
            "owner": entry.owner,
            "created": entry.created,
            "modified": entry.modified,
        }

    def du(self, path: str = "/") -> int:
        """Calculate total size of directory."""
        entry = self._get_entry(path)
        if entry.entry_type == FileType.FILE:
            return entry.size
        total = 0
        for child in entry.children.values():
            if child.entry_type == FileType.FILE:
                total += child.size
            elif child.entry_type == FileType.DIRECTORY:
                total += self.du(f"{path.rstrip('/')}/{child.name}")
        return total

    def to_dict(self) -> Dict[str, Any]:
        """Serialize filesystem."""
        return self.root.to_dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VirtualFS":
        """Deserialize filesystem."""
        fs = cls.__new__(cls)
        fs.root = cls._entry_from_dict(data)
        return fs

    @classmethod
    def _entry_from_dict(cls, data: Dict[str, Any]) -> FSEntry:
        entry = FSEntry(
            name=data["name"],
            entry_type=FileType(data["type"]),
            content=data.get("content", ""),
            permissions=data.get("permissions", "rwxr-xr-x"),
            owner=data.get("owner", "root"),
            size=data.get("size", 0),
            created=data.get("created", 0),
            modified=data.get("modified", 0),
            target=data.get("target"),
        )
        for name, child_data in data.get("children", {}).items():
            entry.children[name] = cls._entry_from_dict(child_data)
        return entry


# ═══════════════════════════════════════════════════════════════════
# Process Manager
# ═══════════════════════════════════════════════════════════════════



