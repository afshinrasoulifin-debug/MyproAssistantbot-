
"""
admin_pkg/helpers.py — Arki Engine v29.0.0
"""
from ._common import *  # noqa

# ──────────── helpers ────────────

def _get_target_id(message: Message) -> int | None:
    """Extract target user ID from command args or reply."""
    # From reply.
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id

    # From command argument.
    parts = (message.text or "").split()
    if len(parts) >= 2:
        try:
            return int(parts[1])
        except ValueError as _exc:
            logger.debug("Suppressed: %s", _exc)

    return None


# ═══ v9.1: Real-time stats dashboard ═══

@router.message(Command("dashboard"))
async def cmd_dashboard(message: Message, db_user: User, settings: Settings) -> None:
    """Real-time admin dashboard."""
    if message.from_user and message.from_user.id not in settings.admin_ids:
        await safe_reply(message, "⚠️ فقط ادمین‌ها دسترسی دارند.")
        return

    try:
        from arki_project.utils.metrics_collector import get_metrics
        metrics = get_metrics()
        stats = metrics.get_all()

        uptime_h = stats.get("uptime_seconds", 0) / 3600
        counters = stats.get("counters", {})
        histograms = stats.get("histograms", {})

        total_msgs = sum(v for k, v in counters.items() if "messages_total" in k)
        total_errors = sum(v for k, v in counters.items() if "errors_total" in k)

        resp_time = histograms.get("response_time_ms", {})
        avg_resp = resp_time.get("avg", 0)
        p95_resp = resp_time.get("p95", 0)

        dashboard = (
            "📊 *Arki Engine Dashboard*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⏱ *Uptime:* {uptime_h:.1f} ساعت\n"
            f"💬 *پیام‌ها:* {total_msgs:,}\n"
            f"❌ *خطاها:* {total_errors:,}\n"
            f"⚡ *میانگین پاسخ:* {avg_resp:.0f}ms\n"
            f"📈 *P95 پاسخ:* {p95_resp:.0f}ms\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
        )

        # Memory info
        try:
            from arki_project.utils.v7_core import get_memory
            mem = get_memory()
            if hasattr(mem, '_store'):
                mem_keys = len(getattr(mem, '_store', {}))
                dashboard += f"🧠 *حافظه:* {mem_keys:,} کلید\n"
        except Exception as _exc:
            logger.debug("Suppressed: %s", _exc)

        # Cache info
        try:
            from arki_project.utils.cache_layer import get_cache
            cache = get_cache()
            cache_stats = cache.stats
            dashboard += f"💾 *کش:* {cache_stats['size']:,} آیتم ({cache_stats['hit_rate']})\n"
        except Exception as _exc:
            logger.debug("Suppressed: %s", _exc)

        await safe_reply(message, dashboard)
    except Exception as e:
        logger.error("Error in handler: %s", e)
        await safe_reply(message, f"❌ خطا: {e}")


# ═══ v9.1: Data export command ═══

@router.message(Command("export"))
async def cmd_export(message: Message, db_user: User, settings: Settings) -> None:
    """Export user's data as JSON."""
    if not message.from_user:
        return

    user_id = message.from_user.id

    try:
        import json
        from aiogram.types import BufferedInputFile

        export_data = {
            "user": {
                "telegram_id": db_user.telegram_id,
                "username": db_user.username,
                "full_name": db_user.full_name,
                "message_count": db_user.message_count or 0,
            },
        }

        # Export memory
        try:
            from arki_project.utils.v7_core import get_memory
            mem = get_memory()
            user_memories = {}
            if hasattr(mem, '_store'):
                for key, val in mem._store.items():
                    if str(user_id) in str(key):
                        user_memories[key] = val
            export_data["memories"] = user_memories
        except Exception as _exc:
            logger.debug("Suppressed: %s", _exc)

        # Export conversation history
        try:

            # Get history from AI client if available
            export_data["conversations"] = {"note": "Use /new to clear history"}
        except Exception as _exc:
            logger.debug("Suppressed: %s", _exc)

        json_bytes = json.dumps(export_data, ensure_ascii=False, indent=2, default=str).encode('utf-8')

        doc = BufferedInputFile(
            json_bytes,
            filename=f"arki_export_{user_id}.json"
        )
        await message.answer_document(doc, caption="📥 داده‌های شما")
    except Exception as e:
        logger.error("Error in handler: %s", e)
        await safe_reply(message, f"❌ خطا در خروجی: {e}")


# ═══ v9.3: Data import command ═══

@router.message(Command("import"))
async def cmd_import_data(message: Message, db_user: User, settings: Settings) -> None:
    """Import user data from JSON file."""
    if not message.document:
        await safe_reply(message,
            "📥 *وارد کردن داده‌ها*\n\n"
            "یک فایل JSON (خروجی /export) را ریپلای کنید به این دستور.")
        return

    try:
        import json
        file = await message.bot.get_file(message.document.file_id)
        data = await message.bot.download_file(file.file_path)
        imported = json.loads(data.read().decode('utf-8'))

        count = 0
        if "memories" in imported:
            try:
                from arki_project.utils.v7_core import get_memory
                mem = get_memory()
                if hasattr(mem, '_store'):
                    for key, val in imported["memories"].items():
                        mem._store[key] = val
                        count += 1
            except Exception as _exc:
                logger.debug("Suppressed: %s", _exc)

        await safe_reply(message, f"✅ {count} آیتم وارد شد.")
    except Exception as e:
        logger.error("Error in handler: %s", e)
        await safe_reply(message, f"❌ خطا: {e}")


# ═══ v9.4: Billing commands ═══

@safe_handler()
@safe_handler()
@router.message(Command("billing"))
async def cmd_billing(message: Message, db_user: User, settings: Settings) -> None:
    """Show billing status and plan info."""
    from arki_project.services.billing_service import get_billing_service
    billing = get_billing_service()
    plan = billing.get_plan(message.from_user.id)
    text = (
        "💰 *وضعیت اشتراک*\n\n"
        f"📦 پلن فعلی: *{plan.name}*\n"
        f"💵 قیمت ماهانه: ${plan.price_monthly}\n"
        f"📨 حداکثر پیام روزانه: {plan.max_messages_day:,}\n"
        f"🔑 توکن روزانه: {plan.max_tokens_day:,}\n\n"
        "*ویژگی‌ها:*\n"
    )
    for feat in plan.features:
        text += f"  ✅ {feat}\n"
    text += "\n*مدل‌های AI:*\n"
    for model in plan.ai_models:
        text += f"  🤖 {model}\n"
    text += "\n📌 ارتقا: /upgrade | کوپن: /coupon <code> | معرفی: /referral"
    await safe_reply(message, text, parse_mode="Markdown")


@safe_handler()
@safe_handler()
@router.message(Command("upgrade"))
async def cmd_upgrade(message: Message, db_user: User, settings: Settings) -> None:
    """Upgrade subscription plan."""
    from arki_project.services.billing_service import get_billing_service, PlanTier
    billing = get_billing_service()
    current = billing.get_plan(message.from_user.id)
    if current.tier == PlanTier.PRO:
        await safe_reply(message, "✅ شما قبلاً پلن حرفه‌ای دارید!")
        return
    sub = billing.start_trial(message.from_user.id, days=7)
    await safe_reply(message,
        "🎉 *دوره آزمایشی ۷ روزه حرفه‌ای فعال شد!*\n\n"
        "تمام قابلیت‌های Pro فعال شدند.\n"
        "برای خرید دائمی: /subscribe pro",
        parse_mode="Markdown")


@safe_handler()
@safe_handler()
@router.message(Command("coupon"))
async def cmd_coupon(message: Message, db_user: User, settings: Settings) -> None:
    """Apply a coupon code."""
    from arki_project.services.billing_service import get_billing_service
    billing = get_billing_service()
    parts = message.text.split(None, 1) if message.text else []
    if len(parts) < 2:
        await safe_reply(message, "❌ استفاده: /coupon <code>")
        return
    discount = billing.apply_coupon(parts[1])
    if discount:
        await safe_reply(message, f"✅ کوپن اعمال شد! تخفیف: {discount}%")
    else:
        await safe_reply(message, "❌ کوپن نامعتبر یا منقضی شده.")


@safe_handler()
@safe_handler()
@router.message(Command("referral"))
async def cmd_referral(message: Message, db_user: User, settings: Settings) -> None:
    """Get or use referral code."""
    from arki_project.services.billing_service import get_billing_service
    billing = get_billing_service()
    parts = message.text.split(None, 1) if message.text else []
    if len(parts) >= 2:
        success = billing.use_referral(parts[1], message.from_user.id)
        if success:
            await safe_reply(message, "✅ کد معرفی استفاده شد! ۱۴ روز Pro رایگان!")
        else:
            await safe_reply(message, "❌ کد نامعتبر.")
    else:
        code = billing.generate_referral_code(message.from_user.id)
        await safe_reply(message,
            f"🎁 *کد معرفی شما:* `{code}`\n\n"
            "به دوستانتان بدهید — هر دو ۱۴ روز Pro رایگان می‌گیرید!",
            parse_mode="Markdown")


# ═══ v9.4: Enterprise commands ═══

@safe_handler()
@safe_handler()
@router.message(Command("audit"))
async def cmd_audit(message: Message, db_user: User, settings: Settings) -> None:
    """Show audit log (admin only)."""
    from arki_project.services.enterprise import get_audit_log
    audit = get_audit_log()
    entries = audit.query(since=0)[-20:]  # last 20
    if not entries:
        await safe_reply(message, "📋 لاگ حسابرسی خالی است.")
        return
    text = "📋 *آخرین ۲۰ رویداد حسابرسی:*\n\n"
    for e in entries[-10:]:
        import datetime
        ts = datetime.datetime.fromtimestamp(e.timestamp).strftime("%H:%M:%S")
        text += f"`{ts}` {e.action.value} — user:{e.user_id} — {e.resource}\n"
    await safe_reply(message, text, parse_mode="Markdown")


@router.message(Command("gdpr_export"))
async def cmd_gdpr_export(message: Message, db_user: User, settings: Settings) -> None:
    """Export user data (GDPR)."""
    from arki_project.services.enterprise import get_gdpr
    gdpr = get_gdpr()
    data = await gdpr.export_user_data(message.from_user.id)
    import json
    from aiogram.types import BufferedInputFile
    doc = BufferedInputFile(
        json.dumps(data, indent=2, default=str).encode('utf-8'),
        filename=f"gdpr_export_{message.from_user.id}.json"
    )
    await message.answer_document(doc, caption="📦 داده‌های شما (GDPR)")


@router.message(Command("gdpr_delete"))
async def cmd_gdpr_delete(message: Message, db_user: User, settings: Settings) -> None:
    """Delete user data (GDPR right to be forgotten)."""
    from arki_project.services.enterprise import get_gdpr
    gdpr = get_gdpr()
    result = await gdpr.delete_user_data(message.from_user.id)
    await safe_reply(message,
        "🗑 *داده‌های شما حذف شد*\n\n"
        f"حافظه: {result.get('memories', 0)} مورد\n"
        f"بردارها: {result.get('vectors', 0)} مورد",
        parse_mode="Markdown")


@router.message(Command("team"))
async def cmd_team(message: Message, db_user: User, settings: Settings) -> None:
    """Manage team members."""
    from arki_project.services.enterprise import get_team_manager, TeamRole
    team = get_team_manager()
    members = team.list_members()
    if not members:
        team.add_member(message.from_user.id, TeamRole.OWNER)
        members = team.list_members()
    text = "👥 *اعضای تیم:*\n\n"
    for m in members:
        text += f"• User {m.user_id} — {m.role.value} — {len(m.permissions)} دسترسی\n"
    await safe_reply(message, text, parse_mode="Markdown")


# ═══ v9.4: Network tools ═══

@router.message(Command("network"))
async def cmd_network(message: Message, db_user: User, settings: Settings) -> None:
    """Network diagnostic tools (admin)."""
    parts = message.text.split(None, 2) if message.text else []
    if len(parts) < 2:
        await safe_reply(message,
            "🌐 *ابزارهای شبکه*\n\n"
            "• `/network ping <host>`\n"
            "• `/network scan <host>`\n"
            "• `/network dns <domain>`")
        return
    action = parts[1].lower()
    target = parts[2] if len(parts) > 2 else ""
    try:
        if action == "scan" and target:
            from arki_project.utils.network_scanner import NetworkScanner
            scanner = NetworkScanner()
            result = await scanner.scan(target)
            await safe_reply(message, f"🔍 *نتایج اسکن {target}:*\n```{result}```", parse_mode="Markdown")
        elif action == "ping" and target:
            from arki_project.utils.network_tools import ping
            result = await ping(target)
            await safe_reply(message, f"🏓 Ping {target}: {result}")
        elif action == "dns" and target:
            from arki_project.utils.network_tools import dns_lookup
            result = await dns_lookup(target)
            await safe_reply(message, f"🌐 DNS {target}:\n```{result}```", parse_mode="Markdown")
        else:
            await safe_reply(message, "❌ استفاده: /network <ping|scan|dns> <target>")
    except Exception as e:
        logger.error("Error in handler: %s", e)
        await safe_reply(message, f"❌ خطا: {e}")


# ═══ v9.4: Feature flags ═══

@router.message(Command("feature"))
async def cmd_feature(message: Message, db_user: User, settings: Settings) -> None:
    """Toggle feature flags (admin)."""
    from arki_project.utils.feature_flags import get_feature_flags
    ff = get_feature_flags()
    parts = message.text.split(None, 2) if message.text else []
    if len(parts) >= 3 and parts[1] == "toggle":
        new_state = ff.toggle(parts[2])
        status = "✅ فعال" if new_state else "❌ غیرفعال"
        await safe_reply(message, f"🏴 `{parts[2]}` → {status}")
        return
    flags = ff.list_all()
    text = "🏴 *وضعیت Feature Flags:*\n\n"
    for name, enabled in sorted(flags.items()):
        icon = "✅" if enabled else "❌"
        text += f"{icon} `{name}`\n"
    text += "\n🔄 تغییر: `/feature toggle <name>`"
    await safe_reply(message, text, parse_mode="Markdown")


# ══════════ v10.3: Victor Stats ══════════
@router.message(Command("victorstats"))
async def cmd_victor_stats(message: Message, settings: Settings = None, **kwargs) -> None:
    """Show Victor v6 brain statistics. Admin only."""
    if settings and message.from_user:
        if message.from_user.id not in settings.admin_ids:
            await message.answer("⛔ فقط ادمین‌ها دسترسی دارند.")
            return

    try:
        from arki_project.handlers.victor import VictorBrain
        brain = VictorBrain()
        stats = brain.memory.get_stats()
        lines = [
            "🧠 *Victor v6 — Brain Stats*",
            f"📊 کل خاطرات: `{stats.get('total_memories', 0)}`",
            f"🔗 اتصالات گراف: `{stats.get('graph_edges', 0)}`",
            f"📏 قوانین استنتاج: `{stats.get('inference_rules', 0)}`",
            f"📝 تصحیحات: `{stats.get('corrections', 0)}`",
            f"💬 تعامل‌ها: `{stats.get('total_interactions', 0)}`",
            f"📖 آموزش‌ها: `{stats.get('total_teachings', 0)}`",
            f"📚 واژگان TF-IDF: `{stats.get('vocabulary_size', 0)}`",
            f"💪 میانگین قدرت: `{stats.get('avg_strength', 0):.1f}`",
            f"🧩 عمق مکالمه: `{stats.get('context_depth', 0)}`",
        ]
        if stats.get("by_type"):
            type_str = " | ".join(f"{t}: {c}" for t, c in stats["by_type"].items())
            lines.append(f"📂 انواع: `{type_str}`")
        await message.answer("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"Victor stats error: {e}")


# ══════════ v10.3: Performance Stats ══════════
@router.message(Command("perfstats"))
async def cmd_perf_stats(message: Message, settings: Settings = None, **kwargs) -> None:
    """Show handler performance statistics. Admin only."""
    if settings and message.from_user:
        if message.from_user.id not in settings.admin_ids:
            await message.answer("⛔ فقط ادمین‌ها دسترسی دارند.")
            return

    try:
        from arki_project.utils.performance_tracker import perf_tracker
        stats = perf_tracker.get_stats()
        if not stats:
            await message.answer("📊 هنوز آماری ثبت نشده.")
            return

        lines = ["📊 *Performance Stats*", ""]
        for op, data in sorted(stats.items(), key=lambda x: x[1].get("avg_ms", 0), reverse=True)[:15]:
            avg_ms = data.get("avg_ms", 0)
            count = data.get("count", 0)
            errors = data.get("errors", 0)
            p95 = data.get("p95_ms", 0)
            icon = "🔴" if avg_ms > 2000 else "🟡" if avg_ms > 1000 else "🟢"
            err_tag = f" ⚠️{errors}err" if errors else ""
            lines.append(f"{icon} `{op}`: avg={avg_ms:.0f}ms p95={p95:.0f}ms n={count}{err_tag}")
        await message.answer("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"Performance stats error: {e}")


# ═══════════════════════════════════════════════════════════════════
# v26.0: AI Performance Stats Generator
# ═══════════════════════════════════════════════════════════════════

async def generate_ai_stats_message() -> str:
    """Generate AI performance statistics message in Farsi."""
    if not _HAS_ANALYTICS:
        return "📊 آمار عملکرد هنوز در دسترس نیست."
    
    try:
        analytics = _get_pa()
        return analytics.format_stats_message()
    except Exception as e:
        return f"⚠️ خطا در بارگذاری آمار: {e}"



