# V5.1 vs V5.2 Content Audit

Automated semantic + sequence audit. Mismatch candidates are review flags, not automatic deletions.

| Tab | V5.1 count | V5.2 count | V5.1 mismatches | V5.2 mismatches | V5.1 max source streak | V5.2 max source streak | V5.2 top source |
|---|---:|---:|---:|---:|---|---|---|
| top | 53 | 46 | 0 | 0 | 2× Fox News | 1× Reuters | Fox News 3 (6.5%) |
| x | 10 | 10 | 0 | 0 | 1× KFF Health News | 1× KFF Health News | KFF Health News 1 (10.0%) |
| underreported | 75 | 74 | 0 | 0 | 4× ProPublica | 4× ProPublica | Inside Climate News 15 (20.3%) |
| entertainment | 80 | 76 | 20 | 23 | 2× The Hollywood Reporter | 4× People | Variety 6 (7.9%) |
| world | 90 | 81 | 55 | 45 | 9× Reuters | 11× Reuters | Reuters 37 (45.7%) |
| us | 20 | 22 | 14 | 14 | 4× Reuters | 3× Reuters | Reuters 7 (31.8%) |
| presidential | 54 | 60 | 34 | 38 | 14× Reuters | 16× Reuters | Reuters 25 (41.7%) |
| federal | 25 | 34 | 2 | 3 | 5× Reuters | 5× Reuters | Reuters 6 (17.6%) |
| legislation | 24 | 23 | 0 | 0 | 13× New Mexico Legislature | 13× New Mexico Legislature | New Mexico Legislature 13 (56.5%) |
| nm | 52 | 59 | 1 | 1 | 6× KRQE | 10× krqe.com | krqe.com 23 (39.0%) |
| local | 369 | 359 | 19 | 17 | 4× the-journal.com | 4× St. George News | CBS News 26 (7.2%) |
| region | 73 | 73 | 3 | 7 | 6× East Idaho News | 3× Arizona Daily Sun | CBS News 7 (9.6%) |
| nfl | 23 | 25 | 0 | 0 | 22× ESPN | 23× ESPN | ESPN 23 (92.0%) |
| technology | 68 | 70 | 25 | 26 | 3× Politico | 2× Reuters | TechCrunch 9 (12.9%) |
| gaming | 63 | 61 | 4 | 4 | 4× Tom's Hardware | 4× Tom's Hardware | IGN 11 (18.0%) |
| military | 50 | 47 | 0 | 0 | 17× Defense News | 8× Defense News | Defense News 13 (27.7%) |

Exact cross-tab repeat groups: V5.1=0, V5.2=0

## top
V5.1: 53 items, 11 sources, streak 2× Fox News; V5.2: 46 items, 18 sources, streak 1× Reuters.
V5.2 top sources: Fox News (3), CBS News (3), Associated Press (3), The New York Times (3), CNBC (3), NPR (3)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=0.

## x
V5.1: 10 items, 9 sources, streak 1× KFF Health News; V5.2: 10 items, 10 sources, streak 1× KFF Health News.
V5.2 top sources: KFF Health News (1), Yahoo Finance (1), Yahoo News (1), The Guardian (1), Wired (1), Entertainment Weekly (1)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=0.

## underreported
V5.1: 75 items, 22 sources, streak 4× ProPublica; V5.2: 74 items, 21 sources, streak 4× ProPublica.
V5.2 top sources: Inside Climate News (15), KFF Health News (11), ProPublica (9), The Marshall Project (8), Grist (7), Source New Mexico (4)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=0.

## entertainment
V5.1: 80 items, 28 sources, streak 2× The Hollywood Reporter; V5.2: 76 items, 28 sources, streak 4× People.
V5.2 top sources: Variety (6), USA Today (6), People (6), Yahoo News (6), Billboard (6), The Hollywood Reporter (5)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=23.
Mismatch candidates:
- #1 — Variety — 2026 Emmys Predictions in Every Category (Final) - Variety — weak/no entertainment anchor
- #2 — Variety — Bob Mackie, Renowned Fashion Designer to Cher, Tina Turner, Carol Burnett and More, Dies at 87 - Variety — weak/no entertainment anchor
- #4 — USA Today — See the best photos from New York Fashion Week 2026 - USA Today — weak/no entertainment anchor
- #7 — USA Today — Zendaya and Tom Holland's wedding gets bombshell update from Law Roach - USA Today — weak/no entertainment anchor
- #9 — USA Today — Hayden Panettiere's boyfriend Brian Hickerson detained, his brother arrested - USA Today — weak/no entertainment anchor
- #12 — USA Today — Sydney Sweeney's new sports ad is not her first controversy - USA Today — weak/no entertainment anchor
- #13 — E! News — 7 New York Fashion Week Runway Trends That Are Surprisingly Wearable for Fall - E! News — weak/no entertainment anchor
- #16 — People — Gillian Anderson Reveals She Identifies as Pansexual, Reflects on Relationships with Women: ‘I Didn’t Have the Language’ - People.com — weak/no entertainment anchor
- #18 — People — Mikayla Matthews Announces Shocking Exit from ‘Mormon Wives’ - People.com — weak/no entertainment anchor
- #19 — Deadline — Gary Myers Dies: NASCAR Driver, Patriarch Of Racing Family Was 76 - Deadline — weak/no entertainment anchor
- #22 — Deadline — Pierce Brosnan Says Tom Hardy ‘MobLand’ Feud Was “Storm In A Teacup” - Deadline — weak/no entertainment anchor
- #27 — People — Influencer Madalina Apostol Dies a Month After Celebrating 40th Birthday - People.com — weak/no entertainment anchor

## world
V5.1: 90 items, 32 sources, streak 9× Reuters; V5.2: 81 items, 32 sources, streak 11× Reuters.
V5.2 top sources: Reuters (37), NBC News (3), CBS News (3), WTHR (3), Defense News (3), The Guardian (3)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=45.
Mismatch candidates:
- #2 — Yahoo Sports — 2 Indiana football veterans ineligible as court case continues. What we know — fails World semantic gate; sports-looking headline in civic/geography tab
- #6 — CBS News — Negotiations resume amid monthslong lockout of union workers at BP refinery in Whiting, Indiana — fails World semantic gate
- #7 — WTHR — Indiana State Police investigating officer-involved shooting after high-speed chase in western Indiana — fails World semantic gate
- #10 — Ars Technica — Rocket Report: Europe joins the commercial launch club; a Ravn X sighting? — fails World semantic gate
- #12 — Federal Register (.gov) — Iranian Transactions and Sanctions Regulations — fails World semantic gate
- #13 — IGN — Indiana Jones - IGN Deutschland — fails World semantic gate
- #14 — IndyStar — Reports of ICE activity surge across Indianapolis — fails World semantic gate
- #15 — Reuters — COMMENTARY: Trading Day: AI-pocalypse now — fails World semantic gate; technology/product-looking headline outside Technology
- #16 — Reuters — How China is preparing for the risk of AI escaping human control — technology/product-looking headline outside Technology
- #17 — Reuters — Iceland's last whaling company shrugs off threat of permanent ban — fails World semantic gate
- #18 — Defense News — US, South Korean officials to broach thorny Hormuz mission at talks this week — fails World semantic gate
- #20 — Reuters — Germany says halting AI development not 'viable' as Europe weighs safety of new tech — technology/product-looking headline outside Technology

## us
V5.1: 20 items, 12 sources, streak 4× Reuters; V5.2: 22 items, 13 sources, streak 3× Reuters.
V5.2 top sources: Reuters (7), NBC News (2), CNBC (2), Associated Press (2), IGN (1), The New York Times (1)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=14.
Mismatch candidates:
- #2 — Reuters — US NTSB says one-third of FAA answers to safety recommendations are 'unacceptable' - Reuters — fails US semantic gate
- #4 — Reuters — US rail fuel surcharges on grain hit record highs, squeezing farmers in harvest season - Reuters — fails US semantic gate
- #5 — Reuters — Houthi advance in Yemen puts U.S. in a new bind - Reuters — fails US semantic gate
- #6 — The New York Times — Visa Issue Threatens U.S.-Brazil Cooperation on Crime - The New York Times — fails US semantic gate
- #7 — Time Magazine — U.S. Diesel Prices Just Surpassed a Record $6 Per Gallon. Here Are Three Ways That Affects You - Time Magazine — fails US semantic gate
- #8 — Reuters — Afghan woman deported from US in first use of secretive terrorism court - Reuters — fails US semantic gate
- #10 — NBC News — Map: Track the spread of measles in the U.S. - NBC News — fails US semantic gate
- #11 — Reuters — US consumer prices accelerate in August, push Fed closer to rate hike - Reuters — fails US semantic gate
- #12 — Reuters — Peru to join US anti-drug coalition 'Shield of the Americas' after Rubio visit - Reuters — fails US semantic gate
- #13 — Reuters — EXCLUSIVE: US grant for MAGA-aligned groups in Europe excludes French applicants over election fears - Reuters — fails US semantic gate
- #14 — ABC News - Breaking News, Latest News and Videos — How every US state approaches 9/11 history in schools - ABC News - Breaking News, Latest News and Videos — fails US semantic gate
- #15 — AP News — George Clooney on the current state of US politics - AP News — fails US semantic gate

## presidential
V5.1: 54 items, 8 sources, streak 14× Reuters; V5.2: 60 items, 14 sources, streak 16× Reuters.
V5.2 top sources: Reuters (25), Associated Press (23), The Guardian (1), CBC (1), BBC (1), NPR (1)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=38.
Mismatch candidates:
- #3 — CBC — Trump's 9/11 statements come under scrutiny again — weak/no presidential anchor
- #4 — Associated Press — Trump calls on Ukraine to halt strikes on Russian diesel fuel, citing a global shortage — weak/no presidential anchor
- #5 — Reuters — Trump tells Ukraine's Zelenskiy to stop hitting Russian diesel — weak/no presidential anchor
- #6 — BBC — Trump's comments on a united Ireland may have targeted audience across the Atlantic — weak/no presidential anchor
- #8 — NPR — Trump officials propose sweeping changes to the census that would reshape voting maps - NPR — weak/no presidential anchor
- #9 — NBC News — Trump calls for a Bombardier plane ban, drawing pushback from a GOP senator - NBC News — weak/no presidential anchor
- #10 — Reuters — Trump dismisses AI safety alarm, says US already has tools to police industry - Reuters — technology/product-looking headline outside Technology; weak/no presidential anchor
- #11 — Reuters — Trump approval up from record low, but outlook sours for Republicans, Reuters/Ipsos poll finds - Reuters — weak/no presidential anchor
- #12 — Reuters — Trump calls $5,000 payouts 'easy' to fit into federal budget - Reuters — weak/no presidential anchor
- #13 — Reuters — Trump downplays report China entities helped Iran before attack that killed US troops - Reuters — weak/no presidential anchor
- #14 — Reuters — Trump reiterates support for united Ireland, says won't talk about Scotland 'yet' - Reuters — weak/no presidential anchor
- #15 — Reuters — Trump says US could stay in Iran and keep oil, like Venezuela deal - Reuters — weak/no presidential anchor

## federal
V5.1: 25 items, 16 sources, streak 5× Reuters; V5.2: 34 items, 23 sources, streak 5× Reuters.
V5.2 top sources: Reuters (6), Associated Press (4), Politico (2), NPR (2), The Hill (2), Fresno Bee (1)
V5.2 duplicate flags: exact=0, fuzzy=1; mismatch candidates=3.
Mismatch candidates:
- #19 — France 24 — US Treasury issues $1 coin with Trump's face on it - France 24 — weak/no federal anchor
- #22 — Newsweek — Federal Judges Rebuke ICE Detention as Similar to WWII Internment Camps - Newsweek — weak/no federal anchor
- #23 — Politico — Appeals court rejects ICE detention policy, setting stage for SCOTUS - Politico — weak/no federal anchor
Likely duplicate candidates:
- USA Today: No constitutional right to clean water, federal court finds - USA Today  ⇄  Yahoo Finance: Federal court tells lead-poisoned Jackson, Mississippi residents they have no constitutional right to clean water - Yahoo Finance (overlap 0.89)

## legislation
V5.1: 24 items, 5 sources, streak 13× New Mexico Legislature; V5.2: 23 items, 4 sources, streak 13× New Mexico Legislature.
V5.2 top sources: New Mexico Legislature (13), Congress.gov (8), Associated Press (1), The Arkansas Democrat-Gazette (1)
V5.2 duplicate flags: exact=1, fuzzy=0; mismatch candidates=0.

## nm
V5.1: 52 items, 14 sources, streak 6× KRQE; V5.2: 59 items, 21 sources, streak 10× krqe.com.
V5.2 top sources: krqe.com (23), Santa Fe New Mexican (8), KOAT (4), KOB 4 (4), The Guardian (3), Tri City Record (2)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=1.
Mismatch candidates:
- #5 — Yahoo Sports — OU football vs New Mexico TV channel, odds, scouting report for Sooners-Lobos - Yahoo Sports — sports-looking headline in civic/geography tab

## local
V5.1: 369 items, 169 sources, streak 4× the-journal.com; V5.2: 359 items, 171 sources, streak 4× St. George News.
V5.2 top sources: CBS News (26), ABC News - Breaking News, Latest News and Videos (8), MLive.com (7), AL.com (5), Tri City Record (4), the-journal.com (4)
V5.2 duplicate flags: exact=0, fuzzy=3; mismatch candidates=17.
Mismatch candidates:
- #7 — KOLD — Local leaders discuss affordability in Tucson, Pima County - KOLD — production classifier prefers region
- #8 — Arizona Daily Sun — LOCAL ROUNDUP: Flagstaff football falls to 0-3 with loss at Tempe - Arizona Daily Sun — sports-looking headline in civic/geography tab
- #16 — Durango Herald — Juan Galis Sanchez Obituary (1989 - 2026) - Denver, CO - The Denver Gazette - Durango Herald — production classifier prefers region
- #29 — St. George News — ‘Food is the connector’: Multiple groups collaborate on community garden on Cedar City Paiute reservation - St. George News — production classifier prefers region
- #30 — St. George News — What's Going There: In-N-Out Burger, Cafe Rio open as Desert Color and SunRiver area explodes with growth - St. George News — production classifier prefers region
- #39 — The Missoulian — Shelf Life: University of Montana prof explores generative AI at Missoula Public Library - The Missoulian — technology/product-looking headline outside Technology
- #98 — Yakima Herald-Republic — PNW power crunch starts with AI. The bigger challenge may come after - Yakima Herald-Republic — technology/product-looking headline outside Technology
- #104 — Fairbanks Daily News-Miner — Fairbanks weighs new rules for e-bikes and e-motos - Fairbanks Daily News-Miner — production classifier prefers legislation
- #125 — KCBD — Texas Tech opening remote telescope access to campus community - KCBD — technology/product-looking headline outside Technology
- #157 — The Virginian-Pilot — 757Teamz field hockey Top 15: Key win lifts Norfolk Academy as top teams brace for rugged games - The Virginian-Pilot — sports-looking headline in civic/geography tab
- #175 — Sports Illustrated — University City Lions Football (St. Louis, MO) News - Sports Illustrated — sports-looking headline in civic/geography tab
- #198 — Duluth News Tribune — US Senator's View: Trade with Canada, so good for Minnesota, threatened by tariffs - Duluth News Tribune — production classifier prefers federal
Likely duplicate candidates:
- Fairbanks Daily News-Miner: Gary Lane - Fairbanks Daily News-Miner  ⇄  Fairbanks Daily News-Miner: Drink up - Fairbanks Daily News-Miner (overlap 0.67)
- PennLive.com: Bill Williams Obituary (1951 - 2026) - Memphis, TN - The Daily Memphian - PennLive.com  ⇄  MLive.com: Ramon Briones Obituary (1974 - 2026) - Memphis, TN - The Daily Memphian - MLive.com (overlap 0.7)
- PennLive.com: Marvin Campbell Obituary (2026) - Harrisburg, PA - PennLive.com  ⇄  PennLive.com: Marvin Wirt Obituary (2026) - Harrisburg, PA - PennLive.com (overlap 0.83)

## region
V5.1: 73 items, 40 sources, streak 6× East Idaho News; V5.2: 73 items, 42 sources, streak 3× Arizona Daily Sun.
V5.2 top sources: CBS News (7), ABC News - Breaking News, Latest News and Videos (6), Fox News (6), Yahoo Sports (4), Oil City News (4), Arizona Daily Sun (3)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=7.
Mismatch candidates:
- #18 — CBS News — Nevada County DA faces scrutiny after prosecutors allegedly used generative AI that fabricated facts - CBS News — technology/product-looking headline outside Technology
- #25 — KUOW — A bitter battle is brewing in one of Washington state’s last swing districts - KUOW — production classifier prefers legislation
- #38 — Yahoo Sports — Iowa football rises in latest AP Top 25 rankings - Yahoo Sports — sports-looking headline in civic/geography tab
- #40 — Sports Illustrated — The Biggest Reason Why Iowa State Football Lost to Iowa in Cy-Hawk Game - Sports Illustrated — sports-looking headline in civic/geography tab
- #48 — OregonLive.com — What TV channel is West Virginia football on today? Preview, streaming options - OregonLive.com — sports-looking headline in civic/geography tab
- #50 — Yahoo Sports — West Virginia assistant coach Noel Devine arrested on strangulation charge hours after WVU's win over UT-Martin - Yahoo Sports — sports-looking headline in civic/geography tab
- #72 — CBS News — Former Georgia Democratic state lawmaker avoids additional jail time for COVID-19 unemployment fraud - CBS News — production classifier prefers federal

## nfl
V5.1: 23 items, 2 sources, streak 22× ESPN; V5.2: 25 items, 2 sources, streak 23× ESPN.
V5.2 top sources: ESPN (23), CBS News (2)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=0.

## technology
V5.1: 68 items, 34 sources, streak 3× Politico; V5.2: 70 items, 35 sources, streak 2× Reuters.
V5.2 top sources: TechCrunch (9), The Verge (6), Wired (5), Reuters (4), Yahoo Finance (4), The Guardian (4)
V5.2 duplicate flags: exact=0, fuzzy=1; mismatch candidates=26.
Mismatch candidates:
- #2 — Reuters — Global AI stocks fall as industry chiefs call for slowing development — fails Technology semantic gate
- #3 — NBC News — Two of the world’s top AI chief executives publicly agree on slowing AI development — fails Technology semantic gate
- #11 — Ars Technica — Apple releases iOS 27, macOS Golden Gate 27 with Siri AI and Liquid Glass refinements - Ars Technica — fails Technology semantic gate
- #13 — The Verge — Apple releases iOS 27 with Siri AI overhaul - theverge.com — fails Technology semantic gate
- #14 — TechCrunch — Microsoft’s new AI ‘code of conduct’ tells models not to hack systems or trick humans - TechCrunch — fails Technology semantic gate
- #16 — CNBC — Trump goes scorched earth on AI warnings, raging about data center opposition and regulation - CNBC — fails Technology semantic gate
- #23 — The Verge — Is Big Tech’s AI slowdown a safety pact or a cartel? - theverge.com — fails Technology semantic gate
- #24 — The Verge — Apple Home’s new security camera features cost as much as $60 a month - theverge.com — fails Technology semantic gate
- #25 — The Guardian — AI CEOs say they need to slow the pace of development. But will they? - The Guardian — fails Technology semantic gate
- #27 — Ars Technica — AI bots "Timmy," "Ren," and "Jackie" are flooding social media with slop - Ars Technica — fails Technology semantic gate
- #30 — Ars Technica — AI leaders want to hit the brakes after years of reckless speed - Ars Technica — fails Technology semantic gate
- #31 — Wired — The Top New Features in Apple’s iOS 27 and iPadOS 27 - WIRED — fails Technology semantic gate
Likely duplicate candidates:
- Ars Technica: Apple releases iOS 27, macOS Golden Gate 27 with Siri AI and Liquid Glass refinements - Ars Technica  ⇄  The Verge: Apple releases iOS 27 with Siri AI overhaul - theverge.com (overlap 0.88)

## gaming
V5.1: 63 items, 35 sources, streak 4× Tom's Hardware; V5.2: 61 items, 35 sources, streak 4× Tom's Hardware.
V5.2 top sources: IGN (11), PC Gamer (9), Tom's Hardware (4), Nintendo Life (3), Notebookcheck (2), Polygon (2)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=4.
Mismatch candidates:
- #24 — IGN — This Fantasy Party Game Combines Drinking Rules With D&D-Themed Gameplay - IGN — fails Gaming semantic gate
- #55 — PC Gamer — Arc Raiders Expeditions may not come back: 'Maybe we'll scrap the whole system' - PC Gamer — hardware/technology-only headline in Gaming
- #58 — PC Gamer — Bungie delays next Marathon update and ends 'strict seasonal schedule' as it goes all-in on Destiny-like features - PC Gamer — hardware/technology-only headline in Gaming
- #59 — PC Gamer — Valve canned finished VR headsets 'three, four years ago' - PC Gamer — hardware/technology-only headline in Gaming

## military
V5.1: 50 items, 10 sources, streak 17× Defense News; V5.2: 47 items, 19 sources, streak 8× Defense News.
V5.2 top sources: Defense News (13), The Guardian (4), CBS News (4), Reuters (3), BBC (3), CNN (2)
V5.2 duplicate flags: exact=0, fuzzy=0; mismatch candidates=0.

