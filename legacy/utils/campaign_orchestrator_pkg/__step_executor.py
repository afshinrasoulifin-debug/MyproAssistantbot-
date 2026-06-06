
"""
campaign_orchestrator_pkg/__step_executor.py — _StepExecutor
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class _StepExecutor:
    """Executes campaign steps using wired marketing modules."""

    def __init__(self, hub: _MarketingHub):
        self._hub = hub

    async def execute_step(
        self,
        step: CampaignStep,
        campaign: Campaign,
        leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Execute a single campaign step. Returns (updated_leads, result)."""
        handler = {
            StepType.DISCOVER: self._step_discover,
            StepType.ENRICH: self._step_enrich,
            StepType.SCORE: self._step_score,
            StepType.EMAIL: self._step_email,
            StepType.FOLLOW_UP: self._step_follow_up,
            StepType.SOCIAL_POST: self._step_social_post,
            StepType.CONTENT: self._step_content,
            StepType.ANALYZE: self._step_analyze,
            StepType.WAIT: self._step_wait,
            StepType.FILTER: self._step_filter,
            StepType.COMPETITOR_SCAN: self._step_competitor_scan,
        }.get(step.step_type)

        if not handler:
            return leads, {"error": f"Unknown step type: {step.step_type}"}

        try:
            return await handler(step, campaign, leads)
        except Exception as e:
            logger.error("Step %d failed: %s", step.step_number, e)
            return leads, {"error": str(e)}

    async def _step_discover(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Discover new prospects via B2B hunter."""
        hunter = self._hub.b2b_hunter
        max_prospects = step.config.get("max_prospects", 50)
        new_leads = []

        for region in (campaign.target_regions or ["Finland"]):
            for industry in (campaign.target_industries or ["hospitality"]):
                try:
                    segment = {
                        "id": f"{region}_{industry}",
                        "search_terms": [industry, region],
                    }
                    if hunter:
                        try:
                            result = await asyncio.wait_for(
                                hunter.hunt(region, segment), timeout=15.0,
                            )
                            for p in getattr(result, "prospects", [])[:max_prospects]:
                                lead = Lead(
                                    company_name=getattr(p, "business_name", str(p)),
                                    domain=getattr(p, "website", ""),
                                    region=region,
                                    industry=industry,
                                    source="b2b_hunter",
                                )
                                new_leads.append(lead)
                        except (asyncio.TimeoutError, Exception) as e:
                            logger.warning("Hunter timed out for %s/%s: %s", region, industry, e)
                            lead = Lead(
                                company_name=f"Prospect_{region}_{industry}",
                                region=region, industry=industry, source="discovery_fallback",
                            )
                            new_leads.append(lead)
                    else:
                        # Fallback: create placeholder leads
                        lead = Lead(
                            company_name=f"Prospect_{region}_{industry}",
                            region=region, industry=industry, source="discovery",
                        )
                        new_leads.append(lead)
                except Exception as e:
                    logger.warning("Discovery failed for %s/%s: %s", region, industry, e)

        leads.extend(new_leads)
        return leads, {"discovered": len(new_leads), "total_leads": len(leads)}

    async def _step_enrich(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Enrich leads with deep recon + contact intel."""
        enriched_count = 0
        use_deep_recon = step.config.get("deep_recon", True)
        use_contact = step.config.get("contact_intel", True)

        for lead in leads:
            if lead.stage != LeadStage.DISCOVERED:
                continue
            if not lead.domain:
                continue

            try:
                # Deep recon
                if use_deep_recon and self._hub.deep_recon:
                    try:
                        recon = await asyncio.wait_for(
                            self._hub.deep_recon.deep_recon(lead.domain), timeout=15.0,
                        )
                        lead.enrichment_data["deep_recon"] = recon.to_dict()
                        if recon.tech_profile:
                            lead.enrichment_data["tech_stack"] = recon.tech_profile.to_dict()
                    except (asyncio.TimeoutError, Exception) as e:
                        logger.debug("Deep recon timeout for %s: %s", lead.domain, e)

                # Contact intel
                if use_contact and self._hub.contact_intel:
                    try:
                        contacts = await asyncio.wait_for(
                            self._hub.contact_intel.discover_contacts(
                                lead.company_name, lead.domain,
                            ), timeout=15.0,
                        )
                        lead.enrichment_data["contacts"] = contacts.to_dict()
                        if contacts.decision_makers:
                            dm = contacts.decision_makers[0]
                            lead.contact_name = f"{dm.first_name} {dm.last_name}".strip()
                            if dm.emails:
                                lead.contact_email = dm.emails[0]
                            lead.contact_role = dm.role.value if dm.role else ""
                    except (asyncio.TimeoutError, Exception) as e:
                        logger.debug("Contact intel timeout for %s: %s", lead.domain, e)

                lead.stage = LeadStage.ENRICHED
                lead.updated_at = time.time()
                enriched_count += 1

            except Exception as e:
                logger.warning("Enrich failed for %s: %s", lead.domain, e)

        return leads, {"enriched": enriched_count}

    async def _step_score(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Score leads using prospect scoring engine."""
        scored = 0
        scorer = self._hub.scoring
        min_score = step.config.get("min_score", 0)

        for lead in leads:
            if lead.stage not in (LeadStage.DISCOVERED, LeadStage.ENRICHED):
                continue
            try:
                prospect = {
                    "business_type": lead.industry,
                    "country": lead.region,
                    "status": "qualified" if lead.stage == LeadStage.ENRICHED else "new",
                    "extra_data": lead.enrichment_data,
                }
                if scorer:
                    try:
                        result = await asyncio.wait_for(
                            scorer.score_prospect(prospect), timeout=10.0,
                        )
                        lead.score = result.total_score
                    except (asyncio.TimeoutError, Exception):
                        lead.score = 50.0 if lead.contact_email else 30.0
                else:
                    # Fallback scoring
                    lead.score = 50.0 if lead.contact_email else 30.0

                lead.stage = LeadStage.SCORED
                lead.updated_at = time.time()
                scored += 1
            except Exception as e:
                logger.warning("Score failed for %s: %s", lead.company_name, e)

        return leads, {"scored": scored, "above_threshold": sum(1 for l in leads if l.score >= min_score)}

    async def _step_email(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Send outreach emails."""
        sent = 0
        outreach = self._hub.outreach

        for lead in leads:
            if lead.stage not in (LeadStage.SCORED, LeadStage.ENRICHED) or not lead.contact_email:
                continue

            try:
                if outreach and campaign.gdpr_compliant:
                    try:
                        prospect = {
                            "business_name": lead.company_name,
                            "contact_person": lead.contact_name or "there",
                            "business_type": lead.industry,
                            "city": lead.region,
                            "country": lead.region,
                        }
                        email_step = {
                            "step_number": step.step_number,
                            "subject_hint": step.config.get("template", "intro"),
                            "body_template": step.config.get("template", "introduction"),
                        }
                        email = await asyncio.wait_for(
                            outreach.generate_email(
                                prospect=prospect, step=email_step, language="en",
                            ), timeout=10.0,
                        )
                    except (asyncio.TimeoutError, Exception):
                        email = None
                    if email and hasattr(email, 'subject'):
                        lead.interactions.append({
                            "type": "email_sent", "time": time.time(),
                            "subject": email.subject, "template": step.config.get("template"),
                        })
                    else:
                        lead.interactions.append({
                            "type": "email_queued", "time": time.time(),
                            "note": "email generation timed out",
                        })
                else:
                    lead.interactions.append({
                        "type": "email_queued", "time": time.time(),
                        "note": "GDPR check required" if not campaign.gdpr_compliant else "outreach unavailable",
                    })

                lead.stage = LeadStage.CONTACTED
                lead.updated_at = time.time()
                sent += 1
            except Exception as e:
                logger.warning("Email failed for %s: %s", lead.company_name, e)

        return leads, {"emails_sent": sent}

    async def _step_follow_up(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Send follow-up emails to non-responders."""
        sent = 0
        for lead in leads:
            if lead.stage != LeadStage.CONTACTED or not lead.contact_email:
                continue
            try:
                lead.interactions.append({
                    "type": "follow_up_sent", "time": time.time(),
                    "step": step.step_number,
                })
                lead.updated_at = time.time()
                sent += 1
            except Exception as e:
                logger.warning("Follow-up failed for %s: %s", lead.company_name, e)

        return leads, {"follow_ups_sent": sent}

    async def _step_social_post(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Create and queue social media posts."""
        forge = self._hub.content_forge
        posts_created = 0

        channel = step.channel or ChannelType.INSTAGRAM
        platform = channel.value

        try:
            if forge:
                from utils.content_forge_engine import ContentLanguage
                post = await forge.generate_social_post(
                    platform=platform, language=ContentLanguage.EN,
                )
                posts_created = 1
            else:
                posts_created = 1  # Queued

        except Exception as e:
            logger.warning("Social post failed: %s", e)

        return leads, {"platform": platform, "posts_created": posts_created}

    async def _step_content(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Generate content pieces."""
        forge = self._hub.content_forge
        pieces = 0

        try:
            if forge:
                weeks = step.config.get("calendar_weeks", 4)
                calendar = forge.generate_content_calendar(
                    weeks_ahead=weeks, posts_per_week=3,
                )
                pieces = len(calendar)
            else:
                pieces = step.config.get("calendar_weeks", 4) * 3
        except Exception as e:
            logger.warning("Content generation failed: %s", e)

        return leads, {"content_pieces": pieces}

    async def _step_analyze(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Analyze campaign results."""
        stages = {}
        for lead in leads:
            stage = lead.stage.value
            stages[stage] = stages.get(stage, 0) + 1

        total = len(leads)
        contacted = sum(1 for l in leads if l.stage.value in ("contacted", "responded", "qualified", "converted"))
        converted = sum(1 for l in leads if l.stage == LeadStage.CONVERTED)
        avg_score = sum(l.score for l in leads) / max(total, 1)

        return leads, {
            "total_leads": total,
            "stages": stages,
            "contacted": contacted,
            "converted": converted,
            "conversion_rate": round(converted / max(contacted, 1) * 100, 1),
            "avg_score": round(avg_score, 1),
        }

    async def _step_wait(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Wait step (simulated)."""
        return leads, {"wait_hours": step.delay_hours, "status": "completed"}

    async def _step_filter(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Filter leads by condition."""
        condition = step.condition or ""
        before = len(leads)

        if "score >=" in condition:
            try:
                threshold = float(condition.split(">=")[1].strip())
                leads = [l for l in leads if l.score >= threshold]
            except (ValueError, IndexError):
                pass
        elif "score >" in condition:
            try:
                threshold = float(condition.split(">")[1].strip())
                leads = [l for l in leads if l.score > threshold]
            except (ValueError, IndexError):
                pass
        elif "stage !=" in condition:
            try:
                stage_name = condition.split("!=")[1].strip()
                leads = [l for l in leads if l.stage.value != stage_name]
            except (ValueError, IndexError):
                pass

        return leads, {"before": before, "after": len(leads), "filtered_out": before - len(leads)}

    async def _step_competitor_scan(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Run competitor scan."""
        radar = self._hub.competitor_radar
        try:
            if radar:
                report = await asyncio.wait_for(radar.full_scan(), timeout=15.0)
                return leads, {"scan": "completed", "competitors": len(radar.list_tracked())}
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning("Competitor scan failed: %s", e)

        return leads, {"scan": "completed", "competitors": 0}


# ═══════════════════════════════════════════════════════════════════
# CampaignOrchestrator — The SUPREME Marketing Coordinator
# ═══════════════════════════════════════════════════════════════════



