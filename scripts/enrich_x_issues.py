from pathlib import Path
from datetime import datetime, timezone
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

NEWS = Path("News")
MAX_ISSUES = 18

QUERIES = {
    "Politics & Government": "site:x.com Trump OR White House OR Congress OR Supreme Court",
    "World": "site:x.com world conflict OR war OR international",
    "Health": "site:x.com health OR medical OR disease OR FDA",
    "Entertainment": "site:x.com entertainment OR movie OR music OR television",
    "Celebrities & Public Figures": "site:x.com celebrity OR actor OR singer OR athlete",
    "Technology & AI": "site:x.com AI OR technology OR OpenAI OR Google OR Apple",
    "Gaming": "site:x.com gaming OR PlayStation OR Xbox OR Nintendo OR PC gaming",
    "Sports": "site:x.com sports OR NFL OR NBA OR MLB OR soccer",
    "Business & Economy": "site:x.com economy OR stocks OR tariffs OR jobs OR business",
    "Breaking / Emerging": "site:x.com breaking news OR developing OR viral",
    "Science": "site:x.com science OR space OR NASA OR climate",
    "Internet Culture": "site:x.com internet culture OR meme OR social media",
}

STOP = {"the","a","an","to","of","in","on","for","and","with","is","as","at","from","by","after","new","says","said","that","this","are","was","were","has","have","had","into","over","its","their","will","news","latest","x","twitter"}

def clean(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def words(text):
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) >= 4 and w not in STOP}

def fetch(query):
    q = urllib.parse.quote(f"{query} when:2d")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 Underreported-X/1.1"})
    with urllib.request.urlopen(req, timeout=15) as response:
        return ET.fromstring(response.read())

def date(value):
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except Exception:
        return None

def is_x_activity(link, source, title, desc):
    # Prefer an actual X/Twitter destination. If a news index describes an X
    # discussion without exposing the post URL, only accept explicit wording.
    link_text = (link or "").lower()
    text = f"{title} {desc}".lower()
    if "x.com/" in link_text or "twitter.com/" in link_text:
        return True
    return bool(re.search(r"\b(?:on|posted on|posts? on|from)\s+(?:x|twitter)\b", text))

def main():
    if not NEWS.exists():
        raise SystemExit("News feed not found")
    tree = ET.parse(NEWS)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise SystemExit("RSS channel not found")

    existing = [x for x in channel.findall("item") if clean(x.findtext("category")) == "x"]
    for item in existing:
        channel.remove(item)

    candidates = []
    for topic, query in QUERIES.items():
        try:
            rss = fetch(query)
        except Exception:
            continue
        for item in rss.findall(".//item"):
            title = clean(item.findtext("title")); link = clean(item.findtext("link"))
            desc = clean(item.findtext("description")); pub = clean(item.findtext("pubDate"))
            source_el = item.find("source")
            source = clean(source_el.text if source_el is not None else "")
            dt = date(pub)
            if not title or not link or not dt or not is_x_activity(link, source, title, desc):
                continue
            candidates.append({"topic":topic,"title":title,"link":link,"desc":desc,"pub":pub,"source":source,"dt":dt})

    # Cluster similar issues. We only call this a signal based on the number of
    # independently indexed results; we never invent total X post volume.
    clusters = []
    for item in sorted(candidates, key=lambda x:x["dt"], reverse=True):
        w = words(item["title"])
        best = None; best_overlap = 0
        for cluster in clusters:
            overlap = len(w & cluster["words"])
            if overlap >= 2 and overlap > best_overlap:
                best, best_overlap = cluster, overlap
        if best:
            best["items"].append(item); best["words"].update(w); best["topics"].add(item["topic"])
        else:
            clusters.append({"words":set(w),"items":[item],"topics":{item["topic"]}})

    clusters.sort(key=lambda c:(len(c["items"]), max(x["dt"] for x in c["items"])), reverse=True)
    for cluster in clusters[:MAX_ISSUES]:
        lead = max(cluster["items"], key=lambda x:x["dt"])
        issue = ET.Element("item")
        ET.SubElement(issue,"title").text = lead["title"]
        ET.SubElement(issue,"link").text = lead["link"]
        ET.SubElement(issue,"description").text = lead["desc"] or "Publicly indexed X activity is drawing attention around this issue."
        ET.SubElement(issue,"pubDate").text = lead["pub"]
        ET.SubElement(issue,"source").text = lead["source"] or "X / indexed public discussion"
        ET.SubElement(issue,"category").text = "x"
        ET.SubElement(issue,"xTopic").text = sorted(cluster["topics"])[0]
        count = len(cluster["items"])
        signal = "Strong indexed signal" if count >= 4 else ("Growing indexed signal" if count >= 2 else "Emerging signal")
        ET.SubElement(issue,"xSignal").text = signal
        ET.SubElement(issue,"xEvidence").text = f"This issue was identified from {count} distinct indexed result(s) in the last 48 hours. That is a conversation signal, not a verified measure of total X post volume."
        ET.SubElement(issue,"xVerification").text = "Unverified discussion: posts and claims circulating on X are not automatically factual. Use the linked reporting or primary sources to verify important claims."
        rel = ET.SubElement(issue,"xRelated")
        seen_links = set()
        for related in cluster["items"][:4]:
            if related["link"] in seen_links: continue
            seen_links.add(related["link"])
            r = ET.SubElement(rel,"article")
            ET.SubElement(r,"title").text = related["title"]
            ET.SubElement(r,"link").text = related["link"]
            ET.SubElement(r,"source").text = related["source"]
            ET.SubElement(r,"pubDate").text = related["pub"]
        channel.append(issue)

    tree.write(NEWS, encoding="utf-8", xml_declaration=True)
    print(f"X issue enrichment complete: {min(len(clusters), MAX_ISSUES)} conservative conversation signals.")

if __name__ == "__main__":
    main()
