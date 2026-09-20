"""Debug the seed step by step."""
import sys, time
sys.path.insert(0, '.')

print("Step 1: importing...", flush=True)
from seed import generate_vendors, generate_availability, get_knowledge_chunks
print("Step 2: import done", flush=True)

t = time.time()
vendors = generate_vendors()
print(f"Step 3: vendors done: {len(vendors)} in {time.time()-t:.1f}s", flush=True)

t = time.time()
avail = generate_availability(vendors)
print(f"Step 4: availability done: {len(avail)} in {time.time()-t:.1f}s", flush=True)

t = time.time()
chunks = get_knowledge_chunks()
print(f"Step 5: chunks done: {len(chunks)} in {time.time()-t:.1f}s", flush=True)

import json
from pathlib import Path
out = Path('.')

t = time.time()
with open(out / "vendors.json", "w", encoding="utf-8") as f:
    json.dump(vendors, f, separators=(",",":"), ensure_ascii=False)
print(f"Step 6: vendors.json written in {time.time()-t:.1f}s", flush=True)

t = time.time()
with open(out / "availability.json", "w", encoding="utf-8") as f:
    json.dump(avail, f, separators=(",",":"))
print(f"Step 7: availability.json written in {time.time()-t:.1f}s", flush=True)

Path("knowledge").mkdir(exist_ok=True)
t = time.time()
with open(out / "knowledge/chunks.json", "w", encoding="utf-8") as f:
    json.dump(chunks, f, separators=(",",":"), ensure_ascii=False)
print(f"Step 8: chunks.json written in {time.time()-t:.1f}s", flush=True)
print("DONE", flush=True)
