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
                    'id':            s.get('id'),
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
    # ── URGENT: immediate danger, safety, health, security ──
    ("emergency fire hazard broken electrical wires dangerous", "urgent"),
    ("safety risk flooding water leaking roof ceiling", "urgent"),
    ("medical emergency first aid health risk injury", "urgent"),
    ("immediate security threat violence danger", "urgent"),
    ("urgent fix needed in the laboratory immediately", "urgent"),
    ("critical system down affecting all students", "urgent"),
    ("gas leak smell chemistry lab dangerous fumes", "urgent"),
    ("broken stairs railing students falling risk injury", "urgent"),
    ("exposed live wire near hostel block dangerous", "urgent"),
    ("fight breaking out between students need security now", "urgent"),
    ("student collapsed needs ambulance immediately", "urgent"),
    ("fire alarm not working in hostel building safety", "urgent"),
    ("water contamination outbreak students getting sick", "urgent"),
    ("building structural crack ceiling about to collapse", "urgent"),
    ("armed intruder seen on campus alert security", "urgent"),
    ("food poisoning multiple students affected cafeteria", "urgent"),
    ("elevator stuck students trapped inside emergency", "urgent"),
    ("chemical spill in laboratory needs immediate cleanup", "urgent"),

    # ── HIGH: significant impact on studies/operations ──
    ("broken equipment not working important exam", "high"),
    ("internet wifi not working affecting studies", "high"),
    ("exam results delayed important grades academic", "high"),
    ("transport bus not available students stranded", "high"),
    ("need new computers in lab old ones are slow", "high"),
    ("lecturer not showing up for classes for weeks", "high"),
    ("exam timetable clashing two papers same time", "high"),
    ("library closed during exam period need access", "high"),
    ("hostel water supply cut off for days", "high"),
    ("fee payment portal not working before deadline", "high"),
    ("projector broken in main lecture hall", "high"),
    ("course registration system crashed during deadline", "high"),
    ("no electricity in hostels during exam week", "high"),
    ("missing marks in continuous assessment test results", "high"),
    ("graduation list error my name is missing", "high"),
    ("scholarship application deadline system not accepting", "high"),
    ("printer in computer lab not working before submission", "high"),

    # ── MEDIUM: notable quality-of-life improvement, workable ──
    ("library books missing important resources", "medium"),
    ("cafeteria food quality improvement needed", "medium"),
    ("sports facility renovation upgrade request", "medium"),
    ("improve the quality of meals in dining hall", "medium"),
    ("request for new sports equipment basketball", "medium"),
    ("more reading materials needed in library", "medium"),
    ("longer study hours requested for library", "medium"),
    ("improve hostel cleaning services more often", "medium"),
    ("request more computer lab opening hours", "medium"),
    ("add more seating in cafeteria during lunch", "medium"),
    ("improve internet speed during peak hours", "medium"),
    ("request counseling services more available", "medium"),
    ("more parking space needed near main building", "medium"),
    ("improve communication from administration office", "medium"),
    ("request extension of library opening hours weekends", "medium"),
    ("add more dustbins around the compound", "medium"),
    ("request better lighting in evening study areas", "medium"),

    # ── LOW: nice-to-have, cosmetic, minor ──
    ("classroom painting decoration improvement", "low"),
    ("suggest adding more flowers trees beautification", "low"),
    ("minor suggestion about notice board design", "low"),
    ("would be nice to have better furniture someday", "low"),
    ("add more plants around the courtyard", "low"),
    ("suggest changing the school logo colors", "low"),
    ("request for music during lunch break", "low"),
    ("would like more decorations during events", "low"),
    ("suggest adding a suggestion box near the office", "low"),
    ("minor change to website font style", "low"),
    ("request for better signage around campus", "low"),
    ("suggest a new color scheme for notice boards", "low"),
    ("would be nice to have benches under trees", "low"),
    ("minor request for more clocks around buildings", "low"),
    ("suggest improving the school website homepage design", "low"),
    ("would be nice to add more artwork in hallways", "low"),
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
        'spam_model':       os.path.exists(SPAM_MODEL_PATH),
        'priority_model':   os.path.exists(PRIO_MODEL_PATH),
        'resolution_model': os.path.exists(RESOLUTION_MODEL_PATH),
        'spam_samples':     len(SPAM_TRAINING_DATA),
        'priority_samples': len(PRIORITY_TRAINING_DATA),
    }
    return stats


# ═══════════════════════════════════════════════════════════════════
# 5. RESOLUTION TIME PREDICTOR
# Predicts how many days a suggestion will take to be resolved,
# based on category, priority, text features, and historical data.
# Falls back to synthetic training data when real history is sparse.
# ═══════════════════════════════════════════════════════════════════
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder

RESOLUTION_MODEL_PATH = os.path.join(MODEL_DIR, 'resolution_model.pkl')

# Category and priority encoders (consistent ordering)
CATEGORIES  = ['academics', 'facilities', 'welfare', 'technology',
                'administration', 'sports', 'other']
PRIORITIES  = ['low', 'medium', 'high', 'urgent']
PRIORITY_MAP = {'low': 1, 'medium': 2, 'high': 3, 'urgent': 4}

# Synthetic baseline training data (category, priority, days_to_resolve)
# Based on realistic Kenyan university administration patterns
RESOLUTION_TRAINING_DATA = [
    # urgent — resolved very fast
    ('facilities',     'urgent',  1), ('welfare',      'urgent',  1),
    ('technology',     'urgent',  2), ('academics',    'urgent',  2),
    ('administration', 'urgent',  1), ('sports',       'urgent',  3),
    ('other',          'urgent',  2),
    # high
    ('facilities',     'high',    4), ('welfare',      'high',    3),
    ('technology',     'high',    5), ('academics',    'high',    4),
    ('administration', 'high',    6), ('sports',       'high',    5),
    ('other',          'high',    5),
    # medium
    ('facilities',     'medium',  9), ('welfare',      'medium',  7),
    ('technology',     'medium', 10), ('academics',    'medium',  8),
    ('administration', 'medium', 12), ('sports',       'medium', 10),
    ('other',          'medium',  9),
    # low — slowest resolution
    ('facilities',     'low',    18), ('welfare',      'low',    14),
    ('technology',     'low',    16), ('academics',    'low',    15),
    ('administration', 'low',    20), ('sports',       'low',    18),
    ('other',          'low',    17),
    # Extra variance samples to help the model generalise
    ('academics',    'high',   3),  ('academics',    'medium', 10),
    ('facilities',   'medium', 8),  ('welfare',      'high',    4),
    ('technology',   'urgent', 1),  ('administration','medium', 11),
]


def _extract_resolution_features(category, priority, title='', description=''):
    """Convert inputs to numeric feature vector."""
    cat_encoded  = CATEGORIES.index(category) if category in CATEGORIES else len(CATEGORIES) - 1
    prio_encoded = PRIORITY_MAP.get(priority, 2)
    title_len    = len(title or '')
    desc_len     = len(description or '')
    word_count   = len((title + ' ' + description).split())
    return [cat_encoded, prio_encoded, title_len, desc_len, word_count]


def train_resolution_model(historical_data=None):
    """Train resolution time predictor.
    historical_data: list of dicts with keys category, priority, days_to_resolve
    Falls back to synthetic data if historical is insufficient."""
    X, y = [], []

    # Add real historical data first (higher weight via repetition)
    if historical_data:
        for d in historical_data:
            try:
                feats = _extract_resolution_features(
                    d.get('category', 'other'),
                    d.get('priority', 'medium')
                )
                days = float(d.get('days_to_resolve', 7))
                if 1 <= days <= 90:   # ignore outliers
                    X.append(feats)
                    y.append(days)
                    # Repeat real data 3x so it dominates over synthetic
                    X.append(feats); y.append(days)
                    X.append(feats); y.append(days)
            except Exception:
                pass

    # Always include synthetic baseline
    for cat, prio, days in RESOLUTION_TRAINING_DATA:
        X.append(_extract_resolution_features(cat, prio))
        y.append(float(days))

    model = RandomForestRegressor(
        n_estimators=100, max_depth=6,
        random_state=42, min_samples_leaf=2
    )
    model.fit(X, y)

    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(RESOLUTION_MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    print(f'✅ Resolution model trained with {len(X)} samples')
    return model


def _load_resolution_model():
    if os.path.exists(RESOLUTION_MODEL_PATH):
        with open(RESOLUTION_MODEL_PATH, 'rb') as f:
            return pickle.load(f)
    return train_resolution_model()


def predict_resolution_time(category, priority, title='', description=''):
    """Predict how many days until this suggestion is likely resolved.
    Returns (predicted_days: int, confidence: str, label: str)"""
    try:
        model  = _load_resolution_model()
        feats  = _extract_resolution_features(category, priority, title, description)
        raw    = model.predict([feats])[0]
        days   = max(1, round(raw))

        # Confidence based on how well we know this category/priority combo
        prio_encoded = PRIORITY_MAP.get(priority, 2)
        # Trees give per-tree predictions; use spread as uncertainty proxy
        tree_preds   = np.array([t.predict([feats])[0] for t in model.estimators_])
        std          = np.std(tree_preds)
        if std < 2:
            confidence = 'High'
        elif std < 5:
            confidence = 'Moderate'
        else:
            confidence = 'Low'

        # Human-friendly label
        if days <= 3:
            label = 'Very Fast ⚡'
        elif days <= 7:
            label = 'Fast 🚀'
        elif days <= 14:
            label = 'Normal ⏱️'
        elif days <= 21:
            label = 'Slow 🐢'
        else:
            label = 'Long Wait ⌛'

        return days, confidence, label
    except Exception as e:
        print(f'Resolution prediction error: {e}')
        # Safe fallback based on SLA days
        fallback = {'urgent': 1, 'high': 3, 'medium': 7, 'low': 14}
        days = fallback.get(priority, 7)
        return days, 'Low', 'Normal ⏱️'


# Train models on import if not already trained
if not os.path.exists(SPAM_MODEL_PATH):
    train_spam_model()
if not os.path.exists(PRIO_MODEL_PATH):
    train_priority_model()
if not os.path.exists(RESOLUTION_MODEL_PATH):
    train_resolution_model()


# ═══════════════════════════════════════════════════════════════════
# 6. TOPIC CLUSTERING
# Groups suggestions into themes using K-Means on TF-IDF vectors.
# Automatically names each theme from its top keywords.
# Returns clusters sorted by size (most discussed first).
# ═══════════════════════════════════════════════════════════════════
from sklearn.cluster import KMeans

# Words that don't help identify themes — filtered out
CLUSTER_STOP_WORDS = [
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
    'for', 'of', 'with', 'by', 'from', 'is', 'was', 'are', 'were',
    'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that',
    'these', 'those', 'it', 'its', 'we', 'our', 'us', 'i', 'my', 'me',
    'you', 'your', 'they', 'their', 'there', 'here', 'how', 'what',
    'when', 'where', 'who', 'which', 'all', 'more', 'also', 'not',
    'very', 'so', 'if', 'as', 'about', 'need', 'needs', 'please',
    'university', 'school', 'students', 'student', 'administration',
    'suggest', 'suggestion', 'request', 'would', 'like', 'think',
    'feel', 'believe', 'want', 'make', 'get', 'give', 'new', 'better',
]

# Emoji icons per theme keyword — makes the UI pop
THEME_ICONS = {
    'library': '📚', 'books': '📚', 'reading': '📚',
    'wifi': '📶', 'internet': '📶', 'network': '📶', 'connection': '📶',
    'food': '🍽️', 'cafeteria': '🍽️', 'meals': '🍽️', 'dining': '🍽️',
    'transport': '🚌', 'bus': '🚌', 'commute': '🚌',
    'toilet': '🚽', 'sanitation': '🚽', 'hygiene': '🚽', 'bathroom': '🚽',
    'lab': '🔬', 'laboratory': '🔬', 'computer': '💻', 'equipment': '🔬',
    'sports': '⚽', 'field': '⚽', 'gym': '⚽', 'recreation': '⚽',
    'fees': '💰', 'payment': '💰', 'money': '💰', 'finance': '💰',
    'safety': '🔒', 'security': '🔒', 'crime': '🔒', 'theft': '🔒',
    'hostel': '🏠', 'accommodation': '🏠', 'housing': '🏠', 'dorm': '🏠',
    'exam': '📝', 'exams': '📝', 'results': '📝', 'marks': '📝',
    'lecture': '🎓', 'class': '🎓', 'lecturer': '🎓', 'teaching': '🎓',
    'health': '🏥', 'clinic': '🏥', 'medical': '🏥', 'sick': '🏥',
    'water': '💧', 'electricity': '⚡', 'power': '⚡', 'lighting': '💡',
    'parking': '🚗', 'chairs': '🪑', 'furniture': '🪑', 'seats': '🪑',
}

def _get_theme_icon(keywords):
    """Find the best emoji for a cluster based on its keywords."""
    for kw in keywords:
        for term, icon in THEME_ICONS.items():
            if term in kw.lower():
                return icon
    return '💬'


def cluster_suggestions(suggestions, n_clusters=None):
    """
    Cluster suggestions into themes using K-Means + TF-IDF.

    suggestions: list of dicts with keys: id, suggestion_id, title,
                 description, category, priority, status, vote_count,
                 fullname, created_at
    n_clusters: number of themes (auto-selected if None)

    Returns list of cluster dicts sorted by size, each with:
        theme_name, icon, keywords, count, suggestions (top 3)
    """
    if not suggestions or len(suggestions) < 3:
        return []

    # Combine title + description for richer signal
    texts = []
    for s in suggestions:
        text = f"{s.get('title','')} {s.get('title','')} {s.get('description','')}"
        texts.append(text.lower())

    # Auto-select number of clusters
    n = len(suggestions)
    if n_clusters is None:
        if n < 10:
            k = 2
        elif n < 25:
            k = 3
        elif n < 60:
            k = 4
        elif n < 120:
            k = 5
        else:
            k = 6
    else:
        k = min(n_clusters, max(2, n // 3))

    try:
        # TF-IDF vectorization
        vectorizer = TfidfVectorizer(
            max_features=300,
            stop_words=CLUSTER_STOP_WORDS,
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True
        )
        X = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()

        # K-Means clustering
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10, max_iter=300)
        labels = kmeans.fit_predict(X)

        # Extract top keywords per cluster from cluster centroids
        clusters = []
        for cluster_id in range(k):
            # Get indices of suggestions in this cluster
            member_indices = [i for i, l in enumerate(labels) if l == cluster_id]
            if not member_indices:
                continue

            # Top keywords from centroid
            centroid    = kmeans.cluster_centers_[cluster_id]
            top_indices = centroid.argsort()[-8:][::-1]
            keywords    = [feature_names[i] for i in top_indices
                          if len(feature_names[i]) > 3][:5]

            # Theme name: title-case the top keyword(s)
            if keywords:
                theme_name = ' & '.join(k.title() for k in keywords[:2])
            else:
                theme_name = f'Theme {cluster_id + 1}'

            # Get icon
            icon = _get_theme_icon(keywords)

            # Top suggestions in this cluster (by vote count)
            members = [suggestions[i] for i in member_indices]
            members_sorted = sorted(members, key=lambda s: s.get('vote_count', 0), reverse=True)

            # Dominant category
            cats = [s.get('category', 'other') for s in members]
            dominant_cat = max(set(cats), key=cats.count)

            # Dominant sentiment (if available)
            statuses = [s.get('status', 'pending') for s in members]
            dominant_status = max(set(statuses), key=statuses.count)

            clusters.append({
                'cluster_id':      cluster_id,
                'theme_name':      theme_name,
                'icon':            icon,
                'keywords':        keywords,
                'count':           len(member_indices),
                'category':        dominant_cat,
                'dominant_status': dominant_status,
                'suggestions':     [
                    {
                        'id':            s.get('id'),
                        'suggestion_id': s.get('suggestion_id'),
                        'title':         s.get('title','')[:70],
                        'vote_count':    s.get('vote_count', 0),
                        'status':        s.get('status', 'pending'),
                        'priority':      s.get('priority', 'medium'),
                    }
                    for s in members_sorted[:3]
                ]
            })

        # Sort by size — most discussed first
        clusters.sort(key=lambda c: c['count'], reverse=True)
        return clusters

    except Exception as e:
        print(f'Clustering error: {e}')
        return []


