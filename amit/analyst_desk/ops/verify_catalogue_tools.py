"""Check the deployed catalogue through authenticated read/calculation tools.

Run inside the app container, which already has scoped tool credentials. This
operator check creates no research run, approves no plan and publishes no note.
"""
import asyncio
from collections import Counter
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desk.data import Corpus
from desk.workflow import Engine


async def verify():
    source = Corpus()
    companies = source.companies()
    if len(companies) != 12 or Counter(row['sector'] for row in companies) != {'Technology': 6, 'Healthcare': 6}:
        raise ValueError('The deployed catalogue must contain twelve companies across the declared sectors')
    reader = object.__new__(Engine)
    calls = 0

    async def call(role, server, tool, **arguments):
        nonlocal calls
        value = await reader._wire_call(role, server, tool, arguments)
        calls += 1
        return value

    cells, chunks = [], 0
    for company in companies:
        ticker, years = company['ticker'], source.years(company['ticker'])
        if years != [2023, 2024, 2025]:
            raise ValueError('The deployed company is missing a required fiscal year')
        facts = await call('researcher', 'edgar', 'get_facts', ticker=ticker, years=years)
        if sorted(facts, key=lambda row: row['id']) != sorted(source.facts(ticker, years), key=lambda row: row['id']):
            raise ValueError('The deployed fact server has a different source snapshot')
        results = await call('researcher', 'filings-kb', 'search_filings', ticker=ticker, years=years,
                             query='operational risk revenue operating income', k=3)
        if not results or any(row['ticker'] != ticker or int(row['year']) not in years
                              or row['text'] != source.passage(row['id'])['text'] for row in results):
            raise ValueError('Deployed filing search returned evidence outside its source scope')
        for year in years:
            pair = {row['concept']: row for row in facts if row['fiscal_year'] == year}
            row = await call('quant', 'python-sandbox', 'calculate_margin',
                             revenue_fact_id=pair['revenue']['id'], operating_income_fact_id=pair['operating_income']['id'])
            if not source.verify_row(row):
                raise ValueError('Independent arithmetic verification rejected a deployed calculation')
            for item in ('1A', '7'):
                section = await call('risk', 'edgar', 'get_section', ticker=ticker, year=year, item=item)
                expected = source.section(ticker, year, item)
                if section['chunks'] != expected['chunks'] or section['source_ids'] != expected['source_ids']:
                    raise ValueError('The deployed section server has incomplete or mismatched cached chunks')
                chunks += len(section['chunks'])
            cells.append({'ticker': ticker, 'fiscal_year': year, 'period_start': row['period_start'],
                          'period_end': row['period_end'], 'margin_pct': row['margin_pct'], 'verified': True})
    return {'status': 'passed', 'verification_kind': 'operator_deployed_catalogue_tools',
            'source_fingerprint': source.fingerprint, 'company_count': len(companies),
            'sector_counts': dict(Counter(row['sector'] for row in companies)),
            'company_year_count': len(cells), 'verified_calculation_rows': len(cells),
            'verified_financial_values': len(cells) * 3, 'section_groups_checked': len(cells) * 2,
            'section_chunks_checked': chunks, 'search_scopes_checked': len(companies),
            'authenticated_tool_calls': calls, 'model_calls': 0, 'research_runs_created': 0,
            'human_decisions_submitted': 0, 'notes_published': 0, 'cells': cells,
            'limitations': ['Operational coverage check, not an independent research benchmark.',
                            'Source identity and arithmetic checks do not establish original Item boundaries or economic risk interpretation.']}


if __name__ == '__main__':
    try:
        print(json.dumps(asyncio.run(verify()), indent=2, sort_keys=True))
    except Exception as error:
        print('Catalogue tool verification failed: ' + type(error).__name__, file=sys.stderr)
        raise SystemExit(1)
