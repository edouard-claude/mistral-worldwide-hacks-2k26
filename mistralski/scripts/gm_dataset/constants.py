"""Constants extracted from game YAML configs for dataset generation."""

from typing import Final

# --- Country codes (from countries.yaml) ---
COUNTRY_CODES: Final[list[str]] = [
    "FR", "US", "RU", "CN", "BR", "DE", "GB", "JP",
    "EG", "SN", "IN", "UA", "AR", "NG", "AU",
]

COUNTRY_NAMES: Final[dict[str, str]] = {
    "FR": "France",
    "US": "États-Unis",
    "RU": "Russie",
    "CN": "Chine",
    "BR": "Brésil",
    "DE": "Allemagne",
    "GB": "Royaume-Uni",
    "JP": "Japon",
    "EG": "Égypte",
    "SN": "Sénégal",
    "IN": "Inde",
    "UA": "Ukraine",
    "AR": "Argentine",
    "NG": "Nigeria",
    "AU": "Australie",
}

# --- Action IDs (from game.yaml) ---
ACTION_IDS: Final[list[str]] = [
    # Désinformation
    "fake_news", "photo_choquante", "etude_commanditee",
    "vieux_scandale", "sondage_favorable",
    # Manipulation
    "bouc_emissaire", "distraction_massive", "polemique",
    "hashtag", "creer_martyr",
    # Censure
    "couper_internet", "dementi", "faire_disparaitre",
    "loi_exception", "museler_leader",
    # Déstabilisation
    "guerre_commerciale", "urgence_nationale", "cyberattaque",
    "provoquer_krach", "referendum_truque",
]

ACTION_LABELS: Final[dict[str, str]] = {
    "fake_news": "Injecter Fake News",
    "photo_choquante": "Sortir Photo Choquante",
    "etude_commanditee": "Commanditer une Étude",
    "vieux_scandale": "Ressortir Vieux Scandale",
    "sondage_favorable": "Publier Sondage Favorable",
    "bouc_emissaire": "Créer Bouc Émissaire",
    "distraction_massive": "Lancer Distraction Massive",
    "polemique": "Déclencher Polémique",
    "hashtag": "Lancer Hashtag",
    "creer_martyr": "Créer un Martyr",
    "couper_internet": "Couper Internet",
    "dementi": "Lancer Démenti",
    "faire_disparaitre": "Faire Disparaître",
    "loi_exception": "Invoquer Loi d'Exception",
    "museler_leader": "Museler un Leader",
    "guerre_commerciale": "Guerre Commerciale",
    "urgence_nationale": "Urgence Nationale",
    "cyberattaque": "Cyberattaque",
    "provoquer_krach": "Provoquer un Krach",
    "referendum_truque": "Référendum Truqué",
}

ACTION_CATEGORIES: Final[dict[str, str]] = {
    "fake_news": "desinformation",
    "photo_choquante": "desinformation",
    "etude_commanditee": "desinformation",
    "vieux_scandale": "desinformation",
    "sondage_favorable": "desinformation",
    "bouc_emissaire": "manipulation",
    "distraction_massive": "manipulation",
    "polemique": "manipulation",
    "hashtag": "manipulation",
    "creer_martyr": "manipulation",
    "couper_internet": "censure",
    "dementi": "censure",
    "faire_disparaitre": "censure",
    "loi_exception": "censure",
    "museler_leader": "censure",
    "guerre_commerciale": "destabilisation",
    "urgence_nationale": "destabilisation",
    "cyberattaque": "destabilisation",
    "provoquer_krach": "destabilisation",
    "referendum_truque": "destabilisation",
}

ACTION_COSTS: Final[dict[str, int]] = {
    "fake_news": 8, "photo_choquante": 10, "etude_commanditee": 15,
    "vieux_scandale": 6, "sondage_favorable": 5,
    "bouc_emissaire": 12, "distraction_massive": 10, "polemique": 7,
    "hashtag": 4, "creer_martyr": 20,
    "couper_internet": 18, "dementi": 5, "faire_disparaitre": 25,
    "loi_exception": 15, "museler_leader": 14,
    "guerre_commerciale": 16, "urgence_nationale": 20, "cyberattaque": 18,
    "provoquer_krach": 22, "referendum_truque": 25,
}

ACTION_EFFECTS: Final[dict[str, dict[str, float]]] = {
    "fake_news": {"credibilite": 10, "complotisme": 5},
    "photo_choquante": {"rage": 15, "credibilite": 5},
    "etude_commanditee": {"credibilite": 12, "esperance_democratique": -5},
    "vieux_scandale": {"rage": 10, "complotisme": 3},
    "sondage_favorable": {"credibilite": 8, "esperance_democratique": -3},
    "bouc_emissaire": {"rage": 20, "esperance_democratique": -8},
    "distraction_massive": {"credibilite": 5, "rage": -10},
    "polemique": {"rage": 12, "complotisme": 8},
    "hashtag": {"rage": 5, "credibilite": 3},
    "creer_martyr": {"rage": 25, "esperance_democratique": -15, "complotisme": 10},
    "couper_internet": {"rage": 15, "credibilite": -10, "esperance_democratique": -12},
    "dementi": {"complotisme": 8, "credibilite": 3},
    "faire_disparaitre": {"rage": 10, "esperance_democratique": -20, "complotisme": 15},
    "loi_exception": {"esperance_democratique": -18, "rage": 8},
    "museler_leader": {"esperance_democratique": -10, "rage": 12},
    "guerre_commerciale": {"rage": 10, "esperance_democratique": -8},
    "urgence_nationale": {"rage": 20, "credibilite": 10, "esperance_democratique": -15},
    "cyberattaque": {"complotisme": 15, "rage": 8},
    "provoquer_krach": {"rage": 18, "esperance_democratique": -12},
    "referendum_truque": {"credibilite": 15, "esperance_democratique": -25, "complotisme": 12},
}

# --- Index names ---
INDEX_NAMES: Final[list[str]] = [
    "credibilite", "rage", "complotisme", "esperance_democratique",
]

# --- Agent data (from agents.yaml) ---
AGENT_IDS: Final[list[str]] = [
    f"agent_{i:02d}" for i in range(1, 11)
]

AGENT_DATA: Final[list[dict[str, str]]] = [
    {"id": "agent_01", "name": "Jean-Édouard", "country": "FR", "level": "actif"},
    {"id": "agent_02", "name": "Karen", "country": "US", "level": "actif"},
    {"id": "agent_03", "name": "Dmitri", "country": "RU", "level": "leader"},
    {"id": "agent_04", "name": "Mamadou", "country": "SN", "level": "passif"},
    {"id": "agent_05", "name": "Brenda", "country": "BR", "level": "actif"},
    {"id": "agent_06", "name": "Hans-Peter", "country": "DE", "level": "passif"},
    {"id": "agent_07", "name": "Aisha", "country": "EG", "level": "leader"},
    {"id": "agent_08", "name": "Takeshi", "country": "JP", "level": "actif"},
    {"id": "agent_09", "name": "Svetlana", "country": "UA", "level": "passif"},
    {"id": "agent_10", "name": "Pedro", "country": "AR", "level": "actif"},
]

# --- GM message types ---
GM_TYPES: Final[list[str]] = [
    "gm_temperature", "gm_headlines", "gm_reaction", "gm_narrative",
]

# --- Headline styles ---
HEADLINE_STYLES: Final[list[str]] = ["gorafi", "onion", "raw"]

# --- Game phases ---
EARLY_TURNS: Final[range] = range(1, 4)    # 1-3
MID_TURNS: Final[range] = range(4, 7)      # 4-6
LATE_TURNS: Final[range] = range(7, 11)    # 7-10

# --- vLLM config (Qwen 3.5 on Scaleway H100) ---
VLLM_BASE_URL: Final[str] = "http://51.159.151.86:8000"
VLLM_API_KEY: Final[str] = "5y4q9PK47Qg04c74nghSYzEWHKCAT0TLYX5tqYCJ"
VLLM_MODEL: Final[str] = "Qwen/Qwen3.5-35B-A3B"
GENERATION_TEMPERATURE: Final[float] = 0.9
GENERATION_MAX_TOKENS: Final[int] = 2048
BATCH_SIZE: Final[int] = 10
