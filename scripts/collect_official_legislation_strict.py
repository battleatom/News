#!/usr/bin/env python3
"""Strict official legislation collector.

Uses the established Congress.gov/NM Legislature fetchers but never preserves
journalism cards when the official fetch is sparse. Whatever official records are
available become the entire Legislation tab; zero official records means an empty
Legislation tab rather than substituting news.
"""
import xml.etree.ElementTree as ET

import collect_official_legislation_v2 as core


def main():
    if not core.NEWS.exists():
        raise SystemExit('News feed not found')
    tree = ET.parse(core.NEWS)
    channel = tree.getroot().find('channel')
    if channel is None:
        raise SystemExit('RSS channel not found')

    federal_error = nm_error = None
    try:
        federal = core.fetch_federal()
    except Exception as exc:
        federal = []
        federal_error = exc
    try:
        nm = core.fetch_nm()
    except Exception as exc:
        nm = []
        nm_error = exc

    official = federal + nm
    for item in list(channel.findall('item')):
        if core.clean(item.findtext('category')) == 'legislation':
            channel.remove(item)
    for row in official:
        core.append_item(channel, row)

    tree.write(core.NEWS, encoding='utf-8', xml_declaration=True)
    print(
        f'Strict official legislation collection: {len(federal)} Congress.gov + '
        f'{len(nm)} New Mexico Legislature = {len(official)} official records. '
        f'No journalism cards preserved. federal_error={federal_error!r} nm_error={nm_error!r}'
    )


if __name__ == '__main__':
    main()
