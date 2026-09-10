from pathlib import Path
import re

P = Path('scripts/update_news.py')
s = P.read_text(encoding='utf-8')

# Underreported first page should be genuinely varied: one story per broad topic
# before a second story from any topic can appear.
s = s.replace(
    'topic_cap = 2 if first_page else 4',
    'topic_cap = 1 if first_page else 4',
)

# Famous institutions/names alone should not make a story Underreported. Require
# either a public-interest newsroom or a substantive accountability/impact signal.
needle = '''        public_interest_bonus += 8 if any(t in text for t in (
            'investigation','audit','inspector general','whistleblower','public records','lawsuit','settlement',
            'contamination','pollution','hospital','medicaid','workers','labor','privacy','surveillance',
            'civil rights','tribal','indigenous','veteran','fraud','regulation','legislation','bill','law'
        )) else 0
        celebrity_penalty = 10 if any(t in text for t in ('donald trump','president trump','elon musk')) and public_interest_bonus < 12 else 0
'''
replacement = '''        public_interest_bonus += 8 if any(t in text for t in (
            'investigation','audit','inspector general','whistleblower','public records','lawsuit','settlement',
            'contamination','pollution','hospital','medicaid','workers','labor','privacy','surveillance',
            'civil rights','tribal','indigenous','veteran','fraud','regulation','legislation','bill','law'
        )) else 0
        substantive_signal = any(t in text for t in (
            'investigation','audit','inspector general','whistleblower','public records','lawsuit','settlement',
            'contamination','pollution','hospital','medicaid','workers','labor','privacy','surveillance',
            'civil rights','tribal','indigenous','veteran','fraud','regulation','legislation','bill','law',
            'court','ruling','election','voting','killed','deaths','war','attack','strike','famine','humanitarian',
            'wildfire','drought','flood','outbreak','recall','bankruptcy','layoffs','school','education','housing'
        ))
        public_interest_source = any(t in src_raw for t in UNDERREPORTED_PUBLIC_INTEREST_TOKENS)
        if not substantive_signal and not public_interest_source:
            continue
        celebrity_penalty = 10 if any(t in text for t in ('donald trump','president trump','elon musk')) and public_interest_bonus < 12 else 0
'''
if needle not in s:
    raise SystemExit('Could not locate Underreported substantive-signal insertion point')
s = s.replace(needle, replacement, 1)

# Legislation must represent a meaningful government action or a materially
# important measure. Reject database noise, promotional pages, bare amendments,
# and low-impact raw government entries that merely contain bill-like words.
pattern = re.compile(r'def legislation_action_allowed\(item\):.*?\n\ndef legislation_score', re.S)
new_func = r'''def legislation_action_allowed(item):
    title = (item.get('title') or '').lower()
    source = (item.get('source') or '').lower()
    padded = f" {title} "

    # Never treat promotional/ceremonial pages or generic pre-publication queues
    # as legislation news, even when their titles happen to mention a bill.
    reject_always = (
        'public inspection:', 'personal vision', 'historic results',
        'promises made', 'patriot day', 'proclamation', 'remarks by',
        'statement from the president', 'fact sheet: president',
    )
    if any(term in title for term in reject_always):
        return False

    # Bare profile and amendment/database entries are not useful cards without
    # an explanatory action headline.
    if title.startswith(('representative ', 'senator ', 'text - ', 'actions - ')):
        return False
    if re.match(r'^s\.amdt\.\d+\s+to\s+', title):
        return False

    years = [int(y) for y in re.findall(r'\b(19\d{2}|20\d{2})\b', title)]
    current_year = datetime.now(timezone.utc).year
    if years and min(years) < current_year - 2 and ('congress' in source or 'federal register' in source):
        return False

    explicit_action = any(term in padded for term in (
        ' signed into law ', ' signs bill ', ' signed bill ', ' enacted ',
        ' passes house ', ' house passes ', ' passes senate ', ' senate passes ',
        ' passed the house ', ' passed the senate ', ' vetoed ', ' vetoes ',
        ' executive order ', ' final rule ', ' proposed rule ', ' rulemaking ',
        ' rescission ', ' repeal ', ' ordinance ', ' resolution '
    ))
    if explicit_action:
        return True

    # Established journalism may surface an introduced/proposed measure before
    # the official database shows a clear status; keep it if the headline is
    # explicitly about legislation/regulation.
    government_source = any(term in source for term in (
        'congress.gov','congress gov','federal register','white house','.gov','nmlegis'
    ))
    measure_terms = (' bill ', ' h.r.', ' s.', ' act ', ' legislation ', ' regulation ', ' ordinance ')
    if not government_source and any(term in padded for term in measure_terms):
        return True

    # Raw government pages are retained only for measures with broad public
    # consequence. This avoids filling the tab with obscure naming/site bills.
    high_impact = any(term in padded for term in (
        ' war powers ', ' military ', ' national security ', ' veterans ',
        ' medicaid ', ' medicare ', ' health care ', ' healthcare ', ' hospital ',
        ' tax ', ' taxes ', ' budget ', ' spending ', ' housing ',
        ' immigration ', ' border ', ' asylum ', ' voting ', ' election ',
        ' civil rights ', ' privacy ', ' surveillance ', ' cybersecurity ',
        ' artificial intelligence ', ' antitrust ', ' labor ', ' wage ', ' workers ',
        ' education ', ' student ', ' abortion ', ' environment ', ' pollution ',
        ' water ', ' climate ', ' energy ', ' consumer ', ' disability ', ' tribal ', ' indigenous '
    ))
    if government_source and high_impact and any(term in padded for term in measure_terms):
        return True

    # Substantive Federal Register rules can be useful even without the literal
    # phrase "final rule," but routine notices and information collections are not.
    if 'federal register' in source:
        if any(term in title for term in ('information collection', 'combined filings', 'postal products', 'meeting notice', 'availability of')):
            return False
        return high_impact and any(term in title for term in (
            'requirements', 'standards', 'eligibility', 'registration', 'fee for',
            'ban on', 'regulation of', 'amendments to', 'rule on', 'rules for'
        ))
    return False


def legislation_score'''
s2, n = pattern.subn(lambda m: new_func, s, count=1)
if n != 1:
    raise SystemExit('Could not replace legislation_action_allowed()')
s = s2

P.write_text(s, encoding='utf-8')
print('Tightened Underreported first-page diversity and filtered legislation to meaningful, high-impact actions.')
