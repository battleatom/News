# V5.1 vs V5.2 Content Audit

Automated semantic + sequence audit. Mismatch candidates are review flags, not automatic deletions.

| Tab | V5.1 count | V5.2 count | V5.1 mismatches | V5.2 mismatches | V5.1 max source streak | V5.2 max source streak | V5.2 top source |
|---|---:|---:|---:|---:|---|---|---|
| top | 53 | 44 | 0 | 0 | 2× Fox News | 1× Reuters | The New York Times 3 (6.8%) |
| x | 10 | 10 | 0 | 0 | 1× KFF Health News | 1× KFF Health News | KFF Health News 1 (10.0%) |
| underreported | 75 | 74 | 0 | 0 | 4× ProPublica | 4× ProPublica | Inside Climate News 14 (18.9%) |
| entertainment | 80 | 75 | 20 | 18 | 2× The Hollywood Reporter | 1× Variety | Variety 6 (8.0%) |
| world | 90 | 67 | 55 | 32 | 9× Reuters | 28× Reuters | Reuters 32 (47.8%) |
| us | 20 | 24 | 14 | 14 | 4× Reuters | 4× Reuters | Reuters 7 (29.2%) |
| presidential | 54 | 61 | 34 | 39 | 14× Reuters | 6× Reuters | Reuters 27 (44.3%) |
| federal | 25 | 34 | 2 | 3 | 5× Reuters | 4× Reuters | Reuters 7 (20.6%) |
| legislation | 24 | 21 | 0 | 0 | 13× New Mexico Legislature | 6× New Mexico Legislature | New Mexico Legislature 13 (61.9%) |
| nm | 52 | 57 | 1 | 0 | 6× KRQE | 16× KRQE | KRQE 24 (42.1%) |
| local | 369 | 336 | 19 | 11 | 4× the-journal.com | 20× CBS News | CBS News 28 (8.3%) |
| region | 73 | 70 | 3 | 2 | 6× East Idaho News | 1× ABC News - Breaking News, Latest News and Videos | ABC News - Breaking News, Latest News and Videos 6 (8.6%) |
| nfl | 23 | 25 | 0 | 0 | 22× ESPN | 22× ESPN | ESPN 23 (92.0%) |
| technology | 68 | 80 | 25 | 38 | 3× Politico | 1× Reuters | Reuters 10 (12.5%) |
| gaming | 63 | 59 | 4 | 3 | 4× Tom's Hardware | 1× Reuters | IGN 10 (16.9%) |
| military | 50 | 46 | 0 | 0 | 17× Defense News | 9× Defense News | Defense News 13 (28.3%) |

Exact cross-tab repeat groups: V5.1=0, V5.2=0

## top
V5.1: 53 items, 11 sources, streak 2× Fox News; V5.2: 44 items, 18 sources, streak 1× Reuters.
V5.2 top sources: The New York Times (3), Fox News (3), CBS News (3), CNN (3), CNBC (3), Associated Press (3)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=0.

## x
V5.1: 10 items, 9 sources, streak 1× KFF Health News; V5.2: 10 items, 10 sources, streak 1× KFF Health News.
V5.2 top sources: KFF Health News (1), Yahoo Finance (1), Yahoo News (1), The Guardian (1), Wired (1), Entertainment Weekly (1)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=0.

## underreported
V5.1: 75 items, 22 sources, streak 4× ProPublica; V5.2: 74 items, 21 sources, streak 4× ProPublica.
V5.2 top sources: Inside Climate News (14), KFF Health News (11), ProPublica (9), Grist (7), The Marshall Project (7), Source New Mexico (4)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=0.

## entertainment
V5.1: 80 items, 28 sources, streak 2× The Hollywood Reporter; V5.2: 75 items, 29 sources, streak 1× Variety.
V5.2 top sources: Variety (6), The Hollywood Reporter (6), People (6), Yahoo News (6), Billboard (6), USA Today (5)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=18.
Mismatch candidates:
- #3 — USA Today — See the best photos from New York Fashion Week 2026 - USA Today — weak/no entertainment anchor
- #6 — People — Gillian Anderson Reveals She Identifies as Pansexual, Reflects on Relationships with Women: ‘I Didn’t Have the Language’ - People.com — weak/no entertainment anchor
- #7 — Deadline — Gary Myers Dies: NASCAR Driver, Patriarch Of Racing Family Was 76 - Deadline — weak/no entertainment anchor
- #10 — TMZ — Hayden Panettiere Died From Fentanyl-Laced Oxy, Sources - TMZ — weak/no entertainment anchor
- #34 — BBC — Strictly Come Dancing 2026 contestants reveal why they're heading for the ballroom, their dream songs to dance to and what they're most nervous about - BBC — weak/no entertainment anchor
- #36 — Deadline — Pierce Brosnan Says Tom Hardy ‘MobLand’ Feud Was “Storm In A Teacup” - Deadline — weak/no entertainment anchor
- #38 — Yahoo News — Pretty Ricky’s Spectacular Smith Sued By Arizona Woman Alleging Sexual Assault - Yahoo — weak/no entertainment anchor
- #47 — People — Influencer Madalina Apostol Dies a Month After Celebrating 40th Birthday - People.com — weak/no entertainment anchor
- #52 — E! News — Why Jay-Z Thinks Beyoncé, Their 3 Kids Watching His Docuseries Could Be “Cringe" - E! News — weak/no entertainment anchor
- #53 — Variety — Why ‘How Long Gone’ Created Their Own Awards Show — and ‘Squashed the Beef’ With Bowen Yang - Variety — weak/no entertainment anchor
- #55 — USA Today — Zendaya and Tom Holland's wedding gets bombshell update from Law Roach - USA Today — weak/no entertainment anchor
- #56 — BBC — Closed wedding venue seeks new suitor for £18m - BBC — weak/no entertainment anchor

## world
V5.1: 90 items, 32 sources, streak 9× Reuters; V5.2: 67 items, 27 sources, streak 28× Reuters.
V5.2 top sources: Reuters (32), The Guardian (4), Defense News (3), NBC News (2), Al Jazeera (2), CNBC (2)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=32.
Mismatch candidates:
- #7 — Ars Technica — Rocket Report: Europe joins the commercial launch club; a Ravn X sighting? — fails World semantic gate
- #9 — Federal Register (.gov) — Iranian Transactions and Sanctions Regulations — fails World semantic gate
- #10 — Defense News — US, South Korean officials to broach thorny Hormuz mission at talks this week - defensenews.com — fails World semantic gate
- #12 — The Guardian — The end times fascists are plotting their escape from our world. Our mission is clear | Naomi Klein and Astra Taylor — fails World semantic gate
- #13 — TechCrunch — ClickFix attacks are tricking Mac and Windows users into hacking themselves - TechCrunch — fails World semantic gate
- #14 — tech-insider.org — Conti Ransomware Hacker Sentenced to 4 Years [2026] - tech-insider.org — fails World semantic gate; technology/product-looking headline outside Technology
- #15 — Industrial Cyber — Global ransomware attacks hit record 997 in August 2026 as utility, healthcare and business attacks surge - Industrial Cyber — fails World semantic gate; technology/product-looking headline outside Technology
- #16 — Tech Times — Cisco Firewall Manager Hacked by Sandworm Espionage Implant and Qilin Ransomware - Tech Times — fails World semantic gate; technology/product-looking headline outside Technology
- #17 — Chief Healthcare Executive — What ‘The Pitt’ got right on a hospital ransomware attack - Chief Healthcare Executive — fails World semantic gate
- #18 — Africa Business Communities — Kenya cyber attacks up 6pc as ransomware nearly doubles globally - Africa Business Communities — fails World semantic gate; technology/product-looking headline outside Technology
- #19 — teiss — News - Ransomware group claims breach at Dunedin clinical research firm ZenTech - teiss — fails World semantic gate
- #20 — Tech Observer Magazine — HBO Max Reddit account hijacked to spread malware via ClickFix ads - Tech Observer Magazine — fails World semantic gate; technology/product-looking headline outside Technology

## us
V5.1: 20 items, 12 sources, streak 4× Reuters; V5.2: 24 items, 14 sources, streak 4× Reuters.
V5.2 top sources: Reuters (7), Associated Press (3), NBC News (2), CNBC (2), IGN (1), nytimes.com (1)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=14.
Mismatch candidates:
- #2 — Reuters — US NTSB says one-third of FAA answers to safety recommendations are 'unacceptable' - Reuters — fails US semantic gate
- #4 — nytimes.com — Visa Issue Threatens U.S.-Brazil Cooperation on Crime - nytimes.com — fails US semantic gate
- #5 — Time Magazine — U.S. Diesel Prices Just Surpassed a Record $6 Per Gallon. Here Are Three Ways That Affects You - Time Magazine — fails US semantic gate
- #7 — ABC News - Breaking News, Latest News and Videos — How every US state approaches 9/11 history in schools - ABC News - Breaking News, Latest News and Videos — fails US semantic gate
- #8 — AP News — George Clooney on the current state of US politics - AP News — fails US semantic gate
- #10 — France 24 — Reporters - US state of Louisiana in battle over electoral map - France 24 — fails US semantic gate
- #15 — Reuters — US rail fuel surcharges on grain hit record highs, squeezing farmers in harvest season - Reuters — fails US semantic gate
- #16 — NBC News — Map: Track the spread of measles in the U.S. - NBC News — fails US semantic gate
- #17 — CNBC — Why the election could make Washington's looming next fiscal crisis harder - CNBC — fails US semantic gate
- #19 — Reuters — Houthi advance in Yemen puts U.S. in a new bind - Reuters — fails US semantic gate
- #21 — Reuters — Afghan woman deported from US in first use of secretive terrorism court - Reuters — fails US semantic gate
- #22 — Reuters — US consumer prices accelerate in August, push Fed closer to rate hike - Reuters — fails US semantic gate

## presidential
V5.1: 54 items, 8 sources, streak 14× Reuters; V5.2: 61 items, 13 sources, streak 6× Reuters.
V5.2 top sources: Reuters (27), Associated Press (22), The Guardian (2), CBC (1), BBC (1), NPR (1)
V5.2 duplicate flags: exact=0, fuzzy=1; mismatch candidates=39.
Mismatch candidates:
- #3 — CBC — Trump's 9/11 statements come under scrutiny again — weak/no presidential anchor
- #4 — Reuters — Trump tells Ukraine's Zelenskiy to stop hitting Russian diesel — weak/no presidential anchor
- #5 — BBC — Trump's comments on a united Ireland may have targeted audience across the Atlantic — weak/no presidential anchor
- #6 — NPR — Trump officials propose sweeping changes to the census that would reshape voting maps - NPR — weak/no presidential anchor
- #7 — NBC News — Trump calls for a Bombardier plane ban, drawing pushback from a GOP senator - NBC News — weak/no presidential anchor
- #11 — CNBC — Trump admin targets tax-exempt status at private colleges — threatening a key tax break for donations - CNBC — weak/no presidential anchor
- #14 — Associated Press — Trump calls on Ukraine to halt strikes on Russian diesel fuel, citing a global shortage — weak/no presidential anchor
- #15 — The Guardian — Trump says he will consider releasing more 9/11 records after families’ request — weak/no presidential anchor
- #17 — Associated Press — Trump calls AI risks a ‘hoax,’ says there is a ‘SICK conspiracy’ against AI and data centers - AP News — technology/product-looking headline outside Technology; weak/no presidential anchor
- #18 — Reuters — Trump dismisses AI safety alarm, says US already has tools to police industry - Reuters — technology/product-looking headline outside Technology; weak/no presidential anchor
- #19 — Associated Press — Trump nominates wife of 'God Bless the USA' singer Lee Greenwood to serve as US ambassador - AP News — weak/no presidential anchor
- #20 — Reuters — Trump approval up from record low, but outlook sours for Republicans, Reuters/Ipsos poll finds - Reuters — weak/no presidential anchor
Likely duplicate candidates:
- The Guardian: Trump says he will consider releasing more 9/11 records after families’ request  ⇄  Reuters: Trump says he will consider request to release more 9/11 records - Reuters (overlap 0.83)

## federal
V5.1: 25 items, 16 sources, streak 5× Reuters; V5.2: 34 items, 22 sources, streak 4× Reuters.
V5.2 top sources: Reuters (7), Associated Press (3), Politico (2), NPR (2), The Hill (2), The Seattle Times (2)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=3.
Mismatch candidates:
- #12 — France 24 — US Treasury issues $1 coin with Trump's face on it - France 24 — weak/no federal anchor
- #14 — Newsweek — Federal Judges Rebuke ICE Detention as Similar to WWII Internment Camps - Newsweek — weak/no federal anchor
- #25 — Politico — Appeals court rejects ICE detention policy, setting stage for SCOTUS - Politico — weak/no federal anchor

## legislation
V5.1: 24 items, 5 sources, streak 13× New Mexico Legislature; V5.2: 21 items, 2 sources, streak 6× New Mexico Legislature.
V5.2 top sources: New Mexico Legislature (13), Congress.gov (8)
V5.2 duplicate flags: exact=1, fuzzy=0; mismatch candidates=0.

## nm
V5.1: 52 items, 14 sources, streak 6× KRQE; V5.2: 57 items, 19 sources, streak 16× KRQE.
V5.2 top sources: KRQE (24), Santa Fe New Mexican (8), KOAT (4), KOB 4 (4), The Guardian (2), Tri City Record (2)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=0.

## local
V5.1: 369 items, 169 sources, streak 4× the-journal.com; V5.2: 336 items, 165 sources, streak 20× CBS News.
V5.2 top sources: CBS News (28), MLive.com (8), ABC News - Breaking News, Latest News and Videos (7), St. George News (4), Post Register (4), San Diego Union-Tribune (4)
V5.2 duplicate flags: exact=0, fuzzy=5; mismatch candidates=11.
Mismatch candidates:
- #4 — KOLD — Local leaders discuss affordability in Tucson, Pima County - KOLD — production classifier prefers region
- #28 — Los Angeles Times — Column: California provides tax breaks to Hollywood. Why not struggling news outlets? - Los Angeles Times — production classifier prefers federal
- #64 — KSAT — Man sentenced to 2 years in connection with Central Texas skimming operation, authorities say - KSAT — production classifier prefers federal
- #69 — KCBD — Texas Tech opening remote telescope access to campus community - KCBD — technology/product-looking headline outside Technology
- #103 — Yahoo Sports — Milwaukee Brewers get the vote MLB insiders would not give the Dodgers - Yahoo Sports — sports-looking headline in civic/geography tab
- #117 — PennLive.com — Bill Williams Obituary (1951 - 2026) - Memphis, TN - The Daily Memphian - PennLive.com — production classifier prefers legislation
- #170 — St. George News — ‘Food is the connector’: Multiple groups collaborate on community garden on Cedar City Paiute reservation - St. George News — production classifier prefers region
- #193 — Fairbanks Daily News-Miner — Fairbanks weighs new rules for e-bikes and e-motos - Fairbanks Daily News-Miner — production classifier prefers legislation
- #214 — Duluth News Tribune — US Senator's View: Trade with Canada, so good for Minnesota, threatened by tariffs - Duluth News Tribune — production classifier prefers federal
- #289 — St. George News — What's Going There: In-N-Out Burger, Cafe Rio open as Desert Color and SunRiver area explodes with growth - St. George News — production classifier prefers region
- #317 — CBS News — Judge exempts Chicago Archdiocese, nuns, other Catholic workers from Illinois medical aid in dying law - CBS News — production classifier prefers federal
Likely duplicate candidates:
- Fairbanks Daily News-Miner: Drink up - Fairbanks Daily News-Miner  ⇄  Fairbanks Daily News-Miner: Nuggets - Fairbanks Daily News-Miner (overlap 0.8)
- PennLive.com: Bill Williams Obituary (1951 - 2026) - Memphis, TN - The Daily Memphian - PennLive.com  ⇄  MLive.com: Ramon Briones Obituary (1974 - 2026) - Memphis, TN - The Daily Memphian - MLive.com (overlap 0.7)
- Fairbanks Daily News-Miner: Fairbanks weighs new rules for e-bikes and e-motos - Fairbanks Daily News-Miner  ⇄  Fairbanks Daily News-Miner: Nuggets - Fairbanks Daily News-Miner (overlap 0.8)
- Fairbanks Daily News-Miner: Tanana-Yukon Historical Society kicks off new season - Fairbanks Daily News-Miner  ⇄  Fairbanks Daily News-Miner: Nuggets - Fairbanks Daily News-Miner (overlap 0.8)
- PennLive.com: Marvin Campbell Obituary (2026) - Harrisburg, PA - PennLive.com  ⇄  PennLive.com: Marvin Wirt Obituary (2026) - Harrisburg, PA - PennLive.com (overlap 0.83)

## region
V5.1: 73 items, 40 sources, streak 6× East Idaho News; V5.2: 70 items, 47 sources, streak 1× ABC News - Breaking News, Latest News and Videos.
V5.2 top sources: ABC News - Breaking News, Latest News and Videos (6), Fox News (6), Oil City News (5), Arizona Daily Sun (3), CBS News (3), KRDO (2)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=2.
Mismatch candidates:
- #18 — KUOW — A bitter battle is brewing in one of Washington state’s last swing districts - KUOW — production classifier prefers legislation
- #29 — Deseret News — What Arkansas coach Ryan Silverfield said about Utah - Deseret News — sports-looking headline in civic/geography tab

## nfl
V5.1: 23 items, 2 sources, streak 22× ESPN; V5.2: 25 items, 2 sources, streak 22× ESPN.
V5.2 top sources: ESPN (23), CBS News (2)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=0.

## technology
V5.1: 68 items, 34 sources, streak 3× Politico; V5.2: 80 items, 39 sources, streak 1× Reuters.
V5.2 top sources: Reuters (10), TechCrunch (8), The Verge (6), The Guardian (5), CNBC (5), Wired (4)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=38.
Mismatch candidates:
- #1 — Reuters — COMMENTARY: Trading Day: AI-pocalypse now — fails Technology semantic gate
- #2 — NBC News — China dismisses AI slowdown calls and blasts ‘fearmongering’ from U.S. tech leaders — fails Technology semantic gate
- #4 — Ars Technica — Apple releases iOS 27, macOS Golden Gate 27 with Siri AI and Liquid Glass refinements - Ars Technica — fails Technology semantic gate
- #12 — CNBC — Trump goes scorched earth on AI warnings, raging about data center opposition and regulation - CNBC — fails Technology semantic gate
- #17 — Wired — The Top New Features in Apple’s iOS 27 and iPadOS 27 - wired.com — fails Technology semantic gate
- #19 — 디지털투데이 — Amodei AI slowdown talk spooks chip stocks while bitcoin rises. Why? - 디지털투데이 — fails Technology semantic gate
- #21 — Channel Insider — Apple’s 2026 Lineup: New Devices Open Bigger Opportunities for Channel Partners - Channel Insider — fails Technology semantic gate
- #25 — breitbart.com — Beijing Refuses to Slow AI Research, Criticizes ‘Fearmongering’ from U.S. - breitbart.com — fails Technology semantic gate
- #27 — HPCwire — Genesis Mission Project Uses AI to Speed Thin Film Development - HPCwire — fails Technology semantic gate
- #29 — Blockonomi — Market Watch: AI Chip Stocks Tumble, Crude Spikes Past $108, and Bitcoin Braces for Volatility - Blockonomi — fails Technology semantic gate
- #33 — The Hill — Ocasio-Cortez: ‘Put a data center up in Mar-a-Lago’ - The Hill — fails Technology semantic gate; production classifier prefers local
- #34 — The Missoulian — Shelf Life: University of Montana prof explores generative AI at Missoula Public Library - The Missoulian — fails Technology semantic gate

## gaming
V5.1: 63 items, 35 sources, streak 4× Tom's Hardware; V5.2: 59 items, 35 sources, streak 1× Reuters.
V5.2 top sources: IGN (10), PC Gamer (9), Polygon (3), Nintendo Life (3), Tom's Hardware (2), Notebookcheck (2)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=3.
Mismatch candidates:
- #54 — PC Gamer — Arc Raiders Expeditions may not come back: 'Maybe we'll scrap the whole system' - PC Gamer — hardware/technology-only headline in Gaming
- #56 — PC Gamer — Bungie delays next Marathon update and ends 'strict seasonal schedule' as it goes all-in on Destiny-like features - PC Gamer — hardware/technology-only headline in Gaming
- #58 — PC Gamer — Valve canned finished VR headsets 'three, four years ago' - PC Gamer — hardware/technology-only headline in Gaming

## military
V5.1: 50 items, 10 sources, streak 17× Defense News; V5.2: 46 items, 19 sources, streak 9× Defense News.
V5.2 top sources: Defense News (13), The Guardian (4), CBS News (4), Reuters (3), BBC (3), Al Jazeera (2)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=0.

