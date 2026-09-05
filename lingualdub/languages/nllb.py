"""
NLLB language code mappings — single source of truth for translation components.

Previously duplicated between hf_translator.py and sunbird.py with diverging keys.
"""

# ISO 639-1/3 -> NLLB 200 code mapping for supported low-resource languages.
# Extend here; all translation components should import from this module.
NLLB_CODE_MAP: dict[str, str] = {
    "eng": "eng_Latn",
    "lug": "lug_Latn",
    "nyn": "nyn_Latn",
    "swa": "swh_Latn",
    "ach": "ach_Latn",
    "teo": "teo_Latn",
    "lgg": "lgg_Latn",
    "fra": "fra_Latn",
}
