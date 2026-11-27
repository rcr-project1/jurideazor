# Kaggle Notebook: Build E5 FAISS index with metadata prefix
# ============================================================
# 1. Upload chunks.json as a Kaggle Dataset (e.g. "jurideazor-chunks")
# 2. Create a new Kaggle Notebook, enable GPU (Settings → Accelerator → GPU T4)
# 3. Copy-paste this into cells and run
#
# Output: download faiss_e5.index, embeddings.npy, faiss_ids.json
#         from /kaggle/working/ and place them in data/search/

# --- Cell 1: Install ---
# !pip install -q sentence-transformers faiss-cpu

# --- Cell 2: Build E5 index ---
import json
import time
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from pathlib import Path

# Adjust this path to match your Kaggle dataset name
CHUNKS_PATH = "/kaggle/input/jurideazor-chunks/chunks.json"
OUT = Path("/kaggle/working")

chunks = json.loads(Path(CHUNKS_PATH).read_text(encoding="utf-8"))
print(f"Loaded {len(chunks)} chunks")

# E5 embeddings with metadata prefix (must match build_index.py)
model = SentenceTransformer("intfloat/multilingual-e5-base")
texts = [
    f"passage: [{c['source_file'].split('/')[-1].replace('.txt','')}] {c['content']}"
    for c in chunks
]

print(f"Sample text[:120]: {texts[0][:120]}")

t0 = time.time()
embeddings = model.encode(
    texts,
    batch_size=64,
    show_progress_bar=True,
    normalize_embeddings=True,
)
print(f"Encoding: {time.time() - t0:.1f}s")

# Build FAISS index
dim = embeddings.shape[1]
index = faiss.IndexFlatIP(dim)
index.add(embeddings.astype(np.float32))
print(f"FAISS: {index.ntotal} vectors, dim={dim}")

# Save
faiss.write_index(index, str(OUT / "faiss_e5.index"))
np.save(str(OUT / "embeddings.npy"), embeddings)

ids = [c["chunk_id"] for c in chunks]
(OUT / "faiss_ids.json").write_text(
    json.dumps(ids, ensure_ascii=False), encoding="utf-8"
)

print(f"\nDone — download from /kaggle/working/:")
print(f"  faiss_e5.index  ({(OUT / 'faiss_e5.index').stat().st_size / 1024 / 1024:.1f} MB)")
print(f"  embeddings.npy  ({(OUT / 'embeddings.npy').stat().st_size / 1024 / 1024:.1f} MB)")
print(f"  faiss_ids.json  ({(OUT / 'faiss_ids.json').stat().st_size / 1024:.0f} KB)")
