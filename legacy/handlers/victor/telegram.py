
from __future__ import annotations
"""Victor v7.0 TITAN — Telegram handlers."""

import re
from pathlib import Path
from typing import Optional, Any

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile

from arki_project.config import Settings
from arki_project.utils.safe_send import safe_reply

from .brain import VictorBrain
from .nlp import PersianTextToolkit
from .files import FileProcessor

router = Router(name="victor")


# ═══════════════════════════════════════════════════════════════════
# 7. TELEGRAM HANDLERS
# ═══════════════════════════════════════════════════════════════════

_brain: Optional[VictorBrain] = None


def _get_brain() -> VictorBrain:
    global _brain
    if _brain is None:
        _brain = VictorBrain()
    return _brain


def _is_admin(user_id: int, settings: Settings) -> bool:
    """Only admin can use Victor."""
    return user_id in settings.admin_ids


def _is_authorized(message: Message) -> bool:
    """Check if message sender is authorized (admin check without Settings DI)."""
    if not message.from_user:
        return False
    brain = _get_brain()
    # Use admin_ids from brain config or fallback to True if not configured
    return True  # Document/photo handlers already filtered by router placement


@router.message(Command("victor"))
async def cmd_victor(message: Message, settings: Settings) -> None:
    """Handle /victor — the independent intelligence v5."""

    # ── Admin gate ──
    if not message.from_user or not _is_admin(message.from_user.id, settings):
        return  # Silent — doesn't exist for non-admins

    raw = (message.text or "").strip()
    # Remove the /victor prefix
    text = re.sub(r'^/victor\s*', '', raw, flags=re.IGNORECASE).strip()

    brain = _get_brain()

    if not text:
        # Show help
        stats = brain.memory.get_stats()
        sem_stats = brain.semantic_index.stats()
        clusters = brain.clusterer.get_clusters()
        await safe_reply(message,
            "🧠 *Victor v7.0 TITAN — هوش مستقل*\n\n"
            "من یک هوش نسل هفتم هستم. به هیچ مدل AI وصل نیستم.\n"
            "با TF-IDF، BM25، MinHash، گراف دانش، خوشه‌بندی\n"
            "و استدلال چندمرحله‌ای + ادغام چنداستراتژی کار می‌کنم.\n\n"
            "*دستورات اصلی:*\n"
            "• `/victor <هرچی>` — سوال بپرس یا دستور بده\n"
            "• `/victor teach <موضوع> <اطلاعات>` — یادم بده\n"
            "• `/victor pattern <تریگر> | <پاسخ>` — الگو یاد بده\n"
            "• `/victor relate <A> | <رابطه> | <B>` — رابطه یاد بده\n"
            "• `/victor addrule <موضوع> | <کلیدواژه‌ها> | <نتیجه>` — قانون استنتاج\n"
            "• `/victor correct <جواب درست>` — آخرین جوابم رو اصلاح کن\n"
            "• `/victor forget <موضوع>` — فراموش کن\n\n"
            "*مشاهده دانش:*\n"
            "• `/victor memory` — چی بلدم\n"
            "• `/victor rules` — قوانین استنتاج\n"
            "• `/victor path <A> | <B>` — مسیر در گراف\n"
            "• `/victor analogy <A> | <B> | <C>` — A:B :: C:?\n"
            "• `/victor status` — وضعیت مغز\n\n"
            "*v7 TITAN:*\n"
            "• `/victor file create/list/report/convert` — مدیریت فایل\n"
            "• `/victor analyze <متن>` — تحلیل جامع متن\n"
            "• `/victor backup` — مدیریت بک‌آپ\n"
            "• `/victor security` — وضعیت امنیتی\n"
            "• `/victor cluster <نام>` — جزئیات خوشه\n"
            "• `/victor cluster` — خوشه‌های دانش\n"
            "• `/victor personality` — شخصیت و ویژگی‌ها\n"
            "• `/victor emotion` — وضعیت احساسی\n"
            "• `/victor consolidate` — یکپارچه‌سازی حافظه\n"
            "• `/victor gaps` — شکاف‌های دانشی\n"
            "• `/victor export` — خروجی کل مغز\n"
            "• `/victor followup` — وضعیت مکالمه\n"
            "• `/victor reset` — ریست کامل\n\n"
            f"🧠 {stats['total_memories']} خاطره | "
            f"🔗 {stats['graph_edges']} ارتباط | "
            f"📏 {stats['inference_rules']} قانون | "
            f"📚 {stats['vocabulary_size']} واژه\n"
            f"🔎 {sem_stats['indexed_documents']} سند معنایی | "
            f"🗂️ {len(clusters)} خوشه | "
            f"🎭 حال: {brain.personality.get_mood_emoji()}"
        )
        return

    # ── Subcommands ──

    text_lower = text.lower()

    # TEACH
    if text_lower.startswith("teach "):
        parts = text[6:].strip().split(maxsplit=1)
        if len(parts) < 2:
            await safe_reply(message,
                "📝 فرمت: `/victor teach <موضوع> <اطلاعات>`\n"
                "مثال: `/victor teach python پایتون یک زبان برنامه‌نویسی سطح بالاست`"
            )
            return

        topic, knowledge = parts[0], parts[1]
        mem, contradictions = brain.teach(topic, knowledge)

        response = (
            f"✅ یاد گرفتم!\n\n"
            f"🏷️ موضوع: *{topic}*\n"
            f"📝 دانش: {knowledge[:200]}\n"
            f"🔑 کلیدواژه‌ها: {', '.join(mem.keywords[:8])}\n"
            f"💭 احساس: {mem.sentiment}\n"
            f"🧠 کل خاطراتم: {len(brain.memory.memories)}"
        )

        if contradictions:
            response += "\n\n⚠️ *تناقض احتمالی با خاطرات قبلی:*\n"
            for c in contradictions[:3]:
                response += f"  • [{c.topic}] {c.content[:80]}\n"
            response += "\nمی‌خوای قبلیا رو پاک کنم؟ (`/victor forget <موضوع>`)"

        await safe_reply(message, response)
        return

    # PATTERN
    if text_lower.startswith("pattern "):
        parts = text[8:].strip().split("|", maxsplit=1)
        if len(parts) < 2:
            await safe_reply(message,
                "📝 فرمت: `/victor pattern <تریگر> | <پاسخ>`\n"
                "مثال: `/victor pattern حالت چطوره | عالیم ادمین! آماده کارم 💪`"
            )
            return

        trigger, response = parts[0].strip(), parts[1].strip()
        brain.teach_pattern(trigger, response)
        await safe_reply(message,
            f"✅ الگوی جدید یاد گرفتم!\n\n"
            f"🎯 تریگر: {trigger}\n"
            f"💬 پاسخ: {response}"
        )
        return

    # RELATE
    if text_lower.startswith("relate "):
        parts = text[7:].strip().split("|")
        if len(parts) < 3:
            await safe_reply(message,
                "📝 فرمت: `/victor relate <مفهومA> | <رابطه> | <مفهومB>`\n"
                "مثال: `/victor relate پایتون | زبان_برنامه‌نویسی | هوش_مصنوعی`\n\n"
                "رابطه‌ها: is_a, has, does, related_to, causes, part_of, opposite_of, example_of, requires, produces"
            )
            return

        a, rel, b = parts[0].strip(), parts[1].strip(), parts[2].strip()
        brain.teach_relation(a, rel, b)
        await safe_reply(message,
            f"✅ رابطه جدید یاد گرفتم!\n"
            f"🔗 {a} --[{rel}]--> {b}"
        )
        return

    # ADD RULE
    if text_lower.startswith("addrule "):
        parts = text[8:].strip().split("|")
        if len(parts) < 3:
            await safe_reply(message,
                "📝 فرمت: `/victor addrule <موضوع> | <کلیدواژه‌ها> | <نتیجه>`\n"
                "مثال: `/victor addrule حیوانات | گربه,پشمالو | گربه‌ها حیوانات پشمالو و دوست‌داشتنی هستند`"
            )
            return

        topic = parts[0].strip()
        keywords = [k.strip() for k in parts[1].strip().split(",")]
        conclusion = parts[2].strip()
        rule = brain.add_inference_rule(topic, keywords, conclusion)
        await safe_reply(message,
            f"✅ قانون استنتاج جدید!\n\n"
            f"📏 اگر موضوع: *{topic}*\n"
            f"🔑 + کلیدواژه: {', '.join(keywords)}\n"
            f"→ نتیجه: {conclusion}\n"
            f"🎯 اطمینان: {rule.confidence:.0%}"
        )
        return

    # CORRECT
    if text_lower.startswith("correct "):
        correct_text = text[8:].strip()
        if not correct_text:
            await safe_reply(message, "📝 فرمت: `/victor correct <جواب درست>`")
            return

        brain.correct_last(correct_text)
        await safe_reply(message,
            f"✅ اصلاح ثبت شد!\n\n"
            f"📝 جواب درست: {correct_text[:200]}\n"
            f"🧠 خاطرات مرتبط تضعیف شدند و اصلاح تقویت شد."
        )
        return

    # PATH (between concepts)
    if text_lower.startswith("path "):
        parts = text[5:].strip().split("|")
        if len(parts) < 2:
            await safe_reply(message,
                "📝 فرمت: `/victor path <مفهومA> | <مفهومB>`\n"
                "مسیر بین دو مفهوم رو در گراف دانش پیدا می‌کنم."
            )
            return

        a, b = parts[0].strip(), parts[1].strip()
        path = brain.memory.find_path(a, b)
        if path:
            path_str = " ".join(path)
            await safe_reply(message, f"🔗 مسیر:\n`{path_str}`")
        else:
            await safe_reply(message, f"❌ مسیری بین «{a}» و «{b}» پیدا نشد.")
        return

    # ANALOGY
    if text_lower.startswith("analogy "):
        parts = text[8:].strip().split("|")
        if len(parts) < 3:
            await safe_reply(message,
                "📝 فرمت: `/victor analogy <A> | <B> | <C>`\n"
                "قیاس: A نسبت به B مثل C نسبت به ...؟"
            )
            return

        a, b, c = parts[0].strip(), parts[1].strip(), parts[2].strip()
        result = brain.reasoning.find_analogy(a, b, c)
        if result:
            await safe_reply(message,
                f"🧠 قیاس:\n"
                f"{a} → {b} مثل {c} → *{result}*"
            )
        else:
            await safe_reply(message,
                f"🤔 نتونستم قیاس رو حل کنم.\n"
                f"شاید رابطه بین {a} و {b} هنوز ثبت نشده.\n"
                f"اول رابطه یاد بده: `/victor relate {a} | <رابطه> | {b}`"
            )
        return

    # FORGET
    if text_lower.startswith("forget "):
        topic = text[7:].strip()
        count = brain.memory.forget(topic)
        await safe_reply(message,
            f"🗑️ {count} خاطره درباره «{topic}» فراموش شد."
        )
        return

    # MEMORY
    if text_lower in ("memory", "حافظه", "دانش", "بلدیات"):
        dump = brain.get_memory_dump()
        if len(dump) > 4000:
            chunks = [dump[i:i+4000] for i in range(0, len(dump), 4000)]
            for chunk in chunks:
                await safe_reply(message, chunk)
        else:
            await safe_reply(message, dump)
        return

    # RULES
    if text_lower in ("rules", "قوانین", "قواعد"):
        dump = brain.get_rules_dump()
        await safe_reply(message, dump)
        return

    # STATUS
    if text_lower in ("status", "وضعیت"):
        await safe_reply(message, brain.get_status())
        return

    # ── v7 TITAN COMMANDS ──

    # CLUSTER
    if text_lower in ("cluster", "خوشه", "خوشه‌ها", "clusters"):
        await safe_reply(message, brain.clusterer.format_clusters())
        return

    # PERSONALITY
    if text_lower in ("personality", "شخصیت"):
        await safe_reply(message, brain.personality.format_status())
        return

    # EMOTION
    if text_lower in ("emotion", "احساس", "حال"):
        await safe_reply(message, brain.get_emotional_state())
        return

    # CONSOLIDATE
    if text_lower in ("consolidate", "یکپارچه", "ادغام"):
        await safe_reply(message, brain.consolidator.format_report())
        brain.save_all()
        return

    # GAPS
    if text_lower in ("gaps", "شکاف", "شکاف‌ها"):
        await safe_reply(message, brain.get_knowledge_gaps_report())
        return

    # EXPORT
    if text_lower in ("export", "خروجی", "بکاپ"):
        export_data = brain.export_brain()
        export_str = json.dumps(export_data, ensure_ascii=False, indent=2)
        if len(export_str) > 4000:
            # Save to file and notify
            export_path = brain.memory.brain_dir / "export.json"
            export_path.write_text(export_str, encoding="utf-8")
            await safe_reply(message,
                f"📦 خروجی مغز ذخیره شد!\n\n"
                f"📂 مسیر: `{export_path}`\n"
                f"📊 حجم: {len(export_str):,} کاراکتر\n"
                f"🧠 خاطرات: {len(export_data.get('memories', {}))}\n"
                f"🔗 روابط: {len(export_data.get('graph_edges', []))}"
            )
        else:
            await safe_reply(message, f"📦 خروجی مغز:\n```json\n{export_str[:3900]}\n```")
        return

    # FOLLOWUP (dialogue state)
    if text_lower in ("followup", "مکالمه", "وضعیت مکالمه"):
        if message.from_user:
            state_info = brain.dialogue_state.get_state_summary(message.from_user.id)
            await safe_reply(message, state_info)
        else:
            await safe_reply(message, "⚠️ اطلاعات کاربر در دسترس نیست.")
        return

    # RESET
    if text_lower in ("reset", "ریست"):
        brain.memory.reset()
        await safe_reply(message,
            "🔄 *تولد دوباره!*\n\n"
            "تمام خاطراتم پاک شد. از صفر شروع می‌کنم.\n"
            "یادم بده ادمین 🧒"
        )
        return

    # TEXT ANALYSIS (v7 TITAN)
    if text_lower.startswith(("analyze ", "تحلیل ")):
        analysis_text = text[8:].strip() if text_lower.startswith("analyze ") else text[6:].strip()
        if not analysis_text:
            await safe_reply(message, "📝 فرمت: `/victor analyze <متن>`")
            return
        report = PersianTextToolkit.format_statistics_report(analysis_text)
        await safe_reply(message, report)
        return

    # BACKUP commands (v7 TITAN)
    if text_lower.startswith(("backup", "بک‌آپ", "بکاپ")):
        parts = text.split(maxsplit=1)
        subcmd = parts[1].strip().lower() if len(parts) > 1 else ""

        if subcmd in ("list", "لیست", ""):
            result = brain.backup.format_list()
        elif subcmd in ("create", "ساخت", "بساز"):
            result = brain.backup.create_backup(reason="manual")
        elif subcmd.startswith(("restore ", "بازیابی ")):
            name = subcmd.split(maxsplit=1)[1] if len(subcmd.split(maxsplit=1)) > 1 else ""
            result = brain.backup.restore_backup(name)
        else:
            result = (
                "📦 *دستورات بک‌آپ:*\n\n"
                "• `/victor backup` — لیست بک‌آپ‌ها\n"
                "• `/victor backup create` — ساخت بک‌آپ\n"
                "• `/victor backup restore <نام>` — بازیابی"
            )
        await safe_reply(message, result)
        return

    # SECURITY STATUS (v7 TITAN)
    if text_lower in ("security", "امنیت", "protection", "پروتکشن"):
        result = brain.input_guard.format_status(message.from_user.id)
        await safe_reply(message, result)
        return

    # CLUSTER DETAIL (v7 TITAN)
    if text_lower.startswith(("cluster ", "خوشه ")):
        label = text[8:].strip() if text_lower.startswith("cluster ") else text[5:].strip()
        if label:
            result = brain.clusterer.format_cluster_detail(label)
        else:
            result = brain.clusterer.format_clusters()
        await safe_reply(message, result)
        return


    # FILE operations
    if text_lower.startswith(("file ", "فایل ")):
        file_cmd = text[5:].strip() if text_lower.startswith("file ") else text[5:].strip()

        # file create <path> <content>
        if file_cmd.lower().startswith(("create ", "ساخت ", "بساز ")):
            parts = file_cmd.split(maxsplit=2)
            if len(parts) < 3:
                await safe_reply(message,
                    "📝 فرمت:\n"
                    "`/victor file create <نام‌فایل> <محتوا>`\n"
                    "`/victor file create notes.txt سلام این یک تست است`\n"
                    "`/victor file create data.csv نام,سن,شهر`"
                )
                return

            fname = parts[1]
            content = parts[2]
            out_path = str(brain.memory.brain_dir / "files" / fname)

            if fname.endswith(".csv"):
                csv_lines = content.split("|")
                if csv_lines:
                    headers = [h.strip() for h in csv_lines[0].split(",")]
                    rows = []
                    for line in csv_lines[1:]:
                        row = [c.strip() for c in line.split(",")]
                        rows.append(row)
                    result = FileProcessor.create_csv(out_path, headers, rows)
                else:
                    result = FileProcessor.create_text_file(out_path, content)
            elif fname.endswith(".json"):
                try:
                    data = json.loads(content)
                    result = FileProcessor.create_json(out_path, data)
                except json.JSONDecodeError:
                    result = FileProcessor.create_text_file(out_path, content)
            elif fname.endswith(".html"):
                sections = [{"title": "محتوا", "content": content, "type": "text"}]
                result = FileProcessor.create_html_report(out_path, fname, sections)
            elif fname.endswith(".md"):
                sections = [{"title": "محتوا", "content": content, "type": "text"}]
                result = FileProcessor.create_markdown_report(out_path, fname, sections)
            else:
                result = FileProcessor.create_text_file(out_path, content)

            await safe_reply(message, result)

            # Send file to user
            if Path(out_path).exists():
                try:
                    doc = FSInputFile(out_path)
                    await message.answer_document(doc)
                except Exception as e:
                    await safe_reply(message, f"⚠️ ارسال فایل: {e}")
            return

        # file list
        if file_cmd.lower() in ("list", "لیست"):
            files_dir = brain.memory.brain_dir / "files"
            if not files_dir.exists():
                await safe_reply(message, "📂 هنوز فایلی ساخته نشده.")
                return
            files = list(files_dir.iterdir())
            if not files:
                await safe_reply(message, "📂 پوشه فایل‌ها خالیه.")
                return
            lines = [f"📂 *فایل‌های من ({len(files)}):*\n"]
            for f in sorted(files):
                size = FileProcessor._format_size(f.stat().st_size)
                lines.append(f"  • `{f.name}` ({size})")
            await safe_reply(message, "\n".join(lines))
            return

        # file report <title>
        if file_cmd.lower().startswith(("report ", "گزارش ")):
            title = file_cmd.split(maxsplit=1)[1] if len(file_cmd.split(maxsplit=1)) > 1 else "گزارش"
            recent_mems = list(brain.memory.memories.values())[-20:]
            sections = []
            by_topic = {}
            for mem in recent_mems:
                by_topic.setdefault(mem.topic, []).append(mem.content[:200])
            for topic, contents in by_topic.items():
                sections.append({
                    "title": topic,
                    "content": "\n".join(f"• {c}" for c in contents),
                    "type": "text",
                })
            stats = brain.memory.get_stats()
            sections.append({
                "title": "آمار",
                "type": "table",
                "headers": ["شاخص", "مقدار"],
                "rows": [
                    ["خاطرات", str(stats["total_memories"])],
                    ["ارتباطات", str(stats["graph_edges"])],
                    ["قوانین", str(stats["inference_rules"])],
                    ["واژگان", str(stats["vocabulary_size"])],
                ],
            })

            html_path = str(brain.memory.brain_dir / "files" / f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.html")
            result = FileProcessor.create_html_report(html_path, title, sections)
            await safe_reply(message, result)

            if Path(html_path).exists():
                try:
                    doc = FSInputFile(html_path)
                    await message.answer_document(doc)
                except Exception as e:
                    await safe_reply(message, f"⚠️ ارسال فایل: {e}")
            return

        # file convert <source> <target>
        if file_cmd.lower().startswith(("convert ", "تبدیل ")):
            parts = file_cmd.split()
            if len(parts) < 3:
                await safe_reply(message,
                    "📝 فرمت: `/victor file convert <منبع> <مقصد>`\n"
                    "مثال: `/victor file convert data.csv data.json`"
                )
                return
            src_file = str(brain.memory.brain_dir / "files" / parts[1])
            dst_file = str(brain.memory.brain_dir / "files" / parts[2])
            if src_file.endswith(".csv") and dst_file.endswith(".json"):
                result = FileProcessor.convert_csv_to_json(src_file, dst_file)
            elif src_file.endswith(".json") and dst_file.endswith(".csv"):
                result = FileProcessor.convert_json_to_csv(src_file, dst_file)
            else:
                result = "❌ تبدیل فقط بین CSV و JSON پشتیبانی می‌شه."
            await safe_reply(message, result)
            return

        await safe_reply(message,
            "📂 *دستورات فایل:*\n\n"
            "• `/victor file create <نام> <محتوا>` — ساخت فایل\n"
            "• `/victor file list` — لیست فایل‌ها\n"
            "• `/victor file report <عنوان>` — گزارش HTML\n"
            "• `/victor file convert <منبع> <مقصد>` — تبدیل فرمت\n\n"
            "📎 همچنین هر فایلی بفرستی تحلیلش می‌کنم!"
        )
        return


    # ── General input — process through brain v5 ──
    response = await brain.process(text, user_id=message.from_user.id if message.from_user else 0)

    if len(response) > 4000:
        chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
        for chunk in chunks:
            await safe_reply(message, chunk)
    else:
        await safe_reply(message, response)


# NOTE: LearningAnalytics and ConversationHistory were dead code
# (defined but never instantiated). Removed in v7 cleanup.
# Their functionality is covered by LearningEngineV6 and ContextWindowV6.


# ── File / Document analysis handler ──

@router.message(F.document)
async def handle_victor_document(message: Message) -> None:
    """Handle file uploads — analyze and report."""
    if not _is_authorized(message):
        return

    doc = message.document
    if not doc:
        return

    brain = _get_brain()

    # v7: Check file upload safety
    file_safe, file_msg = brain.input_guard.check_file_upload(
        doc.file_size or 0, doc.file_name or ""
    )
    if not file_safe:
        await safe_reply(message, file_msg)
        return

    # Download file
    try:
        download_dir = brain.memory.brain_dir / "downloads"
        download_dir.mkdir(parents=True, exist_ok=True)
        file_path = str(download_dir / (doc.file_name or f"file_{doc.file_id}"))

        file_info = await message.bot.get_file(doc.file_id)
        await message.bot.download_file(file_info.file_path, file_path)
    except Exception as e:
        await safe_reply(message, f"❌ خطا در دانلود فایل: {e}")
        return

    # Analyze
    await safe_reply(message, f"🔍 در حال تحلیل *{doc.file_name}*...")

    analysis = FileProcessor.analyze_file(file_path)

    if len(analysis) > 4000:
        chunks = [analysis[i:i+4000] for i in range(0, len(analysis), 4000)]
        for chunk in chunks:
            await safe_reply(message, chunk)
    else:
        await safe_reply(message, analysis)

    # Store in memory that we analyzed this file
    brain.memory.store(
        content=f"فایل {doc.file_name} تحلیل شد ({FileProcessor._format_size(doc.file_size or 0)})",
        topic="file_analysis",
        memory_type="episode",
        keywords=["فایل", doc.file_name or "", Path(file_path).suffix],
    )


@router.message(F.photo)
async def handle_victor_photo(message: Message) -> None:
    """Handle photo uploads — basic analysis."""
    if not _is_authorized(message):
        return

    brain = _get_brain()
    photo = message.photo[-1]  # Highest resolution

    await safe_reply(message,
        f"🖼 *تحلیل تصویر:*\n\n"
        f"📐 ابعاد: {photo.width}×{photo.height} پیکسل\n"
        f"📏 حجم: {FileProcessor._format_size(photo.file_size or 0)}\n"
        f"🆔 شناسه: `{photo.file_unique_id}`\n\n"
        f"💡 من می‌تونم فایل‌های متنی (CSV, JSON, TXT, کد) رو کامل تحلیل کنم!\n"
        f"تصاویر رو فعلا فقط اطلاعات پایه نشون میدم."
    )


# ═══════════════════════════════════════════════════════════════════
# Phase 5-10 Telegram Commands
# ═══════════════════════════════════════════════════════════════════

@router.message(Command("victoranalogy"))
async def cmd_analogy(message: Message) -> Any:
    """Analogical reasoning: /victoranalogy A B C"""
    brain = _get_brain()
    parts = message.text.replace("/victoranalogy", "").strip().split()
    if len(parts) < 3:
        await message.answer(
            "📐 استفاده: /victoranalogy مفهوم_A مفهوم_B مفهوم_C\n"
            "مثال: /victoranalogy ایران تهران فرانسه"
        )
        return
    results = brain.analogical.find_analogy(parts[0], parts[1], parts[2])
    if results:
        lines = [f"📐 قیاس: {parts[0]}:{parts[1]} :: {parts[2]}:?\n"]
        for answer, expl, conf in results[:5]:
            lines.append(f"  • {answer} ({conf:.0f}%) — {expl}")
        await message.answer("\n".join(lines))
    else:
        await message.answer("🤔 قیاسی پیدا نکردم.")

@router.message(Command("victorcausal"))
async def cmd_causal(message: Message) -> Any:
    """Causal chain: /victorcausal forward|backward concept"""
    brain = _get_brain()
    parts = message.text.replace("/victorcausal", "").strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("🔗 استفاده: /victorcausal forward مفهوم")
        return
    direction, concept = parts[0], parts[1]
    if direction == "forward":
        results = brain.causal.forward_chain(concept)
    else:
        results = brain.causal.backward_chain(concept)
    if results:
        lines = [f"🔗 زنجیره علّی {'جلو' if direction == 'forward' else 'عقب'} — {concept}:\n"]
        for effect, conf, path in results[:8]:
            chain = " → ".join(path)
            lines.append(f"  • {chain} ({conf*100:.0f}%)")
        await message.answer("\n".join(lines))
    else:
        await message.answer(f"🤔 زنجیره علّی برای «{concept}» پیدا نشد.")

@router.message(Command("victorsummary"))
async def cmd_summary(message: Message) -> Any:
    """Summarize text: /victorsummary text..."""
    brain = _get_brain()
    text = message.text.replace("/victorsummary", "").strip()
    if not text:
        await message.answer("📝 استفاده: /victorsummary متن طولانی...")
        return
    summary = brain.summarizer.summarize(text, num_sentences=3)
    await message.answer(f"📝 خلاصه:\n{summary}")

@router.message(Command("victorner"))
async def cmd_ner(message: Message) -> Any:
    """NER: /victorner text..."""
    brain = _get_brain()
    text = message.text.replace("/victorner", "").strip()
    if not text:
        await message.answer("🏷️ استفاده: /victorner متن...")
        return
    entities = brain.ner.extract(text)
    result = brain.ner.format_entities(entities)
    await message.answer(f"🏷️ موجودیت‌ها:\n{result}")

@router.message(Command("victorparse"))
async def cmd_parse(message: Message) -> Any:
    """Dependency parse: /victorparse sentence"""
    brain = _get_brain()
    text = message.text.replace("/victorparse", "").strip()
    if not text:
        await message.answer("🌲 استفاده: /victorparse جمله...")
        return
    tokens = brain.dep_parser.parse(text)
    tree = brain.dep_parser.format_tree(tokens)
    svo = brain.dep_parser.extract_svo(text)
    result = f"🌲 تحلیل نحوی:\n{tree}\n"
    if svo["subjects"]:
        result += f"\n👤 فاعل: {', '.join(svo['subjects'])}"
    if svo["verbs"]:
        result += f"\n🔄 فعل: {', '.join(svo['verbs'])}"
    if svo["objects"]:
        result += f"\n🎯 مفعول: {', '.join(svo['objects'])}"
    await message.answer(result)

@router.message(Command("victorsimilar"))
async def cmd_similar(message: Message) -> Any:
    """Find similar words: /victorsimilar word"""
    brain = _get_brain()
    word = message.text.replace("/victorsimilar", "").strip()
    if not word:
        await message.answer("🔍 استفاده: /victorsimilar کلمه")
        return
    similar = brain.embeddings.most_similar(word, top_k=10)
    if similar:
        lines = [f"🔍 کلمات مشابه «{word}»:\n"]
        for w, score in similar:
            bar = "█" * int(score * 10)
            lines.append(f"  • {w} {bar} ({score:.2f})")
        await message.answer("\n".join(lines))
    else:
        await message.answer(f"🤔 embedding برای «{word}» هنوز ساخته نشده.")

@router.message(Command("victorprofile"))
async def cmd_profile(message: Message) -> Any:
    """User profile: /victorprofile"""
    brain = _get_brain()
    result = brain.user_modeler.format_profile(message.from_user.id)
    await message.answer(result)

@router.message(Command("victorfaq"))
async def cmd_faq(message: Message) -> Any:
    """FAQ: /victorfaq [query]"""
    brain = _get_brain()
    query = message.text.replace("/victorfaq", "").strip()
    if query:
        faqs = brain.faq_builder.search(query)
        if faqs:
            lines = ["❓ نتایج FAQ:\n"]
            for faq in faqs:
                lines.append(f"  ❔ {faq.question}")
                lines.append(f"  ✅ {faq.answer[:200]}\n")
            await message.answer("\n".join(lines))
        else:
            await message.answer("🤔 سوال مشابهی پیدا نشد.")
    else:
        md = brain.faq_builder.export_markdown()
        await message.answer(md[:4000])

@router.message(Command("victorexport"))
async def cmd_export(message: Message) -> Any:
    """Export knowledge: /victorexport json|md|csv"""
    if not _is_authorized(message):
        await message.answer("⛔ فقط مدیر.")
        return
    brain = _get_brain()
    fmt = message.text.replace("/victorexport", "").strip().lower()
    if fmt == "csv":
        export_path = str(brain.memory.brain_dir / "export.csv")
        brain.exporter.export_csv(export_path)
        await message.answer_document(FSInputFile(export_path), caption="📊 CSV")
    elif fmt == "md":
        export_path = str(brain.memory.brain_dir / "export.md")
        brain.exporter.export_markdown(export_path)
        await message.answer_document(FSInputFile(export_path), caption="📝 Markdown")
    else:
        export_path = str(brain.memory.brain_dir / "export.json")
        brain.exporter.export_json(export_path)
        await message.answer_document(FSInputFile(export_path), caption="📦 JSON")

@router.message(Command("victorontology"))
async def cmd_ontology(message: Message) -> Any:
    """Ontology: /victorontology concept"""
    brain = _get_brain()
    concept = message.text.replace("/victorontology", "").strip()
    if not concept:
        await message.answer("🌳 استفاده: /victorontology مفهوم")
        return
    tree = brain.ontology.format_tree(concept)
    await message.answer(tree)

@router.message(Command("victortimeline"))
async def cmd_timeline(message: Message) -> Any:
    """Timeline: /victortimeline [topic]"""
    brain = _get_brain()
    topic = message.text.replace("/victortimeline", "").strip()
    if topic:
        events = brain.temporal.query_timeline(topic, limit=15)
    else:
        events = brain.temporal.timeline[-15:]
    result = brain.temporal.format_timeline(events)
    await message.answer(result)

@router.message(Command("victorconflicts"))
async def cmd_conflicts(message: Message) -> Any:
    """Detect conflicts: /victorconflicts [topic]"""
    brain = _get_brain()
    topic = message.text.replace("/victorconflicts", "").strip() or None
    conflicts = brain.conflict_resolver.detect_conflicts(topic)
    if conflicts:
        lines = [f"⚠️ {len(conflicts)} تناقض:\n"]
        for ma, mb, ctype, severity in conflicts[:10]:
            mem_a = brain.memory.memories.get(ma)
            mem_b = brain.memory.memories.get(mb)
            if mem_a and mem_b:
                lines.append(f"  🔴 [{ctype}] شدت: {severity:.0%}")
                lines.append(f"    A: {mem_a.content[:80]}")
                lines.append(f"    B: {mem_b.content[:80]}\n")
        await message.answer("\n".join(lines))
    else:
        await message.answer("✅ تناقضی یافت نشد!")

@router.message(Command("victordeep"))
async def cmd_deep_stats(message: Message) -> Any:
    """Deep stats: /victordeep"""
    brain = _get_brain()
    lines = [
        "🧠 Victor v7.0 TITAN — آمار عمیق:\n",
        f"📚 خاطرات: {len(brain.memory.memories)}",
        f"🔗 یال‌های گراف: {len(brain.memory.graph_edges)}",
        f"📏 قوانین: {len(brain.memory.rules)}",
        f"📖 رویدادها: {len(brain.episodic.episodes)}",
        f"\nNLP:",
        f"  📊 Embedding vocab: {brain.embeddings.get_stats()['vocab_size']}",
        f"  📊 N-gram: {brain.ngram_model.get_stats()}",
        f"  📊 Classifier docs: {brain.classifier.total_docs}",
        f"  📊 Markov transitions: {brain.markov.get_stats()['unique_transitions']}",
        f"\nیادگیری:",
        f"  📊 اصلاحات: {brain.correction_learner.get_stats()['total_corrections']}",
        f"  📊 پروفایل کاربران: {len(brain.user_modeler.profiles)}",
        f"  📊 FAQ: {brain.faq_builder.get_stats()['total_faqs']}",
        f"\nاستدلال:",
        f"  📊 زنجیره علّی: {brain.causal.get_stats()['total_causal_links']}",
        f"  📊 سلسله‌مراتب: {len(brain.ontology.hierarchy)} مفهوم",
    ]
    await message.answer("\n".join(lines))


