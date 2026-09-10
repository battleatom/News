from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import re
import urllib.parse
import urllib.request

OUT = Path('state-legislation.json')
API = 'https://api.legiscan.com/'
MAX_PER_STATE = 12
STATES = {
    'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California','CO':'Colorado','CT':'Connecticut','DE':'Delaware','FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas','KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland','MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NY':'New York','NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah','VT':'Vermont','VA':'Virginia','WA':'Washington','WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming','DC':'District of Columbia'
}
STATUS = {0:'Pre-filed',1:'Introduced',2:'Engrossed',3:'Enrolled',4:'Passed',5:'Vetoed',6:'Failed'}
LOW_VALUE = ('commemorat','memorial','recogniz','honorary','post office','naming','designat','special day','special week','special month')


def request_json(key: str, op: str, **params):
    query = {'key':key,'op':op,**params}
    url = API + '?' + urllib.parse.urlencode(query)
    req = urllib.request.Request(url, headers={'User-Agent':'BattleAtom-News/1.0'})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode('utf-8','replace'))
    if data.get('status') != 'OK':
        raise RuntimeError(f'LegiScan {op} failed: {data}')
    return data


def useful(row):
    text = f"{row.get('title','')} {row.get('description','')}".lower()
    return not any(term in text for term in LOW_VALUE)


def date_key(row):
    return row.get('last_action_date') or row.get('status_date') or ''


def normalize_master(master):
    rows=[]
    for key,row in (master or {}).items():
        if not isinstance(row,dict) or not row.get('bill_id'):
            continue
        if useful(row): rows.append(row)
    rows.sort(key=lambda r:(date_key(r), int(r.get('status') or 0)), reverse=True)
    return rows[:MAX_PER_STATE]


def sponsor_text(bill):
    sponsors=bill.get('sponsors') or []
    primary=[s for s in sponsors if int(s.get('sponsor_type_id') or 0) in (0,1)] or sponsors
    names=[]
    for s in primary[:3]:
        name=(s.get('name') or '').strip()
        if name: names.append(name)
    return ', '.join(names)


def record_from(row, bill, state, state_name):
    history=bill.get('history') or []
    latest=history[-1].get('action','') if history else row.get('last_action','')
    official=(bill.get('state_link') or '').strip()
    return {
        'state':state,
        'stateName':state_name,
        'billId':int(row.get('bill_id')),
        'billNumber':bill.get('bill_number') or row.get('number') or '',
        'title':bill.get('title') or row.get('title') or '',
        'description':bill.get('description') or row.get('description') or row.get('title') or '',
        'status':STATUS.get(int(bill.get('status') if bill.get('status') is not None else row.get('status') or 0),'Active'),
        'statusDate':bill.get('status_date') or row.get('status_date') or '',
        'latestAction':latest,
        'latestActionDate':row.get('last_action_date') or bill.get('status_date') or '',
        'sponsor':sponsor_text(bill),
        'officialSource':official,
        'indexSource':bill.get('url') or row.get('url') or '',
        'changeHash':row.get('change_hash') or bill.get('change_hash') or '',
        'session':(bill.get('session') or {}).get('session_title') or (bill.get('session') or {}).get('session_name') or '',
    }


def main():
    key=(os.environ.get('LEGISCAN_API_KEY') or '').strip()
    if not key:
        print('LEGISCAN_API_KEY is not configured; preserving existing state-legislation.json.')
        return

    old={}
    if OUT.exists():
        try: old=json.loads(OUT.read_text(encoding='utf-8'))
        except Exception: old={}
    old_states=old.get('states') or {}
    result={}
    request_count=0
    detail_count=0
    errors=[]

    for state,state_name in STATES.items():
        try:
            master=request_json(key,'getMasterList',state=state); request_count+=1
            selected=normalize_master(master.get('masterlist'))
            old_by_id={str(r.get('billId')):r for r in (old_states.get(state,{}).get('bills') or [])}
            bills=[]
            for row in selected:
                bid=str(row.get('bill_id'))
                prior=old_by_id.get(bid)
                if prior and prior.get('changeHash')==row.get('change_hash'):
                    bills.append(prior)
                    continue
                detail=request_json(key,'getBill',id=bid); request_count+=1; detail_count+=1
                bills.append(record_from(row, detail.get('bill') or {}, state, state_name))
            result[state]={'state':state,'stateName':state_name,'bills':bills}
            print(f'{state}: {len(bills)} current bills ({sum(1 for r in bills if str(r.get("billId")) in old_by_id and old_by_id[str(r.get("billId"))].get("changeHash")==r.get("changeHash"))} cached)')
        except Exception as exc:
            errors.append(f'{state}: {exc}')
            if state in old_states:
                result[state]=old_states[state]
            else:
                result[state]={'state':state,'stateName':state_name,'bills':[]}
            print(f'{state}: preserving cache after error: {exc}')

    payload={
        'updatedAt':datetime.now(timezone.utc).isoformat(),
        'source':'LegiScan Public API for discovery/status; officialSource links point to state legislatures when supplied by the state.',
        'states':result,
        'requestCount':request_count,
        'detailRequests':detail_count,
        'errors':errors[:20],
    }
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'State legislation cache updated: {len(result)} jurisdictions, {request_count} API requests ({detail_count} changed bill details).')


if __name__=='__main__':
    main()
