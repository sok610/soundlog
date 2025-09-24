EMOTION_GENRES = {
    "joy": ["pop", "indie-pop", "dance"],
    "sadness": ["acoustic", "piano", "chill"],
    "anger": ["rock", "metal", "punk"],
    "anticipation": ["hiphop", "pop", "edm"],
    "surprise": ["electronic", "edm", "indie-pop"],
}
# Targets/min/max you can tune per emotion
EMOTION_FEATURES = {
    "joy": {"target_valence": 0.75, "min_energy": 0.5, "min_danceability": 0.5},
    "sadness": {"max_valence": 0.35, "min_acousticness": 0.6, "max_energy": 0.6},
    "anger": {"min_energy": 0.75, "min_tempo": 110, "min_danceability": 0.4},
    "anticipation": {"target_valence": 0.6, "min_energy": 0.5, "min_danceability": 0.5},
    "surprise": {"min_danceability": 0.5, "min_energy": 0.5, "max_valence": 0.9},
}
DEFAULT_GENRES = ["pop", "indie-pop", "electronic"]