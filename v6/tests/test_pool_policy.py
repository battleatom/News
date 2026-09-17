from __future__ import annotations
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from model import Story
from pool_policy import apply_rolling_pool

class PoolPolicyTests(unittest.TestCase):
    def story(self,i,age,importance=5,category="top"):
        now=datetime(2026,9,17,14,tzinfo=timezone.utc)
        return Story(str(i),category,f"Story {i}",f"https://example.com/{i}","Source",(now-timedelta(hours=age)).isoformat().replace("+00:00","Z"),importance=importance)

    def test_stale_low_importance_falls_out(self):
        now=datetime(2026,9,17,14,tzinfo=timezone.utc)
        registry={"categories":{"top":{"visible_target":10,"reserve_ratio":.2,"expansion_ratio":.3}}}
        kept,meta=apply_rolling_pool([self.story(1,80),self.story(2,80,30)],registry,now=now)
        self.assertEqual([s.id for s in kept],["2"])
        self.assertEqual(meta["retiredStaleCount"],1)

    def test_fresh_surge_unlocks_expansion(self):
        now=datetime(2026,9,17,14,tzinfo=timezone.utc)
        registry={"categories":{"top":{"visible_target":10,"reserve_ratio":.2,"expansion_ratio":.3}}}
        rows=[self.story(i,1) for i in range(20)]
        kept,meta=apply_rolling_pool(rows,registry,now=now)
        self.assertEqual(len(kept),15)
        self.assertEqual(meta["categories"]["top"]["expansionUsed"],3)

    def test_quiet_pool_contracts_naturally(self):
        now=datetime(2026,9,17,14,tzinfo=timezone.utc)
        registry={"categories":{"top":{"visible_target":10,"reserve_ratio":.2,"expansion_ratio":.3}}}
        rows=[self.story(i,20) for i in range(8)]
        kept,meta=apply_rolling_pool(rows,registry,now=now)
        self.assertEqual(len(kept),8)
        self.assertEqual(meta["categories"]["top"]["expansionUsed"],0)

if __name__=="__main__":unittest.main()
