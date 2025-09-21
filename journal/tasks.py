from celery import shared_task
from transformers import pipeline
from keybert import KeyBERT
from .models import JournalEntry, Emotion

sentiment_model = pipeline("text-classification", model="joeddav/distilbert-base-uncased-go-emotions-student")
kw_model = KeyBERT()
classifier = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    top_k=None
)


EMOTION_CATEGORY_MAP = {
    "joy": "joy",
    "optimism": "joy",
    "love": "joy",
    "amusement": "joy",
    "excitement": "anticipation",
    "anticipation": "anticipation",
    "pride": "anticipation",
    "surprise": "surprise",
    "fear": "surprise",
    "sadness": "sadness",
    "grief": "sadness",
    "disappointment": "sadness",
    "anger": "anger",
    "disgust": "anger",
    "annoyance": "anger",
}

@shared_task
def analyze_entry(entry_id):
    entry = JournalEntry.objects.get(id=entry_id)

    results = classifier(entry.content)
    results = results[0]
    top = max(results, key=lambda x: x["score"])
    raw_label = top["label"].lower()

    mapped_label = EMOTION_CATEGORY_MAP.get(raw_label, raw_label)

    entry.detected_emotion = mapped_label
    entry.save()

    emotion_obj, _ = Emotion.objects.get_or_create(slug=mapped_label, defaults={"name": mapped_label.title()})
    entry.emotions.set([emotion_obj])

