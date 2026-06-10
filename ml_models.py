"""
VoiceUp Machine Learning Module
================================
1. Spam Detector — detects spam/fake suggestions
2. Recommendation Engine — suggests similar suggestions to vote on
3. Priority Predictor — predicts priority based on text
4. Auto-trainer — trains on your own data automatically
"""

import os
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

# ─── Model file paths ────────────────────────────────────────────────────────
MODEL_DIR       = os.path.join(os.path.dirname(__file__), 'ml_models')
SPAM_MODEL_PATH = os.path.join(MODEL_DIR, 'spam_model.pkl')
PRIO_MODEL_PATH = os.path.join(MODEL_DIR, 'priority_model.pkl')
VECT_PATH       = os.path.join(MODEL_DIR, 'vectorizer.pkl')

os.makedirs(MODEL_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════
# 1. SPAM DETECTOR
# ═══════════════════════════════════════════════════════════════════

# Training data — spam vs legitimate suggestions
SPAM_TRAINING_DATA = [
    # Spam examples
    ("buy cheap products click here", 1),
    ("win free money now", 1),
    ("click this link for prizes", 1),
    ("make money fast online", 1),
    ("free gift card winner", 1),
    ("lorem ipsum dolor sit amet", 1),
    ("asdfghjkl zxcvbnm qwerty", 1),
    ("aaaaaaaaaa bbbbbbbb cccc", 1),
    ("test test test test test", 1),
    ("this is just a test nothing", 1),
    ("abcdefghij 12345 nothing", 1),
    ("hello world spam content", 1),

    # Legitimate examples
    ("the library should extend its opening hours to midnight", 0),
    ("we need more computers in the computer lab", 0),
    ("the cafeteria food quality needs improvement", 0),
    ("sports facilities need to be upgraded", 0),
    ("please fix the broken lights in corridor B", 0),
    ("students need faster wifi in the dormitories", 0),
    ("the chemistry lab needs new equipment", 0),
    ("we need more buses for transportation", 0),
    ("the hostel bathrooms need renovation", 0),
    ("classroom projectors are outdated and need replacement", 0),
    ("the administration should respond faster to student queries", 0),
    ("we need better mental health support services", 0),
    ("the parking area is too small for students", 0),
    ("lecture halls need better ventilation and air conditioning", 0),
    ("more scholarships should be made available to students", 0),
    ("the student portal is slow and needs upgrading", 0),
    ("we need 24 hour security in the campus", 0),
    ("the waste management system needs improvement", 0),
    ("better study areas needed in the library", 0),
    ("the canteen should offer healthier food options", 0),
]

def train_spam_model():
    """Train the spam detection model."""
    texts  = [d[0] for d in SPAM_TRAINING_DATA]
    labels = [d[1] for d in SPAM_TRAINING_DATA]

    model = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1,2), max_features=5000)),
        ('clf',   MultinomialNB(alpha=0.1))
    ])
    model.fit(texts, labels)

    with open(SPAM_MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    print('✅ Spam model trained and saved!')
    return model

def load_spam_model():
    """Load spam model or train if not exists."""
    if os.path.exists(SPAM_MODEL_PATH):
        with open(SPAM_MODEL_PATH, 'rb') as f:
            return pickle.load(f)
    return train_spam_model()

def is_spam(title, description):
    """Check if a suggestion is spam. Returns (is_spam, confidence)."""
    try:
        model = load_spam_model()
        text  = f"{title} {description}"
        proba = model.predict_proba([text])[0]
        spam_prob = proba[1]
        return spam_prob > 0.7, round(float(spam_prob) * 100)
    except Exception as e:
        print(f'Spam check error: {e}')
        return False, 0

def retrain_spam_model(db_suggestions):
    """Retrain spam model with real data from database."""
    try:
        training_data = list(SPAM_TRAINING_DATA)
        for s in db_suggestions:
            text = f"{s.get('title','')} {s.get('description','')}"
            # Mark rejected suggestions as potential spam
            label = 1 if s.get('status') == 'rejected' else 0
            training_data.append((text, label))

        texts  = [d[0] for d in training_data]
        labels = [d[1] for d in training_data]

        model = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1,2), max_features=5000)),
            ('clf',   MultinomialNB(alpha=0.1))
        ])
        model.fit(texts, labels)
        with open(SPAM_MODEL_PATH, 'wb') as f:
            pickle.dump(model, f)
        print(f'✅ Spam model retrained with {len(training_data)} samples!')
        return True
    except Exception as e:
        print(f'Retrain error: {e}')
        return False


# ═══════════════════════════════════════════════════════════════════
# 2. RECOMMENDATION ENGINE
# ═══════════════════════════════════════════════════════════════════

def get_recommendations(title, description, all_suggestions, top_n=3):
    """Find similar suggestions using TF-IDF cosine similarity."""
    try:
        if not all_suggestions:
            return []

        query = f"{title} {description}"
        corpus = [f"{s.get('title','')} {s.get('description','')}"
                  for s in all_suggestions]
        corpus.append(query)

        vectorizer = TfidfVectorizer(ngram_range=(1,2), max_features=3000, stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(corpus)

        # Query is last item
        query_vec    = tfidf_matrix[-1]
        corpus_vecs  = tfidf_matrix[:-1]

        similarities = cosine_similarity(query_vec, corpus_vecs).flatten()

        # Get top similar suggestions
        top_indices  = similarities.argsort()[::-1][:top_n]
        results = []
        for idx in top_indices:
            sim_score = float(similarities[idx])
            if sim_score > 0.15:  # Minimum similarity threshold
                s = all_suggestions[idx]
                results.append({
                    'suggestion_id': s.get('suggestion_id'),
                    'title':         s.get('title'),
                    'category':      s.get('category'),
                    'vote_count':    s.get('vote_count', 0),
                    'status':        s.get('status'),
                    'similarity':    round(sim_score * 100)
                })
        return results
    except Exception as e:
        print(f'Recommendation error: {e}')
        return []


# ═══════════════════════════════════════════════════════════════════
# 3. PRIORITY PREDICTOR
# ═══════════════════════════════════════════════════════════════════

# Training data for priority prediction
PRIORITY_TRAINING_DATA = [
    ("emergency fire hazard broken electrical wires dangerous", "urgent"),
    ("safety risk flooding water leaking roof ceiling", "urgent"),
    ("medical emergency first aid health risk injury", "urgent"),
    ("immediate security threat violence danger", "urgent"),
    ("broken equipment not working important exam", "high"),
    ("internet wifi not working affecting studies", "high"),
    ("exam results delayed important grades academic", "high"),
    ("transport bus not available students stranded", "high"),
    ("library books missing important resources", "medium"),
    ("cafeteria food quality improvement needed", "medium"),
    ("sports facility renovation upgrade request", "medium"),
    ("classroom painting decoration improvement", "low"),
    ("suggest adding more flowers trees beautification", "low"),
    ("minor suggestion about notice board design", "low"),
    ("would be nice to have better furniture someday", "low"),
    ("urgent fix needed in the laboratory immediately", "urgent"),
    ("critical system down affecting all students", "urgent"),
    ("improve the quality of meals in dining hall", "medium"),
    ("need new computers in lab old ones are slow", "high"),
    ("request for new sports equipment basketball", "medium"),
]

def train_priority_model():
    """Train the priority prediction model."""
    texts  = [d[0] for d in PRIORITY_TRAINING_DATA]
    labels = [d[1] for d in PRIORITY_TRAINING_DATA]

    model = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1,2), max_features=3000)),
        ('clf',   LogisticRegression(max_iter=1000, C=1.0))
    ])
    model.fit(texts, labels)

    with open(PRIO_MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    print('✅ Priority model trained and saved!')
    return model

def load_priority_model():
    """Load priority model or train if not exists."""
    if os.path.exists(PRIO_MODEL_PATH):
        with open(PRIO_MODEL_PATH, 'rb') as f:
            return pickle.load(f)
    return train_priority_model()

def predict_priority(title, description):
    """Predict priority for a suggestion. Returns (priority, confidence)."""
    try:
        model = load_priority_model()
        text  = f"{title} {description}"
        pred  = model.predict([text])[0]
        proba = model.predict_proba([text])[0]
        conf  = round(float(max(proba)) * 100)
        return pred, conf
    except Exception as e:
        print(f'Priority prediction error: {e}')
        return 'medium', 50


# ═══════════════════════════════════════════════════════════════════
# 4. MODEL STATS
# ═══════════════════════════════════════════════════════════════════

def get_model_stats():
    """Get stats about trained models."""
    stats = {
        'spam_model':     os.path.exists(SPAM_MODEL_PATH),
        'priority_model': os.path.exists(PRIO_MODEL_PATH),
        'spam_samples':   len(SPAM_TRAINING_DATA),
        'priority_samples': len(PRIORITY_TRAINING_DATA),
    }
    return stats


# Train models on import if not already trained
if not os.path.exists(SPAM_MODEL_PATH):
    train_spam_model()
if not os.path.exists(PRIO_MODEL_PATH):
    train_priority_model()
