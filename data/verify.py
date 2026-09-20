import json, pathlib
v = json.loads(pathlib.Path('vendors.json').read_text(encoding='utf-8'))
a = json.loads(pathlib.Path('availability.json').read_text(encoding='utf-8'))
c = json.loads(pathlib.Path('knowledge/chunks.json').read_text(encoding='utf-8'))
print(f"vendors     : {len(v)}")
print(f"categories  : {sorted({x['category'] for x in v})}")
cities = sorted({x['city'] for x in v})
print(f"cities      : {cities}")
print(f"event_types : {sorted({t for x in v for t in x['event_types']})}")
print(f"availability: {len(a)}")
print(f"chunks      : {len(c)}")
print(f"documents   : {sorted({x['document_id'] for x in c})}")
# Sample vendor
sample = v[0]
print(f"\nSample vendor: {sample['name']} | cat={sample['category']} | city={sample['city']} | base=INR{sample['base_price']} | floor=INR{sample['price_floor']}")
print("ALL OK")
