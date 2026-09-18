from __future__ import annotations
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from model import Story
from pipeline import normalize_url, near_duplicate, process
from diversity import same_event
from registry import load_registry
from movie_artwork import _is_schedule_label, _title_variants, _normalize_poster_url

class V6PipelineTests(unittest.TestCase):
    def setUp(self): self.registry=load_registry()
    def test_registry_is_explicit_and_unique(self):
        ids=[row["id"] for row in self.registry["sources"]];self.assertEqual(len(ids),len(set(ids)));self.assertIn("world",self.registry["categories"]);self.assertIn("boxoffice",self.registry["categories"])
    def test_tracking_parameters_are_removed(self): self.assertEqual(normalize_url("https://example.com/a?utm_source=x&keep=1#frag"),"https://example.com/a?keep=1")
    def test_semantic_duplicate_detection(self):
        a=Story("a","world","Major storm closes schools across northern New Mexico","https://a.example/x","A","2026-09-15T12:00:00Z");b=Story("b","world","Major storm closes schools across northern New Mexico today","https://b.example/y","B","2026-09-15T12:01:00Z");self.assertTrue(near_duplicate(a,b))
    def test_broader_same_event_detection(self):
        a=Story("a","world","Northern Arizona wildfire evacuation expands across mountain communities","https://a.example/x","A","2026-09-15T12:00:00Z")
        b=Story("b","world","Wildfire evacuation across northern Arizona mountain communities grows overnight","https://b.example/y","B","2026-09-15T12:05:00Z")
        self.assertTrue(same_event(a,b))
    def test_process_dedupes_and_scores(self):
        rows=[Story("a","world","Cyberattack causes emergency outage across city","https://a.example/x?utm_source=test","A","2026-09-15T12:00:00Z","Officials reported an outage."),Story("b","world","Cyberattack causes emergency outage across city","https://a.example/x","B","2026-09-15T12:01:00Z","Duplicate.")];out=process(rows,self.registry,now=datetime(2026,9,15,13,tzinfo=timezone.utc));self.assertEqual(len(out),1);self.assertGreater(out[0].importance,0);self.assertTrue(any(term in out[0].why_matters.lower() for term in ("outage","emergency","attack")))
    def test_topic_saturation_defers_instead_of_discarding_valid_stories(self):
        rows=[
            Story("a1","technology","Anthropic launches Claude security controls for enterprise administrators","https://a.example/1","Outlet A","2026-09-15T12:00:00Z","Anthropic announced enterprise security controls for Claude administrators and business customers."),
            Story("a2","technology","Anthropic expands Claude tools for software development teams","https://b.example/2","Outlet B","2026-09-15T11:50:00Z","Anthropic expanded Claude development tools for software teams using its artificial intelligence platform."),
            Story("a3","technology","Anthropic signs new cloud agreement for Claude infrastructure","https://c.example/3","Outlet C","2026-09-15T11:40:00Z","Anthropic signed a cloud infrastructure agreement supporting Claude artificial intelligence services."),
            Story("g","technology","Google releases Android privacy protections for mobile users","https://d.example/4","Outlet D","2026-09-15T11:30:00Z","Google released Android privacy protections affecting mobile users and application permissions."),
        ]
        out=process(rows,self.registry,now=datetime(2026,9,15,13,tzinfo=timezone.utc));titles=[x.title.lower() for x in out]
        self.assertEqual(len(out),4);self.assertEqual(sum("anthropic" in title for title in titles),3)
        self.assertLess(titles.index(next(t for t in titles if "google" in t)),max(i for i,t in enumerate(titles) if "anthropic" in t))
    def test_underreported_builds_evidence_package_from_collected_pool(self):
        rows=[
            Story("u","underreported","EPA moves to repeal power plant emissions limits","https://primary.example/u","Primary","2026-09-15T12:00:00Z","EPA plans to repeal power plant emissions limits and is expected to announce the final action later this month."),
            Story("a","us","EPA moves to repeal emissions limits for power plants","https://a.example/x","Outlet A","2026-09-14T12:00:00Z","Related report."),
            Story("b","federal","EPA repeal of power plant emissions limits advances","https://b.example/x","Outlet B","2026-09-13T12:00:00Z","Related report."),
        ]
        out=process(rows,self.registry,now=datetime(2026,9,15,13,tzinfo=timezone.utc));story=next(x for x in out if x.id=="u")
        self.assertEqual(story.supporting_source_count,2);self.assertEqual(story.coverage_gap_score,86);self.assertGreater(story.underreported_priority,0);self.assertEqual(story.coverage_score,story.underreported_priority);self.assertEqual(len(story.related),2);self.assertTrue(story.what_happened);self.assertTrue(story.what_is_missing);self.assertTrue(story.background);self.assertTrue(story.what_next)
    def test_underreported_priority_balances_gap_with_corroboration(self):
        zero=Story("z","underreported","Investigation documents river contamination near rural towns","https://example.com/z","Primary","2026-09-15T12:00:00Z","An investigation documented river contamination affecting rural towns while environmental regulators review the findings.")
        supported=Story("s","underreported","Investigation finds hospital safety failures","https://example.com/s","Primary2","2026-09-15T12:00:00Z","An investigation found hospital safety failures affecting patients and regulators are reviewing the findings.",related=[
            {"title":"Hospital safety failures draw state review","url":"https://a.example/1","source":"Reuters","published_at":"2026-09-15T11:00:00Z"},
            {"title":"State reviews hospital safety failures","url":"https://b.example/2","source":"Associated Press","published_at":"2026-09-15T10:00:00Z"},
        ])
        out=process([zero,supported],self.registry,now=datetime(2026,9,15,13,tzinfo=timezone.utc));by={x.id:x for x in out}
        self.assertEqual(by["z"].coverage_gap_score,96);self.assertEqual(by["z"].supporting_source_count,0);self.assertEqual(by["s"].supporting_source_count,2);self.assertGreater(by["s"].corroboration_score,by["z"].corroboration_score);self.assertGreater(by["s"].underreported_priority,by["z"].underreported_priority)
    def test_underreported_rejects_generic_topic_page_title(self):
        row=Story("weak","underreported","Domestic Violence","https://themarshallproject.org/domestic-violence","The Marshall Project","2026-09-14T08:00:00Z","Domestic Violence themarshallproject.org")
        self.assertEqual(process([row],self.registry,now=datetime(2026,9,15,13,tzinfo=timezone.utc)),[])
    def test_underreported_keeps_short_title_when_summary_is_substantive(self):
        row=Story("short","underreported","Water Crisis","https://example.com/water","Investigative Outlet","2026-09-15T12:00:00Z","Residents in three rural communities lost access to safe drinking water after testing found contamination above federal limits, prompting emergency deliveries and a state investigation.")
        out=process([row],self.registry,now=datetime(2026,9,15,13,tzinfo=timezone.utc));self.assertEqual([x.id for x in out],["short"])
    def test_presidential_rejects_foreign_and_former_office_personal_stories(self):
        rows=[Story("fr","presidential","French candidates gain ground in 2027 presidential race","https://example.com/fr","Reuters","2026-09-15T12:00:00Z","Polling in France shows movement in the presidential field."),Story("former","presidential","Deputies respond to trespasser at ex-Vice President's home","https://example.com/former","AP","2026-09-15T12:00:00Z","Deputies responded to a residential trespassing report.")]
        self.assertEqual(process(rows,self.registry,now=datetime(2026,9,15,13,tzinfo=timezone.utc)),[])
    def test_presidential_keeps_current_us_presidency_story(self):
        row=Story("us","presidential","Trump administration announces new trade policy after White House meeting","https://example.com/us","Reuters","2026-09-15T12:00:00Z","Officials said the policy will affect imports and negotiations with major trading partners.")
        out=process([row],self.registry,now=datetime(2026,9,15,13,tzinfo=timezone.utc));self.assertEqual([x.id for x in out],["us"])
    def test_presidential_rejects_stale_headline_only_item(self):
        row=Story("old","presidential","Bannon out at the White House","https://example.com/old","Reuters","2026-08-14T12:55:00Z","Bannon out at the White House Reuters")
        self.assertEqual(process([row],self.registry,now=datetime(2026,9,15,13,tzinfo=timezone.utc)),[])
    def test_legislation_rejects_generic_white_house_release(self):
        row=Story("wh","legislation","First Lady Melania Trump’s Special Visit to Ashe County, North Carolina","https://example.com/wh","The White House","2026-09-15T12:00:00Z","Bearing witness to a community’s resilience.")
        self.assertEqual(process([row],self.registry,now=datetime(2026,9,15,13,tzinfo=timezone.utc)),[])
    def test_legislation_rejects_generic_law_and_rule_mentions(self):
        rows=[Story("law","legislation","Attorney General discusses law enforcement priorities","https://example.com/law","The White House","2026-09-15T12:00:00Z","Officials discussed crime and law enforcement."),Story("rule","legislation","Court ruling changes campaign landscape","https://example.com/rule","News","2026-09-15T12:00:00Z","The ruling drew reactions from both parties.")]
        self.assertEqual(process(rows,self.registry,now=datetime(2026,9,15,13,tzinfo=timezone.utc)),[])
    def test_legislation_keeps_actual_rule_and_bill(self):
        rows=[Story("fr","legislation","Public Inspection: Proposed Rule Changes for Investors Exchange LLC","https://example.com/fr","Federal Register","2026-09-15T12:00:00Z","Proposed rule changes under federal securities regulation."),Story("bill","legislation","Text - S.4013 - National Constitutional Carry Act","https://example.com/bill","Congress.gov","2026-09-15T12:00:00Z","Senate bill text and status.")]
        out=process(rows,self.registry,now=datetime(2026,9,15,13,tzinfo=timezone.utc));self.assertEqual({x.id for x in out},{"fr","bill"})
    def test_boxoffice_schedule_labels_are_not_movies(self):
        for title in ("3rd quarter","October 2026","Summer 2026","Time","Release Date"):
            self.assertTrue(_is_schedule_label(title),title)
        self.assertFalse(_is_schedule_label("The Odyssey"))
    def test_boxoffice_title_variants_help_special_events_match(self):
        variants=_title_variants("SB19 Wakas at Simula: The Trilogy Concert Finale In Cinemas")
        self.assertIn("SB19 Wakas at Simula",variants)
        self.assertIn("SB19 Wakas at Simula: The Trilogy Concert Finale",variants)
        self.assertIn("Adore Him",_title_variants("Adore Him: He is Here"))
    def test_tmdb_media_url_is_normalized_to_image_host(self):
        url=_normalize_poster_url("https://media.themoviedb.org/t/p/w600_and_h900_bestv2/abc123.jpg")
        self.assertEqual(url,"https://image.tmdb.org/t/p/w500/abc123.jpg")

if __name__=="__main__": unittest.main()
