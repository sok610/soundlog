from celery import shared_task
from transformers import pipeline, AutoTokenizer
from keybert import KeyBERT
from .models import JournalEntry

# ✅ 모델 & 토크나이저 로딩
tokenizer = AutoTokenizer.from_pretrained("j-hartmann/emotion-english-distilroberta-base")
classifier = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    top_k=None
)
kw_model = KeyBERT()

@shared_task
def analyze_entry(entry_id):
    entry = JournalEntry.objects.get(id=entry_id)
    text = entry.content

    # ✅ 토큰화 + truncate
    tokens = tokenizer(text, truncation=True, max_length=512)
    truncated_text = tokenizer.decode(tokens["input_ids"], skip_special_tokens=True)

    # ✅ 감정 분석 (pipeline에는 string만 넘김!)
    results = classifier(truncated_text)
    results = results[0]
    top = max(results, key=lambda x: x["score"])
    raw_label = top["label"].lower()

    # ✅ 키워드 추출
    keywords = [kw for kw, score in kw_model.extract_keywords(text, top_n=5)]

    entry.detected_emotion = raw_label
    entry.detected_keywords = keywords
    entry.save(update_fields=["detected_emotion", "detected_keywords"])
