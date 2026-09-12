#!/usr/bin/env python3
"""Generate Why It Matters from the final paraphrased content brief.

Entertainment, Technology, and Gaming use event-specific consequence rules.
Other sections keep the broader editorial rules that were already in production.
"""
from pathlib import Path
import html
import re
import xml.etree.ElementTree as ET

NEWS = Path("News")


def clean(v):
    v = html.unescape(v or "")
    v = re.sub(r"<[^>]+>", " ", v)
    return re.sub(r"\s+", " ", v).strip()


def has(text, *terms):
    return any(re.search(r"\b" + re.escape(t) + r"\b", text, re.I) for t in terms)


def count_terms(text, *terms):
    return sum(bool(re.search(r"\b" + re.escape(t) + r"\b", text, re.I)) for t in terms)


def _tech_why(text):
    if has(text, "data breach", "breach", "ransomware", "cyberattack", "hacked", "hack"):
        return ("The incident can expose users or organizations to account, privacy, and operational risk; "
                "the concrete impact depends on what data or systems were affected and how quickly they are secured.")
    if has(text, "outage", "service disruption", "offline", "downtime"):
        return ("The disruption directly affects access to the service or infrastructure; restoration time, "
                "customer impact, and whether the failure repeats determine its wider significance.")
    if has(text, "vulnerability", "security flaw", "zero-day", "zero day", "exploit", "patch"):
        return ("The security issue matters to people and organizations using the affected product because "
                "unpatched systems may remain exposed until a fix is deployed.")
    if has(text, "antitrust", "lawsuit", "sued", "court", "ruling", "regulator", "regulation", "ban"):
        return ("The legal or regulatory action could change how the company operates, distributes the product, "
                "or competes, and may influence similar technology businesses.")
    if has(text, "layoffs", "layoff", "job cuts", "cuts jobs", "workforce reduction"):
        return ("The workforce reduction affects employees immediately and can signal changes to the company's "
                "product roadmap, support capacity, or spending priorities.")
    if has(text, "acquisition", "acquire", "acquires", "acquired", "merger", "merges"):
        return ("The ownership change can alter product priorities, jobs, pricing, and competition, especially "
                "where the companies serve overlapping users or markets.")
    if has(text, "price increase", "raises prices", "price hike", "subscription price", "pricing"):
        return ("The change directly affects what customers pay and can influence adoption, cancellations, "
                "and how competing services or products are priced.")
    if has(text, "ai model", "artificial intelligence model", "llm", "large language model"):
        if has(text, "launch", "release", "released", "unveil", "unveiled", "debut", "announced", "new model"):
            return ("The model changes the capabilities or economics available to developers and businesses using AI, "
                    "and gives competitors a new performance and cost benchmark.")
        return ("The development is relevant to organizations building or using AI because it may change capability, "
                "cost, access, or the competitive position of major model providers.")
    if has(text, "gpu", "cpu", "processor", "chip", "semiconductor"):
        if has(text, "launch", "release", "released", "unveil", "unveiled", "debut", "announced", "new"):
            return ("The hardware sets a new performance, efficiency, or pricing reference point for buyers and "
                    "can influence competing chips and the devices built around them.")
        return ("The chip development can affect hardware performance, supply, pricing, and the product roadmaps "
                "of device makers that depend on the component.")
    if has(text, "iphone", "ipad", "smartphone", "laptop", "macbook", "device", "headset", "smart glasses", "wearable"):
        if has(text, "launch", "release", "released", "unveil", "unveiled", "debut", "announced", "new"):
            return ("The product affects buyers deciding when and what to upgrade, while its features and pricing "
                    "give competing device makers a new target.")
    if has(text, "partnership", "partners with", "integration", "integrates", "deal"):
        return ("The agreement can expand distribution or combine products and services, changing what users can access "
                "and how the companies compete within the same ecosystem.")
    if has(text, "privacy", "tracking", "user data", "data collection"):
        return ("The change affects how user information is collected or handled, with consequences for privacy, "
                "trust, and compliance obligations.")
    if has(text, "software", "platform", "operating system", "app", "browser"):
        if has(text, "launch", "release", "released", "update", "announced", "new"):
            return ("The software change can alter how existing users work with the platform and may affect developers "
                    "or businesses that depend on its compatibility and rules.")
    return ("The available brief identifies a technology development but does not establish a concrete downstream "
            "effect yet; the significance depends on what changes for users, developers, competitors, or costs.")


def _gaming_why(text):
    if has(text, "delay", "delayed", "pushed back", "postponed"):
        return ("The delay changes the publisher's release calendar and revenue timing, while giving competing games "
                "a less crowded launch window.")
    if has(text, "studio closure", "studio closes", "studio closed", "shuts down", "shutdown", "cancelled", "canceled"):
        return ("The decision can end active projects or live support and affects the developers, players, and release "
                "plans tied to the studio or game.")
    if has(text, "layoffs", "layoff", "job cuts", "cuts jobs", "workforce reduction"):
        return ("The job cuts affect development teams immediately and can reduce the scope, pace, or support of current "
                "and future games.")
    if has(text, "acquisition", "acquire", "acquires", "acquired", "merger", "buys studio", "bought studio"):
        return ("The ownership change can affect creative control, platform availability, staffing, and which projects "
                "receive funding.")
    if has(text, "console", "handheld", "playstation", "xbox", "nintendo switch", "switch 2"):
        if has(text, "launch", "release", "released", "unveil", "unveiled", "announced", "new hardware", "new console"):
            return ("The hardware helps set the direction of the next platform cycle, affecting what players buy and "
                    "which systems developers target for future games.")
    if has(text, "game pass", "playstation plus", "ps plus", "subscription", "price increase", "price hike"):
        return ("The change directly affects player cost and the value of the service, which can influence subscriptions, "
                "game discovery, and platform loyalty.")
    if has(text, "patch", "update", "season", "dlc", "expansion"):
        return ("The update affects the current player experience and can influence retention, balance, and how long the "
                "game remains commercially active.")
    if has(text, "lawsuit", "sued", "court", "regulation", "ban"):
        return ("The dispute or rule can affect how the game, platform, or publisher operates and may shape similar "
                "business practices elsewhere in the industry.")
    if has(text, "sales", "sold", "record", "copies", "players", "concurrent players"):
        return ("The performance is a measurable signal of audience demand and can influence sequel, investment, "
                "platform, and publishing decisions.")
    if has(text, "release date", "launch", "released", "debut"):
        return ("The release establishes the game's commercial window and puts its sales, player adoption, and competition "
                "with nearby launches into focus.")
    return ("The available brief identifies a gaming development but does not establish a concrete downstream effect yet; "
            "the significance depends on what changes for players, developers, release plans, or costs.")


def _entertainment_why(text):
    if has(text, "died", "dies", "death", "dead", "hospitalized", "hospitalised", "cancer", "serious illness"):
        return ("The development has immediate personal significance and can also affect scheduled productions, touring, "
                "or other professional commitments connected to the person involved.")
    if has(text, "lawsuit", "sued", "court", "charged", "arrested", "indicted", "investigation"):
        return ("The legal issue can affect the person's career, contracts, finances, and active productions, with the "
                "larger impact depending on how the case develops.")
    if has(text, "cast", "casting", "joins cast", "starring", "role"):
        return ("The casting helps define the production and can materially raise or redirect the performer's career "
                "while shaping audience expectations for the project.")
    if has(text, "renewed", "renewal", "canceled", "cancelled", "greenlit", "greenlight"):
        return ("The decision affects whether the production continues, which directly matters to its cast, crew, "
                "audience, and the distributor's programming strategy.")
    if has(text, "box office", "opening weekend", "ticket sales"):
        return ("The result is a concrete measure of audience demand and can influence marketing, sequel plans, "
                "theatrical strategy, and future investment.")
    if has(text, "oscar", "oscars", "emmy", "emmys", "grammy", "grammys", "golden globe", "award", "nomination", "nominated", "wins", "winner"):
        return ("The recognition can raise the winner's or nominee's industry profile and affect future roles, "
                "negotiating leverage, financing, and awards-season momentum.")
    if has(text, "album", "single", "tour", "concert"):
        if has(text, "announced", "announce", "release", "released", "launch", "tour"):
            return ("The announcement starts or advances a commercial cycle for the artist, affecting streaming, "
                    "ticketing, promotion, and competition for audience attention.")
    if has(text, "movie", "film", "series", "show", "trailer", "premiere", "release date"):
        if has(text, "trailer", "premiere", "release", "released", "release date", "debut"):
            return ("The release milestone moves the project into its audience and revenue phase, where demand can shape "
                    "marketing, distribution, and prospects for follow-up projects.")
    if has(text, "deal", "contract", "signs", "acquisition", "rights", "distribution"):
        return ("The business agreement can change who controls, finances, distributes, or profits from the work and can "
                "alter the people or companies' future project options.")
    if has(text, "pregnant", "pregnancy", "baby", "gave birth", "gives birth", "welcomes son", "welcomes daughter",
           "engaged", "engagement", "married", "wedding", "dating", "boyfriend", "girlfriend", "breakup", "split"):
        return ("This is primarily a personal celebrity update that matters to the people involved and their audience; "
                "the available brief does not indicate a broader entertainment-industry impact.")
    if has(text, "charity", "philanthropy", "donation", "fundraiser", "fundraising", "benefit gala"):
        return ("The direct significance is the money, attention, or participation directed toward the stated cause; "
                "its broader entertainment-industry impact is secondary.")
    if has(text, "bikini", "swimsuit", "sheer", "see-through", "topless", "nude", "red carpet", "fashion"):
        return ("This is primarily a celebrity or lifestyle update with limited wider industry impact unless it becomes "
                "part of a larger campaign, contract, or production.")
    return ("The available brief describes an entertainment update but does not establish a clear wider industry consequence; "
            "its significance is mainly to the people, project, or audience directly involved.")


def why_for(item):
    brief = clean(item.findtext("description"))
    title = clean(item.findtext("title"))
    cat = clean(item.findtext("category")).lower()
    text = f"{title} {brief}".lower()

    if cat == "technology":
        impact = _tech_why(text)
    elif cat == "gaming":
        impact = _gaming_why(text)
    elif cat.startswith("entertainment"):
        impact = _entertainment_why(text)
    else:
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


def main():
    tree = ET.parse(NEWS)
    items = tree.getroot().findall(".//item")
    updated = 0
    for item in items:
        if clean(item.findtext("category")).lower() == "legislation":
            continue
        if not clean(item.findtext("description")):
            continue
        node = item.find("whyMatters")
        if node is None:
            node = ET.SubElement(item, "whyMatters")
        node.text = why_for(item)
        updated += 1
    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    print(f"Why It Matters: {updated} item(s) regenerated from final paraphrased briefs.")


if __name__ == "__main__":
    main()
