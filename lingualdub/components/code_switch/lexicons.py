"""
Shared lexicons for code-switch detection — single source of truth.

Previously Luganda/English word lists were duplicated between dummy.py (small)
and heuristic.py (large) with drift (e.g. 'oli' etc). This module centralises
the base lexicons; Dummy uses the small map, Heuristic uses the full sets.
"""

# Base Luganda high-frequency words
LUGANDA_LEXICON = {
    "oli", "otya", "nnyabo", "sebo", "webale", "ffe", "gwe", "nze",
    "bwe", "nga", "ku", "mu", "ne", "era", "kuba", "kola", "ebitabo",
    "abaana", "leero", "enkuba", "amatooke", "ssente", "omuntu", "bantu",
    "okukola", "okulaba", "twebaza", "tusanyuse", "emirimu", "bulungi",
    "ki", "kati", "lwa", "lwaki", "bangi", "bano", "ekintu", "ebintu",
    "abantu", "omulimu", "ensi", "katonda", "omukazi", "omusajja",
    "nsaba", "ontereze", "eno", "wano", "eri", "wali", "awo", "naye",
    "nnyo", "okulaba",
}

# Base English high-frequency words
ENGLISH_LEXICON = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
    "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
    "this", "but", "his", "by", "from", "they", "we", "say", "her",
    "she", "or", "an", "will", "my", "one", "all", "would", "there",
    "their", "what", "so", "up", "out", "if", "about", "who", "get",
    "which", "go", "me", "when", "make", "can", "like", "time", "no",
    "just", "him", "know", "take", "people", "into", "year", "your",
    "good", "some", "could", "them", "see", "other", "than", "then",
    "now", "look", "only", "come", "its", "over", "think", "also",
    "back", "after", "use", "two", "how", "our", "work", "first",
    "well", "way", "even", "new", "want", "because", "any", "these",
    "give", "day", "most", "us", "morning", "report", "project",
    "meeting", "send", "please", "today", "tomorrow", "boss", "manager",
    "system", "program", "file", "computer", "phone", "network", "call",
    "hello", "hi", "good", "morning", "report", "today", "can", "you",
    "send", "me", "project", "meeting", "was", "completely", "successful",
}

# Dummy word map derived from lexicons for deterministic testing (small subset preserved for backward compat)
DEFAULT_WORD_LANGUAGES: dict[str, str] = {}
for w in LUGANDA_LEXICON:
    if w in {"oli", "otya", "nnyabo", "sebo", "webale", "nnyo", "tusanyuse", "okulaba", "leero", "abaana", "ebitabo", "nsaba", "ontereze", "eno"}:
        DEFAULT_WORD_LANGUAGES[w] = "lug"
for w in ENGLISH_LEXICON:
    if w in {"hello", "hi", "good", "morning", "report", "today", "can", "you", "send", "me", "project", "meeting", "the", "was", "completely", "successful"}:
        DEFAULT_WORD_LANGUAGES[w] = "eng"
