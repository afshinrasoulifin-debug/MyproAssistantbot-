
from __future__ import annotations
"""Victor v7.0 TITAN — File Processor (analyze, create, convert)"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


# ═══════════════════════════════════════════════════════════════════
# FILE PROCESSOR — Create, Read, Analyze files (v7 TITAN)
# ═══════════════════════════════════════════════════════════════════

class FileProcessor:
    """
    Real file creation and analysis engine for Victor.
    Supports: TXT, CSV, JSON, HTML reports, Markdown, code analysis.
    No fantasy — actual file I/O with proper encoding and error handling.
    """

    # Supported MIME types for analysis
    ANALYZABLE_TYPES = {
        ".txt": "text/plain",
        ".csv": "text/csv",
        ".json": "application/json",
        ".md": "text/markdown",
        ".py": "text/x-python",
        ".js": "text/javascript",
        ".html": "text/html",
        ".xml": "text/xml",
        ".yml": "text/yaml",
        ".yaml": "text/yaml",
        ".log": "text/plain",
        ".ini": "text/plain",
        ".cfg": "text/plain",
        ".env": "text/plain",
        ".sql": "text/x-sql",
        ".sh": "text/x-shellscript",
        ".bat": "text/plain",
        ".tsv": "text/tab-separated-values",
    }

    # Magic bytes for binary detection
    MAGIC_BYTES = {
        b"\x89PNG": "image/png",
        b"\xff\xd8\xff": "image/jpeg",
        b"GIF8": "image/gif",
        b"PK": "application/zip",
        b"%PDF": "application/pdf",
    }

    @classmethod
    def detect_file_type(cls, file_path: str) -> Dict[str, Any]:
        """Detect file type, encoding, and basic metadata."""
        p = Path(file_path)
        info = {
            "name": p.name,
            "extension": p.suffix.lower(),
            "size_bytes": 0,
            "mime_type": "unknown",
            "is_text": False,
            "is_binary": False,
            "encoding": "utf-8",
        }

        if not p.exists():
            info["error"] = "فایل پیدا نشد"
            return info

        info["size_bytes"] = p.stat().st_size

        # Check magic bytes
        try:
            with open(file_path, "rb") as f:
                header = f.read(16)
            for magic, mime in cls.MAGIC_BYTES.items():
                if header.startswith(magic):
                    info["mime_type"] = mime
                    info["is_binary"] = True
                    return info
        except Exception as _err:
            logger.warning("Suppressed error: %s", _err)

        # Check by extension
        if info["extension"] in cls.ANALYZABLE_TYPES:
            info["mime_type"] = cls.ANALYZABLE_TYPES[info["extension"]]
            info["is_text"] = True
        elif info["extension"] in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"}:
            info["mime_type"] = "image/" + info["extension"].strip(".")
            info["is_binary"] = True
        elif info["extension"] in {".mp3", ".wav", ".ogg", ".flac", ".m4a"}:
            info["mime_type"] = "audio/" + info["extension"].strip(".")
            info["is_binary"] = True
        elif info["extension"] in {".mp4", ".avi", ".mkv", ".mov", ".webm"}:
            info["mime_type"] = "video/" + info["extension"].strip(".")
            info["is_binary"] = True
        elif info["extension"] in {".zip", ".rar", ".7z", ".tar", ".gz"}:
            info["mime_type"] = "application/archive"
            info["is_binary"] = True
        elif info["extension"] in {".pdf"}:
            info["mime_type"] = "application/pdf"
            info["is_binary"] = True
        elif info["extension"] in {".doc", ".docx"}:
            info["mime_type"] = "application/msword"
            info["is_binary"] = True
        elif info["extension"] in {".xls", ".xlsx"}:
            info["mime_type"] = "application/vnd.ms-excel"
            info["is_binary"] = True
        else:
            # Try reading as text
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    f.read(1024)
                info["is_text"] = True
                info["mime_type"] = "text/plain"
            except (UnicodeDecodeError, Exception):
                info["is_binary"] = True

        return info

    @classmethod
    def analyze_text_file(cls, file_path: str, max_preview: int = 2000) -> Dict[str, Any]:
        """Analyze a text file: stats, preview, language detection."""
        result = {
            "type": "text",
            "lines": 0,
            "words": 0,
            "chars": 0,
            "preview": "",
            "language": "unknown",
            "empty_lines": 0,
            "avg_line_length": 0,
        }

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="cp1256") as f:
                    content = f.read()
                result["encoding"] = "cp1256 (Windows Arabic)"
            except Exception as e:
                return {"error": f"خطای خواندن: {e}"}

        lines = content.splitlines()
        result["lines"] = len(lines)
        result["words"] = len(content.split())
        result["chars"] = len(content)
        result["empty_lines"] = sum(1 for ln in lines if not ln.strip())
        result["avg_line_length"] = round(result["chars"] / max(1, result["lines"]), 1)
        result["preview"] = content[:max_preview]

        # Detect language
        fa_chars = len(re.findall(r'[\u0600-\u06FF]', content))
        en_chars = len(re.findall(r'[a-zA-Z]', content))
        if fa_chars > en_chars:
            result["language"] = "فارسی"
        elif en_chars > fa_chars:
            result["language"] = "English"
        else:
            result["language"] = "مختلط"

        return result

    @classmethod
    def analyze_csv(cls, file_path: str, delimiter: str = ",") -> Dict[str, Any]:
        """Analyze a CSV file: columns, rows, types, basic stats."""
        import csv as csv_mod
        result = {
            "type": "csv",
            "rows": 0,
            "columns": [],
            "column_count": 0,
            "sample_rows": [],
            "stats": {},
        }

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                sample = f.read(4096)
                f.seek(0)
                if "\t" in sample and sample.count("\t") > sample.count(","):
                    delimiter = "\t"
                elif ";" in sample and sample.count(";") > sample.count(","):
                    delimiter = ";"

                reader = csv_mod.reader(f, delimiter=delimiter)
                rows = list(reader)
        except Exception as e:
            return {"error": f"خطای خواندن CSV: {e}"}

        if not rows:
            return {"error": "فایل CSV خالی است"}

        headers = rows[0]
        data_rows = rows[1:]

        result["columns"] = headers
        result["column_count"] = len(headers)
        result["rows"] = len(data_rows)
        result["sample_rows"] = data_rows[:5]

        # Basic stats per column
        for i, col_name in enumerate(headers):
            col_values = [row[i] for row in data_rows if i < len(row) and row[i].strip()]
            col_stat = {
                "name": col_name,
                "non_empty": len(col_values),
                "unique": len(set(col_values)),
            }

            # Try numeric analysis
            numeric_vals = []
            for v in col_values:
                try:
                    numeric_vals.append(float(v.replace(",", "")))
                except ValueError:
                    pass

            if numeric_vals and len(numeric_vals) > len(col_values) * 0.5:
                col_stat["type"] = "عددی"
                col_stat["min"] = min(numeric_vals)
                col_stat["max"] = max(numeric_vals)
                col_stat["avg"] = round(sum(numeric_vals) / len(numeric_vals), 2)
                col_stat["sum"] = round(sum(numeric_vals), 2)
            else:
                col_stat["type"] = "متنی"
                if col_values:
                    col_stat["most_common"] = max(set(col_values), key=col_values.count)
                    col_stat["avg_length"] = round(
                        sum(len(v) for v in col_values) / len(col_values), 1
                    )

            result["stats"][col_name] = col_stat

        return result

    @classmethod
    def analyze_json(cls, file_path: str) -> Dict[str, Any]:
        """Analyze a JSON file: structure, keys, types, depth."""
        result = {
            "type": "json",
            "structure": "",
            "keys": [],
            "depth": 0,
            "item_count": 0,
        }

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return {"error": f"خطای JSON: {e}"}
        except Exception as e:
            return {"error": f"خطای خواندن: {e}"}

        def describe(obj: Any, d: int=0) -> Any:
            if d > 10:
                return "...", d
            if isinstance(obj, dict):
                keys = list(obj.keys())
                mx = d
                for k in keys[:20]:
                    _, dd = describe(obj[k], d + 1)
                    mx = max(mx, dd)
                return f"dict({len(keys)} keys)", mx
            elif isinstance(obj, list):
                if not obj:
                    return "list(empty)", d
                s, dd = describe(obj[0], d + 1)
                return f"list({len(obj)} items → {s})", dd
            elif isinstance(obj, str):
                return "str", d
            elif isinstance(obj, (int, float)):
                return "number", d
            elif isinstance(obj, bool):
                return "bool", d
            elif obj is None:
                return "null", d
            return str(type(obj).__name__), d

        struct, max_depth = describe(data)
        result["structure"] = struct
        result["depth"] = max_depth

        if isinstance(data, dict):
            result["keys"] = list(data.keys())[:30]
            result["item_count"] = len(data)
        elif isinstance(data, list):
            result["item_count"] = len(data)
            if data and isinstance(data[0], dict):
                result["keys"] = list(data[0].keys())

        preview = json.dumps(data, ensure_ascii=False, indent=2)
        result["preview"] = preview[:2000]

        return result

    @classmethod
    def analyze_code(cls, file_path: str) -> Dict[str, Any]:
        """Analyze a source code file."""
        result = {
            "type": "code",
            "language": "",
            "lines": 0,
            "code_lines": 0,
            "comment_lines": 0,
            "blank_lines": 0,
            "functions": [],
            "classes": [],
            "imports": [],
        }

        ext = Path(file_path).suffix.lower()
        lang_map = {
            ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
            ".java": "Java", ".c": "C", ".cpp": "C++", ".cs": "C#",
            ".rb": "Ruby", ".go": "Go", ".rs": "Rust", ".php": "PHP",
            ".sh": "Shell", ".sql": "SQL", ".html": "HTML", ".css": "CSS",
        }
        result["language"] = lang_map.get(ext, ext)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return {"error": f"خطای خواندن: {e}"}

        lines = content.splitlines()
        result["lines"] = len(lines)
        result["blank_lines"] = sum(1 for ln in lines if not ln.strip())

        # Python-specific analysis
        if ext == ".py":
            try:
                tree = ast.parse(content)
                result["classes"] = [n.name for n in ast.walk(tree)
                                     if isinstance(n, ast.ClassDef)]
                result["functions"] = [n.name for n in ast.walk(tree)
                                       if isinstance(n, ast.FunctionDef)][:30]
                result["imports"] = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        result["imports"].extend(a.name for a in node.names)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            result["imports"].append(node.module)
                result["syntax_valid"] = True
            except SyntaxError as e:
                result["syntax_valid"] = False
                result["syntax_error"] = str(e)

            result["comment_lines"] = sum(
                1 for ln in lines if ln.strip().startswith("#")
            )
            result["code_lines"] = result["lines"] - result["blank_lines"] - result["comment_lines"]
        else:
            comment_chars = {"#", "//"}
            result["comment_lines"] = sum(
                1 for ln in lines
                if any(ln.strip().startswith(c) for c in comment_chars)
            )
            result["code_lines"] = result["lines"] - result["blank_lines"] - result["comment_lines"]

        return result

    @classmethod
    def analyze_file(cls, file_path: str) -> str:
        """Main entry: analyze any file and return Persian report."""
        info = cls.detect_file_type(file_path)

        if info.get("error"):
            return f"❌ {info['error']}"

        size_str = cls._format_size(info["size_bytes"])
        report = [
            f"📂 *تحلیل فایل: {info['name']}*\n",
            f"📏 حجم: {size_str}",
            f"📄 نوع: {info['mime_type']}",
        ]

        if info["is_binary"]:
            report.append("\n⚠️ فایل باینری است — تحلیل محتوا ممکن نیست.")

            if "image" in info["mime_type"]:
                report.append("🖼 فایل تصویری.")
                try:
                    import struct
                    with open(file_path, "rb") as f:
                        header = f.read(32)
                    if header.startswith(b"\x89PNG"):
                        w = struct.unpack(">I", header[16:20])[0]
                        h = struct.unpack(">I", header[20:24])[0]
                        report.append(f"📐 ابعاد: {w}×{h} پیکسل")
                except Exception as _err:
                    logger.warning("Suppressed error: %s", _err)
            elif "pdf" in info["mime_type"]:
                report.append("📑 فایل PDF.")
            elif "zip" in info["mime_type"] or "archive" in info["mime_type"]:
                report.append("📦 فایل آرشیو.")
                try:
                    import zipfile
                    if zipfile.is_zipfile(file_path):
                        with zipfile.ZipFile(file_path, "r") as zf:
                            names = zf.namelist()
                            report.append(f"📁 تعداد فایل‌ها: {len(names)}")
                            report.append("📜 محتویات:")
                            for name in names[:20]:
                                zi = zf.getinfo(name)
                                s = cls._format_size(zi.file_size)
                                report.append(f"  • {name} ({s})")
                            if len(names) > 20:
                                report.append(f"  ... و {len(names) - 20} فایل دیگر")
                except Exception as _err:
                    logger.warning("Suppressed error: %s", _err)

            return "\n".join(report)

        # Text file analysis
        ext = info["extension"]

        if ext in (".csv", ".tsv"):
            analysis = cls.analyze_csv(file_path)
            if analysis.get("error"):
                report.append(f"\n❌ {analysis['error']}")
            else:
                report.append(f"\n📊 *تحلیل CSV:*")
                report.append(f"📈 ردیف‌ها: {analysis['rows']}")
                report.append(f"📋 ستون‌ها: {analysis['column_count']}")
                report.append(f"📝 نام ستون‌ها: {', '.join(analysis['columns'][:15])}")

                if analysis["stats"]:
                    report.append("\n📊 *آمار ستون‌ها:*")
                    for col_name, stat in list(analysis["stats"].items())[:10]:
                        if stat["type"] == "عددی":
                            report.append(
                                f"  • *{col_name}* (عددی): "
                                f"min={stat['min']}, max={stat['max']}, "
                                f"avg={stat['avg']}, sum={stat['sum']}"
                            )
                        else:
                            report.append(
                                f"  • *{col_name}* (متنی): "
                                f"{stat['non_empty']} مقدار, "
                                f"{stat['unique']} یکتا"
                            )

                if analysis["sample_rows"]:
                    report.append("\n📋 *نمونه ردیف‌ها:*")
                    for i, row in enumerate(analysis["sample_rows"][:3], 1):
                        row_str = " | ".join(str(c)[:30] for c in row[:8])
                        report.append(f"  {i}. {row_str}")

        elif ext == ".json":
            analysis = cls.analyze_json(file_path)
            if analysis.get("error"):
                report.append(f"\n❌ {analysis['error']}")
            else:
                report.append(f"\n📊 *تحلیل JSON:*")
                report.append(f"🏗 ساختار: `{analysis['structure']}`")
                report.append(f"📏 عمق: {analysis['depth']}")
                report.append(f"📦 تعداد آیتم: {analysis['item_count']}")
                if analysis["keys"]:
                    report.append(f"🔑 کلیدها: {', '.join(analysis['keys'][:15])}")
                if analysis.get("preview"):
                    preview = analysis["preview"][:800]
                    report.append(f"\n```json\n{preview}\n```")

        elif ext in {".py", ".js", ".ts", ".java", ".go", ".rs", ".php", ".sh", ".sql", ".html", ".css"}:
            analysis = cls.analyze_code(file_path)
            if analysis.get("error"):
                report.append(f"\n❌ {analysis['error']}")
            else:
                report.append(f"\n💻 *تحلیل کد ({analysis['language']}):*")
                report.append(
                    f"📏 خطوط: {analysis['lines']} (کد: {analysis['code_lines']}, "
                    f"کامنت: {analysis['comment_lines']}, خالی: {analysis['blank_lines']})"
                )
                if analysis.get("syntax_valid") is not None:
                    st = "✅ صحیح" if analysis["syntax_valid"] else f"❌ خطا: {analysis.get('syntax_error', '')}"
                    report.append(f"🔍 سینتکس: {st}")
                if analysis["classes"]:
                    report.append(
                        f"🏛 کلاس‌ها ({len(analysis['classes'])}): "
                        f"{', '.join(analysis['classes'][:15])}"
                    )
                if analysis["functions"]:
                    report.append(
                        f"⚙️ توابع ({len(analysis['functions'])}): "
                        f"{', '.join(analysis['functions'][:15])}"
                    )
                if analysis["imports"]:
                    report.append(f"📦 واردات: {', '.join(analysis['imports'][:15])}")

        else:
            # Generic text analysis
            analysis = cls.analyze_text_file(file_path)
            if analysis.get("error"):
                report.append(f"\n❌ {analysis['error']}")
            else:
                report.append(f"\n📊 *تحلیل متن:*")
                report.append(f"📏 خطوط: {analysis['lines']}")
                report.append(f"📝 کلمات: {analysis['words']}")
                report.append(f"🔤 کاراکترها: {analysis['chars']}")
                report.append(f"🌐 زبان: {analysis['language']}")
                if analysis["preview"]:
                    preview = analysis["preview"][:500]
                    report.append(f"\n*پیش‌نمایش:*\n```\n{preview}\n```")

        return "\n".join(report)

    @classmethod
    def create_text_file(cls, file_path: str, content: str) -> str:
        """Create a text file."""
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            size = cls._format_size(len(content.encode("utf-8")))
            return f"✅ فایل متنی ایجاد شد!\n📂 مسیر: `{file_path}`\n📏 حجم: {size}"
        except Exception as e:
            return f"❌ خطا در ایجاد فایل: {e}"

    @classmethod
    def create_csv(cls, file_path: str, headers: List[str],
                   rows: List[List[str]], delimiter: str = ",") -> str:
        """Create a CSV file from headers and rows."""
        import csv as csv_mod
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv_mod.writer(f, delimiter=delimiter)
                writer.writerow(headers)
                writer.writerows(rows)
            size = cls._format_size(Path(file_path).stat().st_size)
            return (
                f"✅ فایل CSV ایجاد شد!\n"
                f"📂 مسیر: `{file_path}`\n"
                f"📏 حجم: {size}\n"
                f"📊 {len(rows)} ردیف × {len(headers)} ستون"
            )
        except Exception as e:
            return f"❌ خطا در ایجاد CSV: {e}"

    @classmethod
    def create_json(cls, file_path: str, data: Any) -> str:
        """Create a JSON file."""
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            content = json.dumps(data, ensure_ascii=False, indent=2)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            size = cls._format_size(len(content.encode("utf-8")))
            return f"✅ فایل JSON ایجاد شد!\n📂 مسیر: `{file_path}`\n📏 حجم: {size}"
        except Exception as e:
            return f"❌ خطا در ایجاد JSON: {e}"

    @classmethod
    def create_html_report(cls, file_path: str, title: str,
                           sections: List[Dict[str, str]]) -> str:
        """Create an HTML report with RTL support for Persian."""
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            html_parts = [
                '<!DOCTYPE html>',
                '<html dir="rtl" lang="fa">',
                '<head>',
                '<meta charset="UTF-8">',
                f'<title>{title}</title>',
                '<style>',
                'body { font-family: Tahoma, Arial, sans-serif; margin: 40px; '
                'background: #f5f5f5; color: #333; line-height: 1.8; }',
                '.container { max-width: 900px; margin: 0 auto; background: white; '
                'padding: 40px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }',
                'h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 15px; }',
                'h2 { color: #2980b9; margin-top: 30px; }',
                '.section { margin: 20px 0; padding: 15px; background: #f8f9fa; '
                'border-radius: 8px; border-right: 4px solid #3498db; }',
                'table { width: 100%; border-collapse: collapse; margin: 15px 0; }',
                'th { background: #3498db; color: white; padding: 12px; text-align: right; }',
                'td { padding: 10px; border-bottom: 1px solid #ddd; }',
                'tr:hover { background: #f1f8ff; }',
                '.meta { color: #888; font-size: 0.9em; margin-top: 30px; '
                'padding-top: 15px; border-top: 1px solid #eee; }',
                'pre { background: #2d2d2d; color: #f8f8f2; padding: 15px; '
                'border-radius: 8px; overflow-x: auto; direction: ltr; text-align: left; }',
                '</style>',
                '</head>',
                '<body>',
                '<div class="container">',
                f'<h1>{title}</h1>',
            ]

            for section in sections:
                s_title = section.get("title", "")
                s_content = section.get("content", "")
                s_type = section.get("type", "text")

                if s_title:
                    html_parts.append(f'<h2>{s_title}</h2>')

                html_parts.append('<div class="section">')

                if s_type == "text":
                    paragraphs = s_content.split("\n")
                    for p in paragraphs:
                        if p.strip():
                            html_parts.append(f'<p>{p}</p>')

                elif s_type == "code":
                    html_parts.append(f'<pre><code>{s_content}</code></pre>')

                elif s_type == "table":
                    table_headers = section.get("headers", [])
                    table_rows = section.get("rows", [])
                    html_parts.append('<table>')
                    if table_headers:
                        html_parts.append('<tr>')
                        for h in table_headers:
                            html_parts.append(f'<th>{h}</th>')
                        html_parts.append('</tr>')
                    for row in table_rows:
                        html_parts.append('<tr>')
                        for cell in row:
                            html_parts.append(f'<td>{cell}</td>')
                        html_parts.append('</tr>')
                    html_parts.append('</table>')

                elif s_type == "list":
                    items = section.get("items", [])
                    html_parts.append('<ul>')
                    for item in items:
                        html_parts.append(f'<li>{item}</li>')
                    html_parts.append('</ul>')

                html_parts.append('</div>')

            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            html_parts.extend([
                f'<div class="meta">ایجاد شده توسط Victor v7 TITAN | {ts}</div>',
                '</div>',
                '</body>',
                '</html>',
            ])

            html_content = "\n".join(html_parts)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            size = cls._format_size(len(html_content.encode("utf-8")))
            return (
                f"✅ گزارش HTML ایجاد شد!\n"
                f"📂 مسیر: `{file_path}`\n"
                f"📏 حجم: {size}\n"
                f"📑 {len(sections)} بخش"
            )
        except Exception as e:
            return f"❌ خطا در ایجاد HTML: {e}"

    @classmethod
    def create_markdown_report(cls, file_path: str, title: str,
                               sections: List[Dict[str, str]]) -> str:
        """Create a Markdown report."""
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            lines = [f"# {title}\n"]

            for section in sections:
                s_title = section.get("title", "")
                s_content = section.get("content", "")
                s_type = section.get("type", "text")

                if s_title:
                    lines.append(f"## {s_title}\n")

                if s_type == "text":
                    lines.append(f"{s_content}\n")
                elif s_type == "code":
                    lang = section.get("language", "")
                    lines.append(f"```{lang}")
                    lines.append(s_content)
                    lines.append("```\n")
                elif s_type == "table":
                    headers = section.get("headers", [])
                    tbl_rows = section.get("rows", [])
                    if headers:
                        lines.append("| " + " | ".join(headers) + " |")
                        lines.append("| " + " | ".join("---" for _ in headers) + " |")
                    for row in tbl_rows:
                        lines.append("| " + " | ".join(str(c) for c in row) + " |")
                    lines.append("")
                elif s_type == "list":
                    items = section.get("items", [])
                    for item in items:
                        lines.append(f"- {item}")
                    lines.append("")

            ts = datetime.now().strftime('%Y-%m-%d %H:%M')
            lines.append(f"\n---\n*ایجاد شده توسط Victor v7 TITAN | {ts}*")

            content = "\n".join(lines)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            size = cls._format_size(len(content.encode("utf-8")))
            return f"✅ گزارش Markdown ایجاد شد!\n📂 مسیر: `{file_path}`\n📏 حجم: {size}"
        except Exception as e:
            return f"❌ خطا در ایجاد Markdown: {e}"

    @classmethod
    def convert_csv_to_json(cls, csv_path: str, json_path: str) -> str:
        """Convert CSV file to JSON."""
        import csv as csv_mod
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv_mod.DictReader(f)
                data = list(reader)
            return cls.create_json(json_path, data)
        except Exception as e:
            return f"❌ خطا در تبدیل: {e}"

    @classmethod
    def convert_json_to_csv(cls, json_path: str, csv_path: str) -> str:
        """Convert JSON array to CSV."""
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list) or not data:
                return "❌ JSON باید آرایه‌ای از آبجکت‌ها باشد"
            headers = list(data[0].keys())
            rows = [[str(item.get(h, "")) for h in headers] for item in data]
            return cls.create_csv(csv_path, headers, rows)
        except Exception as e:
            return f"❌ خطا در تبدیل: {e}"

    @classmethod
    def _format_size(cls, size_bytes: int) -> str:
        """Format file size in human-readable Persian."""
        if size_bytes < 1024:
            return f"{size_bytes} بایت"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} کیلوبایت"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} مگابایت"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} گیگابایت"


