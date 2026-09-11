"""Minimal UI localisation — English / French / Bambara.

Scope, honestly: this translates the static navigation chrome (title, form
labels, buttons, tab names, badges). It does NOT translate the agent's
generated findings (risk narrative, recommendations) — those are produced by
the deterministic template / LLM in English only; translating them would
require localising the synthesis layer itself, out of scope here.

Bambara coverage is partial and best-effort, not native-reviewed: only
core, well-attested farming vocabulary is translated. Any key without a
Bambara entry falls back to French (Mali's administrative written language)
rather than fabricated technical Bambara. This is disclosed in the UI itself
when Bambara is selected — see ``PARTIAL_NOTICE``.
"""
from __future__ import annotations

LANGUAGES: dict[str, str] = {
    "en": "🇬🇧 EN",
    "fr": "🇫🇷 FR",
    "bm": "🇲🇱 BM",
}

PARTIAL_NOTICE = (
    "Bambara translation covers core farming terms only (best-effort, not yet "
    "reviewed by a native speaker); remaining labels are shown in French. "
    "Community review welcome."
)

# key -> {lang: text}. Missing "bm" falls back to "fr", missing "fr" falls
# back to "en" (see t()).
_STRINGS: dict[str, dict[str, str]] = {
    "app_title": {"en": "SAHEL Agent", "fr": "SAHEL Agent", "bm": "SAHEL Agent"},
    "app_tagline": {
        "en": "Multimodal AI Agent for Environmental & Agricultural Intelligence",
        "fr": "Agent IA multimodal pour l'intelligence environnementale et agricole",
        "bm": "Baarakɛminɛn (AI) min bɛ sɛnɛko ni yiriwara kunnafoniw sɛgɛsɛgɛ",
    },
    "judge_mode_banner": {
        "en": "**Judge demo mode** — scenario *{scenario}* is preloaded. Press **ANALYZE** to run the agent.",
        "fr": "**Mode démo jury** — le scénario *{scenario}* est préchargé. Appuyez sur **ANALYZE** pour lancer l'agent.",
    },
    "input_header": {"en": "Input", "fr": "Entrée", "bm": "Ka don"},
    "image_uploader": {
        "en": "Plant / field image (optional)",
        "fr": "Image de plante / champ (optionnel)",
        "bm": "Foro walima yiri ja (wajibi tɛ)",
    },
    "temperature": {"en": "Temperature (°C)", "fr": "Température (°C)", "bm": "Funteni (°C)"},
    "soil_moisture": {"en": "Soil moisture (%)", "fr": "Humidité du sol (%)", "bm": "Dugukolo ɲigin (%)"},
    "air_humidity": {"en": "Air humidity (%)", "fr": "Humidité de l'air (%)"},
    "rainfall": {"en": "Rainfall (mm)", "fr": "Précipitations (mm)", "bm": "Sanji (mm)"},
    "growth_stage": {"en": "Growth stage", "fr": "Stade de croissance"},
    "location_label": {"en": "Location label", "fr": "Nom du lieu", "bm": "Yɔrɔ tɔgɔ"},
    "latitude": {"en": "Latitude", "fr": "Latitude"},
    "longitude": {"en": "Longitude", "fr": "Longitude"},
    "context_optional": {"en": "Context (optional)", "fr": "Contexte (optionnel)"},
    "analyze_button": {"en": "ANALYZE", "fr": "ANALYSER"},
    "agent_activity": {"en": "Agent activity", "fr": "Activité de l'agent"},
    "agent_working": {"en": "Agent working…", "fr": "L'agent travaille…"},
    "situation": {"en": "Situation", "fr": "Situation", "bm": "Ko kɛtaa"},
    "tab_visual": {"en": "Visual observations", "fr": "Observations visuelles"},
    "tab_env": {"en": "Environmental analysis", "fr": "Analyse environnementale"},
    "tab_risk": {"en": "Risk assessment", "fr": "Évaluation du risque"},
    "tab_rec": {"en": "Recommendations", "fr": "Recommandations", "bm": "Laadilikan"},
    "tab_conf": {"en": "Confidence & limitations", "fr": "Confiance et limites"},
    "tab_run": {"en": "Run details", "fr": "Détails d'exécution"},
    "sidebar_runtime": {"en": "Runtime", "fr": "Configuration"},
    "sidebar_load_scenario": {"en": "Load demo scenario", "fr": "Charger un scénario de démo"},
    "load": {"en": "Load", "fr": "Charger"},
    "reset": {"en": "Reset", "fr": "Réinitialiser"},
    "empty_state": {
        "en": "Load a demo scenario or fill the form, then press **ANALYZE**.",
        "fr": "Chargez un scénario de démo ou remplissez le formulaire, puis appuyez sur **ANALYZE**.",
    },
    "offline_caption": {
        "en": "Runs fully offline with mock LLM + local providers. No keys required.",
        "fr": "Fonctionne entièrement hors-ligne avec un LLM factice et des fournisseurs locaux. Aucune clé requise.",
    },
    "badge_low": {"en": "LOW", "fr": "FAIBLE"},
    "badge_moderate": {"en": "MODERATE", "fr": "MODÉRÉ"},
    "badge_medium": {"en": "MEDIUM", "fr": "MOYEN"},
    "badge_high": {"en": "HIGH", "fr": "ÉLEVÉ", "bm": "Belebeleba"},
    "badge_unknown": {"en": "UNKNOWN", "fr": "INCONNU"},
    "evidence_header": {"en": "Evidence", "fr": "Éléments de preuve"},
    "evidence_live": {"en": "🔎 Live via Exa", "fr": "🔎 En direct via Exa"},
    "evidence_sample": {
        "en": "🔎 Offline sample (set EXA_API_KEY for live sources)",
        "fr": "🔎 Échantillon hors-ligne (renseignez EXA_API_KEY pour des sources en direct)",
    },
}


def t(key: str, lang: str = "en", **fmt) -> str:
    """Look up ``key`` for ``lang``; fall back bm -> fr -> en -> the key itself."""
    entry = _STRINGS.get(key)
    if not entry:
        return key
    text = entry.get(lang) or entry.get("fr" if lang == "bm" else "en") or entry.get("en") or key
    return text.format(**fmt) if fmt else text
