from __future__ import annotations
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from model import Story
from pipeline import normalize_url, near_duplicate, process
from registry import load_registry

class V6PipelineTests(unittest.TestCase):
    def setUp(self): self.registry=load_registry()
    def test_registry_is_explicit_and_unique(self):
        ids=[row["id"] for row in self.registry["sources"]];self.assertEqual(len(ids),len(set(ids)));self.assertIn("world",self.registry["categories"]);self.assertIn("boxoffice",self.registry["categories"])
    def test_tracking_parameters_are_removed(self): self.assertEqual(normalize_url("https://example.com/a?utm_source=x&keep=1#frag"),"https://example.com/a?keep=1")
    def test_semantic_duplicate_detection(self):
        a=Story("a","world","Major storm closes schools across northern New Mexico","https://a.example/x","A","2026-09-15T12:00:00Z");b=Story("b","world","Major storm closes schools across northern New Mexico today","https://b.example/y","B","2026-09-15T12:01:00Z");self.assertTrue(near_duplicate(a,b))
    def test_process_dedupes_and_scores(self):
        rows=[Story("a","world","Cyberattack causes emergency outage across city","https://a.example/x?utm_source=test","A","2026-09-15T12:00:00Z","Officials reported an outage."),Story("b","world","Cyberattack causes emergency outage across city","https://a.example/x","B","2026-09-15T12:01:00Z","Duplicate.")];out=process(rows,self.registry,now=datetime(2026,9,15,13,tzinfo=timezone.utc));self.assertEqual(len(out),1);self.assertGreater(out[0].importance,0);self.assertTrue(any(term in out[0].why_matters.lower() for term in ("outage","emergency","attack")))
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

if __name__=="__main__": unittest.main()
