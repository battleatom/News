#!/usr/bin/env python3
"""Generate story-specific Why It Matters explanations.

Entertainment, Technology, and Gaming first build a structured story context:
subject -> event -> affected party -> consequence -> confidence. The rendered
sentence must include story-specific entities/focus instead of a tab-wide canned
template. Other categories retain the established production rules.
"""
from pathlib import Path
import html
import re
import xml.etree.ElementTree as ET

NEWS = Path("News")

EVENT_VERBS = (
    "announce", "announces", "announced", "unveils", "unveiled", "launches", "launched",
    "releases", "released", "raises", "raised", "increases", "increased",
    "cuts", "cut", "delays", "delayed", "postpones", "postponed",
    "acquires", "acquired", "buys", "bought", "merges", "merged",
    "sues", "sued", "files", "filed", "joins", "joined", "casts", "cast",
    "renews", "renewed", "cancels", "canceled", "cancelled", "wins", "won",
    "dies", "died", "hospitalized", "hospitalised", "reveals", "revealed",
    "confirms", "confirmed", "introduces", "introduced", "adds", "added",
    "removes", "removed", "updates", "updated", "patches", "patched",
    "signs", "signed", "partners", "partnered", "opens", "opened",
    "closes", "closed", "shuts", "expands", "expanded", "prices", "priced",
)

GENERIC_SUBJECTS = {
    "company", "companies", "actor", "actress", "artist", "singer", "studio",
    "developer", "publisher", "game", "major game", "report", "technology",
    "executives", "couple", "celebrity",
}


def clean(v):
    v = html.unescape(v or "")
    v = re.sub(r"<[^>]+>", " ", v)
    return re.sub(r"\s+", " ", v).strip()


def has(text, *terms):
    return any(re.search(r"\b" + re.escape(t) + r"\b", text, re.I) for t in terms)


def count_terms(text, *terms):
    return sum(bool(re.search(r"\b" + re.escape(t) + r"\b", text, re.I)) for t in terms)


def strip_source_suffix(title: str, source: str) -> str:
    out = clean(title)
    if source:
        out = re.sub(rf"\s*[-–—|:]\s*{re.escape(source)}\s*$", "", out, flags=re.I)
    return out.strip(" -–—|:")


def _event_match(title: str):
    verbs = "|".join(sorted((re.escape(v) for v in EVENT_VERBS), key=len, reverse=True))
    return re.search(rf"\b({verbs})\b", title, re.I)


def headline_subject(title: str, source: str = "") -> str:
    title = strip_source_suffix(title, source)
    if ":" in title:
        left, right = title.split(":", 1)
        if 2 <= len(left.split()) <= 9 and 3 <= len(left) <= 80 and len(right.strip()) >= 8:
            return left.strip(" -–—|:")
    match = _event_match(title)
    if match:
        subject = title[:match.start()].strip(" -–—|:,")
        if 2 <= len(subject) <= 95:
            return subject
    words = title.split()
    if len(words) <= 10:
        return title.strip(" -–—|:")
    return " ".join(words[:9]).strip(" -–—|:,")


def headline_focus(title: str, subject: str, source: str = "") -> str:
    title = strip_source_suffix(title, source)
    match = _event_match(title)
    focus = title[match.end():] if match else title
    if subject and focus.lower().startswith(subject.lower()):
        focus = focus[len(subject):]
    focus = re.sub(r"^(?:its|the|a|an)\s+", "", focus.strip(" -–—|:,"), flags=re.I)
    focus = re.sub(r"\s+", " ", focus).strip()
    if not focus:
        return ""
    words = focus.split()
    return " ".join(words[:14]).rstrip(" ,;:-")


def specific_number(text: str) -> str:
    patterns = (
        r"\$\d[\d,]*(?:\.\d+)?(?:\s*(?:million|billion|trillion))?",
        r"\b\d+(?:\.\d+)?%",
        r"\b20\d{2}\b",
        r"\b\d+(?:\.\d+)?\s*(?:million|billion|GB|TB|fps|Hz)\b",
    )
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return m.group(0)
    return ""


def possessive_topic(subject: str, focus: str) -> str:
    subject = clean(subject).rstrip(" .,:;")
    focus = clean(focus).rstrip(" .,:;")
    if not focus or focus.lower() in subject.lower():
        return subject
    if subject.endswith(("s", "S")):
        return f"{subject}' {focus}"
    return f"{subject}'s {focus}"


def _context(cat: str, title: str, brief: str, source: str = "") -> dict[str, str]:
    text = f"{title} {brief}".lower()
    subject = headline_subject(title, source)
    focus = headline_focus(title, subject, source)
    number = specific_number(f"{title} {brief}")
    generic = subject.lower() in GENERIC_SUBJECTS or len(subject.split()) < 1
    confidence = "medium" if generic else "high"

    def ctx(event: str, affected: str, consequence: str, confidence_override: str | None = None):
        return {
            "subject": subject,
            "focus": focus,
            "detail": number,
            "event": event,
            "affected": affected,
            "consequence": consequence,
            "confidence": confidence_override or confidence,
        }

    if cat == "technology":
        if has(text, "data breach", "breach", "ransomware", "cyberattack", "hacked", "hack"):
            return ctx("security incident", "users and organizations tied to the affected systems", "exposed accounts, data, or disrupted operations may require remediation")
        if has(text, "outage", "service disruption", "offline", "downtime"):
            return ctx("service outage", "people and businesses relying on the service", "loss of access can interrupt work, communication, or transactions until service is restored")
        if has(text, "vulnerability", "security flaw", "zero-day", "zero day", "exploit", "patch"):
            return ctx("security vulnerability", "users of the affected product", "unpatched systems can remain exposed until a fix is installed")
        if has(text, "antitrust", "lawsuit", "sued", "court", "ruling", "regulator", "regulation", "ban"):
            return ctx("legal or regulatory action", "the company, customers, and competitors", "the outcome can change product rules, distribution, or competitive behavior")
        if has(text, "layoffs", "layoff", "job cuts", "cuts jobs", "workforce reduction"):
            return ctx("workforce reduction", "employees and teams tied to current products", "staffing cuts can change support capacity, spending, and the product roadmap")
        if has(text, "acquisition", "acquire", "acquires", "acquired", "merger", "merges"):
            return ctx("acquisition or merger", "employees, customers, and overlapping competitors", "new ownership can change product priorities, pricing, staffing, and competition")
        if has(text, "price increase", "raises prices", "price hike", "subscription price", "pricing", "price rises"):
            return ctx("pricing change", "current and prospective customers", "the change directly alters customer cost and can affect adoption, cancellations, and competitor pricing")
        if has(text, "ai model", "artificial intelligence model", "llm", "large language model"):
            return ctx("AI model development", "developers and organizations using AI", "capability, cost, or access can shift the competitive benchmark for other model providers")
        if has(text, "gpu", "cpu", "processor", "chip", "semiconductor"):
            return ctx("chip or processor development", "hardware buyers and device makers", "performance, efficiency, supply, or price can shape competing chips and future devices")
        if has(text, "iphone", "ipad", "smartphone", "laptop", "macbook", "device", "headset", "smart glasses", "wearable"):
            return ctx("device development", "buyers and competing device makers", "features and pricing can influence upgrade decisions and competing product roadmaps")
        if has(text, "partnership", "partners with", "integration", "integrates", "deal"):
            return ctx("partnership or integration", "users of the connected products and competing ecosystems", "distribution or interoperability can change what users can access and how the companies compete")
        if has(text, "privacy", "tracking", "user data", "data collection"):
            return ctx("privacy or data-policy change", "people whose data is collected or processed", "the change can alter privacy exposure, trust, and compliance obligations")
        if has(text, "software", "platform", "operating system", "app", "browser"):
            return ctx("software or platform change", "users, developers, and businesses depending on the platform", "compatibility, workflows, or platform rules can change")
        return ctx("technology update", "users, developers, customers, or competitors", "the reporting does not yet establish a measurable downstream effect", "low")

    if cat == "gaming":
        if has(text, "delay", "delayed", "pushed back", "postponed"):
            return ctx("release delay", "players, the publisher, and competing releases", "the release calendar and revenue timing move, leaving competitors a different launch window")
        if has(text, "studio closure", "studio closes", "studio closed", "shuts down", "shutdown", "cancelled", "canceled"):
            return ctx("studio or project shutdown", "developers and players tied to the project", "active projects, live support, or planned releases can end or change")
        if has(text, "layoffs", "layoff", "job cuts", "cuts jobs", "workforce reduction"):
            return ctx("gaming workforce reduction", "development teams and players awaiting their projects", "staffing cuts can reduce the scope, pace, or support of current and future games")
        if has(text, "acquisition", "acquire", "acquires", "acquired", "merger", "buys studio", "bought studio"):
            return ctx("studio acquisition or merger", "developers, players, and platform holders", "ownership can change creative control, staffing, funding, and platform availability")
        if has(text, "game pass", "playstation plus", "ps plus", "subscription", "price increase", "price hike"):
            return ctx("gaming subscription change", "subscribers and prospective players", "the change alters player cost or service value and can affect subscriptions and platform loyalty")
        if has(text, "console", "handheld", "playstation", "xbox", "nintendo switch", "switch 2"):
            return ctx("gaming hardware development", "players and developers choosing target platforms", "hardware capability, price, and availability can shape purchases and future game support")
        if has(text, "patch", "update", "season", "dlc", "expansion"):
            return ctx("game update or expansion", "current players and the live-service community", "balance, content, or progression changes can affect retention and the game's active lifespan")
        if has(text, "lawsuit", "sued", "court", "regulation", "ban"):
            return ctx("gaming legal or regulatory action", "the publisher, platform, developers, and players", "the outcome can change business practices, distribution, or access")
        if has(text, "sales", "sold", "record", "copies", "players", "concurrent players"):
            return ctx("audience or sales performance", "the publisher, developers, and platform partners", "measured demand can influence sequels, investment, marketing, and publishing decisions")
        if has(text, "release date", "launch", "released", "debut"):
            return ctx("game release", "players, the publisher, and nearby competing releases", "the commercial window determines when sales, adoption, reviews, and competition begin")
        return ctx("gaming update", "players, developers, publishers, or platform holders", "the reporting does not yet establish a measurable downstream effect", "low")

    if cat.startswith("entertainment"):
        if has(text, "died", "dies", "death", "dead", "hospitalized", "hospitalised", "cancer", "serious illness"):
            return ctx("death or serious health development", "the person, family, collaborators, and scheduled productions", "professional commitments, productions, or touring may change in addition to the personal impact")
        if has(text, "lawsuit", "sued", "court", "charged", "arrested", "indicted", "investigation"):
            return ctx("legal dispute or investigation", "the person, business partners, and active productions", "contracts, finances, reputation, or ongoing projects can be affected as the case develops")
        if has(text, "cast", "casting", "joins cast", "starring", "role"):
            return ctx("casting or role", "the performer, production, and its audience", "the choice can shape the project while changing the performer's visibility and future negotiating leverage")
        if has(text, "renewed", "renewal", "canceled", "cancelled", "greenlit", "greenlight"):
            return ctx("renewal, cancellation, or greenlight", "cast, crew, audience, and distributor", "the decision determines whether production continues and where programming resources are committed")
        if has(text, "box office", "opening weekend", "ticket sales"):
            return ctx("box-office performance", "the production, distributor, theaters, and future projects", "ticket demand can influence marketing, sequel plans, theatrical strategy, and investment")
        if has(text, "oscar", "oscars", "emmy", "emmys", "grammy", "grammys", "golden globe", "award", "nomination", "nominated", "wins", "winner"):
            return ctx("award or nomination", "the nominee or winner and associated production", "recognition can raise profile, negotiating leverage, financing prospects, and awards-season momentum")
        if has(text, "album", "single", "tour", "concert"):
            return ctx("music release or tour development", "the artist, fans, promoters, and commercial partners", "streaming, ticketing, promotion, and audience attention can shift")
        if has(text, "movie", "film", "series", "show", "trailer", "premiere", "release date"):
            return ctx("film or television release milestone", "the production, distributor, cast, and audience", "audience response can shape marketing, distribution, revenue, and prospects for follow-up projects")
        if has(text, "deal", "contract", "signs", "acquisition", "rights", "distribution"):
            return ctx("entertainment business agreement", "the people and companies controlling or distributing the work", "control, financing, distribution, or profit participation can change")
        if has(text, "pregnant", "pregnancy", "baby", "gave birth", "gives birth", "welcomes son", "welcomes daughter", "engaged", "engagement", "married", "wedding", "dating", "boyfriend", "girlfriend", "breakup", "split"):
            return ctx("personal celebrity update", "the people involved and their audience", "the reporting does not establish a broader entertainment-industry consequence", "medium")
        if has(text, "charity", "philanthropy", "donation", "fundraiser", "fundraising", "benefit gala"):
            return ctx("philanthropy or fundraiser", "the stated cause, participants, and beneficiaries", "money, attention, or participation can flow directly to the cause")
        if has(text, "bikini", "swimsuit", "sheer", "see-through", "topless", "nude", "red carpet", "fashion"):
            return ctx("celebrity or fashion update", "the person, audience, and any associated campaign", "the reporting shows limited wider industry impact unless it is tied to a contract, campaign, or production", "low")
        return ctx("entertainment update", "the people, project, or audience directly involved", "the reporting does not yet establish a wider industry consequence", "low")

    return {
        "subject": subject,
        "focus": focus,
        "detail": number,
        "event": "",
        "affected": "",
        "consequence": "",
        "confidence": "medium",
    }


def _targeted_why(context: dict[str, str]) -> str:
    subject = context["subject"] or "The story"
    focus = context["focus"]
    event = context["event"]
    consequence = context["consequence"]
    affected = context["affected"]
    detail = context["detail"]
    topic = possessive_topic(subject, focus)

    if event == "pricing change":
        label = topic
        if detail and detail not in label:
            label = f"{subject}'s reported {detail} pricing change"
        return f"{label} matters to {affected} because it directly changes customer cost and can affect adoption, cancellations, and competitor pricing."
    if event == "release delay":
        detail_text = f" into {detail}" if detail and detail.isdigit() and detail.startswith("20") else ""
        return f"{subject}'s delay{detail_text} affects {affected} because {consequence}."
    if event == "gaming subscription change":
        if focus.lower().startswith("to "):
            label = f"{subject} change {focus}"
        else:
            label = topic
        return f"{label} matters to {affected} because {consequence}."
    if event == "personal celebrity update":
        return f"The {event} involving {subject} is relevant mainly to {affected}; {consequence}."
    if event == "casting or role":
        role_focus = re.sub(r"^(?:cast of|cast in|role in)\s+", "", focus, flags=re.I)
        label = f"{subject}'s role"
        if role_focus:
            label += f" in {role_focus}"
        return f"{label} matters to {affected} because {consequence}."
    if event in {"legal dispute or investigation", "award or nomination", "box-office performance",
                 "music release or tour development", "film or television release milestone",
                 "entertainment business agreement", "renewal, cancellation, or greenlight",
                 "death or serious health development", "philanthropy or fundraiser",
                 "celebrity or fashion update"}:
        return f"{topic} matters to {affected} because {consequence}."
    if event in {"security incident", "service outage", "security vulnerability", "legal or regulatory action",
                 "workforce reduction", "acquisition or merger", "AI model development",
                 "chip or processor development", "device development", "partnership or integration",
                 "privacy or data-policy change", "software or platform change"}:
        return f"{topic} matters to {affected} because {consequence}."
    if event in {"studio or project shutdown", "gaming workforce reduction", "studio acquisition or merger",
                 "gaming hardware development", "game update or expansion",
                 "gaming legal or regulatory action", "audience or sales performance", "game release"}:
        return f"{topic} matters to {affected} because {consequence}."
    return f"The report about {topic} is mainly an update; {consequence}."


def why_context(item) -> dict[str, str]:
    title = clean(item.findtext("title"))
    brief = clean(item.findtext("description"))
    cat = clean(item.findtext("category")).lower()
    source = clean(item.findtext("source"))
    return _context(cat, title, brief, source)


def why_for(item):
    brief = clean(item.findtext("description"))
    title = clean(item.findtext("title"))
    cat = clean(item.findtext("category")).lower()
    text = f"{title} {brief}".lower()

    if cat in {"technology", "gaming"} or cat.startswith("entertainment"):
        return "Why it matters: " + _targeted_why(why_context(item))

    military = ("war", "airstrike", "missile", "troops", "ceasefire", "invasion", "attack", "military", "bombing", "combat")
    if cat == "military" or count_terms(text, *military) >= 2:
        impact = "It may affect security, military operations, diplomacy, or civilians connected to the conflict."
    elif has(text, "court", "judge", "ruling", "lawsuit", "appeal", "injunction", "law"):
        impact = "It may affect legal rights, enforcement, government authority, or what happens next in the case or policy."
    elif has(text, "recall", "outbreak", "hospital", "medicaid", "medicare", "health", "healthcare", "safety"):
        impact = "It may affect public health, access to care, consumer safety, or costs for people and institutions involved."
    elif has(text, "payment", "payments", "check", "checks", "rebate", "refund", "payout", "cash"):
        impact = "It may affect eligibility, household finances, government spending, or the timing and rules of any proposed payment."
    elif has(text, "election", "elections", "midterm", "ballot", "voting", "campaign"):
        impact = "It may affect election administration, campaign strategy, voter information, or the political debate around the issue."
    elif has(text, "breach", "hack", "cybersecurity", "privacy", "surveillance", "outage", "ai", "software"):
        impact = "It may affect privacy, security, access to technology, users, or how the technology is regulated and deployed."
    elif has(text, "wildfire", "flood", "hurricane", "tornado", "earthquake", "drought", "climate"):
        impact = "It may affect public safety, infrastructure, property, emergency response, or environmental conditions."
    elif cat == "nfl" or has(text, "nfl", "quarterback", "playoffs", "touchdown"):
        impact = "It may affect team availability, standings, roster decisions, or upcoming games."
    elif cat in {"presidential", "federal", "us", "world", "nm", "local", "region"}:
        impact = "It may affect public policy, government operations, communities, or people directly connected to the development."
    else:
        impact = "It may affect the people, organizations, services, or decisions directly connected to the development."
    return "Why it matters: " + impact


def set_text(item: ET.Element, tag: str, value: str) -> None:
    node = item.find(tag)
    if node is None:
        node = ET.SubElement(item, tag)
    node.text = value


def main():
    tree = ET.parse(NEWS)
    items = tree.getroot().findall(".//item")
    updated = 0
    for item in items:
        cat = clean(item.findtext("category")).lower()
        if cat == "legislation" or not clean(item.findtext("description")):
            continue
        set_text(item, "whyMatters", why_for(item))
        if cat in {"technology", "gaming"} or cat.startswith("entertainment"):
            context = why_context(item)
            set_text(item, "whySubject", context["subject"])
            set_text(item, "whyEvent", context["event"])
            set_text(item, "whyAffected", context["affected"])
            set_text(item, "whyConsequence", context["consequence"])
            set_text(item, "whyConfidence", context["confidence"])
        updated += 1
    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    print(f"Why It Matters: {updated} item(s) regenerated from story-specific context.")


if __name__ == "__main__":
    main()
