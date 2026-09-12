#!/usr/bin/env python3
import importlib.util
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('briefs',ROOT/'scripts/create_content_briefs.py')
briefs=importlib.util.module_from_spec(spec);spec.loader.exec_module(briefs)

source=(
    'Microsoft announced a pricing change for its subscription service after reviewing customer demand and operating costs, '
    'which executives said would take effect next month and apply to both new and existing customers. '
    'The company also outlined expanded cloud storage and improved collaboration tools for business customers. '
    'Executives reported that the rollout would begin in October 2026 for accounts in the United States.'
)
brief=briefs.build_brief('Microsoft raises Copilot Pro price to $29.99',source,'Reuters','technology')
assert brief
assert '…' not in brief and '...' not in brief
assert len(brief)<=briefs.MAX_BRIEF_CHARS
sentences=[x.strip() for x in re.split(r'(?<=[.!?])\s+',brief) if x.strip()]
assert 1<=len(sentences)<=2
assert all(x[-1] in '.!?' for x in sentences)
assert not any(x.endswith((',', ';', ':')) for x in sentences)

long=(
    'The company announced a new product with several changes for customers and developers, which includes a long list of '
    'features, compatibility details, regional restrictions, pricing conditions, account requirements, migration notes, '
    'developer policies, enterprise controls, and other implementation details that continue well beyond a normal card summary.'
)
shortened=briefs.complete_clause(long)
assert '…' not in shortened and '...' not in shortened
if shortened:
    assert len(shortened)<=briefs.MAX_FACT_CHARS

fallback=briefs.fallback_brief({'title':'Example product update','source':'Reuters','category':'technology'})
assert '…' not in fallback and fallback.endswith('.')

css=(ROOT/'styles/content-briefs.css').read_text(encoding='utf-8')
assert '-webkit-line-clamp' not in css
assert 'overflow:hidden' not in css
assert 'overflow:visible' in css
print('Story context and complete-brief regressions passed.')
