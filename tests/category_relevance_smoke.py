import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.refine_tech_gaming import tech_relevance_decision, text
from scripts.filter_landing_pages import is_landing_page

NEWS = Path('News')


def make_item(title, description='', source='Test Source', category='technology'):
    item = ET.Element('item')
    ET.SubElement(item, 'title').text = title
    ET.SubElement(item, 'description').text = description
    ET.SubElement(item, 'source').text = source
    ET.SubElement(item, 'category').text = category
    ET.SubElement(item, 'link').text = 'https://example.com/story'
    ET.SubElement(item, 'pubDate').text = 'Thu, 10 Sep 2026 20:00:00 +0000'
    return item


def assert_fixture(title, description, expected, source='Test Source'):
    item = make_item(title, description, source)
    actual = tech_relevance_decision(item)
    assert actual == expected, f'{title!r}: expected {expected}, got {actual}'


def main():
    # User-reported category failures.
    assert_fixture(
        "Kimmel’s ABC show won’t air interview with Democrat because of Trump FCC threats - Ars Technica",
        'Talarico talk will be on YouTube after ABC stations raised concerns about dealing with the FCC.',
        'federal',
        'Ars Technica',
    )
    assert_fixture(
        "Hit Broadway play ‘Oh, Mary!’ is coming to HBO Max next year. - The Verge",
        'The filmed Broadway performance is expected to stream on HBO and HBO Max.',
        'drop',
        'The Verge',
    )
    assert_fixture(
        'Congratulations! You Just Lived Through the Hottest Month Ever Recorded - wired.com',
        'Climate change is the main culprit for the global temperature record, with El Niño also contributing.',
        'world',
        'Wired',
    )
    assert_fixture(
        "Question - Pc displays orange light unless powered off and turned back on while at an angle - Tom's Hardware",
        'A reader asks for troubleshooting help with a PC display.',
        'drop',
        "Tom's Hardware",
    )

    # Legitimate technology/legal stories must survive the stricter gate.
    assert_fixture(
        'OpenAI Wants to Know if an AI Industry Slowdown Would Even Be Legal - wired.com',
        'AI leaders are examining antitrust law and whether it could affect coordination in the artificial intelligence industry.',
        'technology',
        'Wired',
    )
    assert_fixture(
        'LinkedIn beats BrowserGate lawsuits over scanning users’ Chrome extensions - Ars Technica',
        'The lawsuits concerned browser extensions, privacy, and scanning behavior on LinkedIn.',
        'technology',
        'Ars Technica',
    )

    espn = make_item('Watch ESPN - Stream Live Sports & ESPN Originals', source='ESPN', category='world')
    assert is_landing_page(espn), 'ESPN streaming product page was not recognized as a landing page'
    real_espn = make_item('NFL owners approve revised kickoff rule for 2026 season', source='ESPN', category='nfl')
    assert not is_landing_page(real_espn), 'A normal ESPN news headline was incorrectly rejected'

    # Feed-wide post-filter validation. The workflow runs the two filters before this test.
    tree = ET.parse(NEWS)
    items = tree.getroot().findall('./channel/item')
    tech = [item for item in items if text(item, 'category') == 'technology']
    assert len(tech) >= 10, f'Technology was over-filtered: only {len(tech)} stories remain'

    wrong = [(text(item, 'title'), tech_relevance_decision(item)) for item in tech if tech_relevance_decision(item) != 'technology']
    assert not wrong, 'Technology still contains off-topic stories: ' + repr(wrong[:8])

    all_titles = [text(item, 'title').lower() for item in items]
    assert not any(title.startswith('watch espn - stream live sports') for title in all_titles), 'ESPN promotional landing page remains in feed'

    print(f'CATEGORY RELEVANCE PASS — {len(tech)} Technology stories all satisfy the relevance gate; fixtures route correctly.')


if __name__ == '__main__':
    main()
