import os
import json
import glob
import pandas as pd
from pathlib import Path
from tqdm import tqdm

# --- Path Configurations ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
INPUT_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "BDBV2026-Data/data/public_health_response/processed"))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output", "nlp")
FINAL_TABLE_PATH = os.path.join(OUTPUT_DIR, "nlp_result.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Dynamic Class Mapping (Zero-Shot) ---[cite: 3]
PILLAR_CLASSES = {
    "community_engagement": ["rumor management", "sensitization", "radio broadcast", "community resistance"],
    "coordination": ["meeting", "strategic planning", "resource allocation", "partner coordination"],
    "infection_prevention_controle": ["decontamination", "safe burials", "training", "ppe distribution"],
    "laboratory": ["testing", "sample transport", "equipment breakdown", "stockout"],
    "logistics": ["vehicles and transport", "medical supplies", "infrastructure", "communication"],
    "management": ["patient admission", "patient discharge", "death", "bed capacity"],
    "monitoring": ["contact tracing", "active case search", "alert investigation", "point of entry screening"],
    "protection_sexual_exploitation_abuse": ["training", "reporting", "victim support", "awareness"],
    "security": ["armed attack", "roadblock", "kidnapping", "general instability"]
}

def run_nlp_pipeline():
    """Runs Zero-Shot, Summarization, NER, and Emotion classifications over datasets."""
    
    # --- LAZY IMPORTS (Strictly scoped inside function execution) ---
    try:
        from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
    except ModuleNotFoundError as e:
        print("\n" + "="*60)
        print("❌ ERROR: Missing deep learning dependencies for NLP stage.")
        print("Please install them using: pip install transformers torch")
        print("="*60 + "\n")
        raise e

    print("🤖 Initializing NLP Models on CPU...")
    
    # 1. Zero-Shot[cite: 3]
    zero_shot_pipeline = pipeline("zero-shot-classification", model="valhalla/distilbart-mnli-12-3", device=-1)
    
    # 2. Summarization[cite: 4]
    sum_tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
    sum_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
    
    # 3. NER[cite: 5]
    ner_pipeline = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple", device=-1)
    
    # 4. Emotion[cite: 6]
    emotion_pipeline = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", device=-1)

    # Gather target operational logs[cite: 3, 5, 6]
    files = glob.glob(os.path.join(INPUT_DIR, "*_en__daily.csv"))
    if not files:
        # Fallback search if path structure shifts[cite: 3, 5, 6]
        files = [str(p) for p in Path(PROJECT_ROOT).rglob("*_en__daily.csv") if "output" not in str(p)]
        
    print(f"Found {len(files)} target files for consolidated pipeline execution.")
    master_records = []

    for file_path in files:
        filename = os.path.basename(file_path)
        df = pd.read_csv(file_path)
        
        # Enforce column constraint rules
        if df.shape[1] < 3:
            print(f"Skipping {filename}: requires at least [Geography, Date, Text] structure.")
            continue
            
        geo_col, date_col, text_col = df.columns[0], df.columns[1], df.columns[2]
        
        # Identify pillar context[cite: 3]
        current_pillar = next((p for p in PILLAR_CLASSES.keys() if p in filename), None)
        if not current_pillar:
            print(f"Skipping {filename}: unable to map target pillar template.")
            continue
            
        candidate_labels = PILLAR_CLASSES[current_pillar][cite: 3]
        print(f"\nProcessing Pillar [{current_pillar}] from file: {filename}")
        
        # Filter for rows that actually contain tracking text
        valid_df = df[df[text_col].notna() & (df[text_col].astype(str).str.strip() != "")].copy()
        
        if valid_df.empty:
            continue

        for idx, row in tqdm(valid_df.iterrows(), total=len(valid_df), desc="Analyzing entries"):
            raw_text = str(row[text_col])
            
            # --- Job 1: Zero-Shot Classification ---[cite: 3]
            try:
                zs_res = zero_shot_pipeline(raw_text[:1500], candidate_labels, multi_label=False)[cite: 3]
                zeroshot_json = json.dumps({"class": zs_res['labels'][0], "score": round(float(zs_res['scores'][0]), 4)})[cite: 3]
            except Exception as e:
                zeroshot_json = json.dumps({"error": str(e)})[cite: 3]

            # --- Job 2: Text Summarization ---[cite: 4]
            words_count = len(raw_text.split())
            if words_count < 20:[cite: 4]
                summary_json = json.dumps({"summary": raw_text})[cite: 4]
            else:
                try:
                    max_len = min(60, max(20, int(words_count * 0.6)))[cite: 4]
                    min_len = min(10, max_len - 5)[cite: 4]
                    inputs = sum_tokenizer(raw_text[:2000], return_tensors="pt", max_length=1024, truncation=True)[cite: 4]
                    summary_ids = sum_model.generate(inputs["input_ids"], max_length=max_len, min_length=min_len, num_beams=2, early_stopping=True)[cite: 4]
                    summary_text = sum_tokenizer.decode(summary_ids[0], skip_special_tokens=True)[cite: 4]
                    summary_json = json.dumps({"summary": summary_text})[cite: 4]
                except Exception as e:
                    summary_json = json.dumps({"error": str(e)})[cite: 4]

            # --- Job 3: Named Entity Recognition (NER) ---[cite: 5]
            try:
                entities = ner_pipeline(raw_text[:1500])[cite: 5]
                formatted_entities = [{"type": e['entity_group'], "value": e['word'], "score": round(float(e['score']), 4)} for e in entities][cite: 5]
                ner_json = json.dumps(formatted_entities)[cite: 5]
            except Exception as e:
                ner_json = json.dumps([{"error": str(e)}])[cite: 5]

            # --- Job 4: Emotion Extraction ---[cite: 6]
            try:
                em_res = emotion_pipeline(raw_text[:1500])[cite: 6]
                emotion_json = json.dumps({"label": em_res[0]['label'], "score": round(float(em_res[0]['score']), 4)})[cite: 6]
            except Exception as e:
                emotion_json = json.dumps({"error": str(e)})[cite: 6]

            # Append to master collector array
            master_records.append({
                "health_zone": str(row[geo_col]).strip().replace(r"[\[\]'\" ]", ""),
                "date": pd.to_datetime(row[date_col]).strftime("%Y-%m-%d"),
                "pillar": current_pillar,
                "source_file": filename,
                "raw_text": raw_text,
                "zeroshot_json": zeroshot_json,
                "summary_json": summary_json,
                "ner_json": ner_json,
                "emotion_json": emotion_json
            })

    # Save to final consolidated relational table
    if master_records:
        nlp_result_df = pd.DataFrame(master_records)
        nlp_result_df.to_csv(FINAL_TABLE_PATH, index=False)
        print(f"\nSuccess! Table [nlp_result] successfully compiled at: {FINAL_TABLE_PATH}")
        return nlp_result_df
    else:
        print("⚠️ Processing finished, but no valid records were produced.")
        return pd.DataFrame()

if __name__ == "__main__":
    run_nlp_pipeline()
