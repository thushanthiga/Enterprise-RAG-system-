import joblib
import numpy as np
from sentence_transformers import SentenceTransformer

# Load the model
try:
    model = joblib.load("thusha_AI.pkl")
except Exception as e:
    print(f"Error loading model: {e}")
    exit(1)

print("=" * 55)
print("   THUS_AI CLASSIFIER — MODEL INSPECTION")
print("=" * 55)

# Detect model type
model_type = type(model).__name__
print(f"  Model type      : {model_type}")

# ── Head parameters ────────────────────────────────────────
if hasattr(model, 'coef_'):
    head_params = int(np.prod(model.coef_.shape)) + len(model.intercept_)
    head_type = "Sklearn LogisticRegression head"
else:
    head_params = 0
    head_type = "Unknown head"

# ── Body (SentenceTransformer) ─────────────────────────────
# Based on router_agent.py, this uses all-MiniLM-L6-v2
print(f"  Loading base model for parameter count...")
body = SentenceTransformer('all-MiniLM-L6-v2')
body_params = sum(p.numel() for p in body.parameters())

total = body_params + head_params

print(f"  Base model      : all-MiniLM-L6-v2")
print(f"  Body params     : {body_params:,}  ({body_params/1e6:.1f}M)")
print(f"  Head type       : {head_type}")
print(f"  Head params     : {head_params:,}")
print(f"  TOTAL params    : {total:,}  ({total/1e6:.1f}M)")

if hasattr(model, 'classes_'):
    print(f"  Labels          : {list(model.classes_)}")

embedding_dim = body.get_sentence_embedding_dimension()
print(f"  Embedding dim   : {embedding_dim}")

print("=" * 55)
print("\n  COMPARISON TO OTHER MODELS:")
total_m = total / 1e6 if total > 0 else None
print(f"  {'thusha_AI.pkl (yours)':<24}: {total_m:.1f}M params" if total_m else "  thusha_AI.pkl (yours)       : unknown params")
if total_m:
    print(f"  {'Qwen2.5:1.5b':<24}: 1,500.0M params   ({int(1500/total_m)}x bigger)")
    print(f"  {'Llama 3.2:1b':<24}: 1,000.0M params   ({int(1000/total_m)}x bigger)")
else:
    print(f"  {'Qwen2.5:1.5b':<24}: 1,500.0M params")
    print(f"  {'Llama 3.2:1b':<24}: 1,000.0M params")
print(f"  {'GPT-2 small':<24}:   117.0M params")
print(f"  {'BERT-base':<24}:   110.0M params")
print(f"  {'all-MiniLM-L6-v2':<24}:    22.7M params  (base of yours)")
print("=" * 55)
print("\n  KEY FACTS ABOUT YOUR MODEL:")
print("  - NOT a generative model (no text output)")
print("  - Pure classifier: input query -> label + confidence")
print("  - Runs on CPU at ~5ms per query")
print("  - No GPU needed after training")
print("  - 66x smaller than Qwen2.5:1.5b")
print("=" * 55)

# ── Quick inference test ───────────────────────────────────
print("\n  QUICK INFERENCE TEST:")
test_queries = [
    "How many candidates applied last week?",
    "What does the BRD say about eligibility?",
    "List all active recruiters for company 12",
    "What is the interview scoring policy?",
]

for q in test_queries:
    try:
        # Embed text first because the pkl is just the LogisticRegression head
        embeddings = body.encode([q])
        
        if hasattr(model, 'predict_proba'):
            proba = model.predict_proba(embeddings)[0]
            labels_list = list(model.classes_)
            idx = int(np.argmax(proba))
            label = labels_list[idx]
            conf = float(proba[idx])
        else:
            label = str(model.predict(embeddings)[0])
            conf = 1.0
        route = "sql_agent" if label == "db_search" else "doc_agent"
        if conf < 0.65:
            route = "fallback_llm"
        print(f"  [{label}] ({conf:.0%}) -> {route}")
        print(f"    Query: {q}")
    except Exception as e:
        print(f"  Error on query: {e}")

print("=" * 55)