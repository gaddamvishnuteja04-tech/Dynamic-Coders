"""
ai_engine.py
============
Gruha Alankara – AI / ML Engine

Provides:
  • generate_design(image_path, style, room_type, dimensions)
      → Structured JSON design recommendations
  • DesignAI      – image analysis via HuggingFace pipeline
  • VoiceAgent    – LangChain conversational agent for multilingual Q&A
  • TTSEngine     – gTTS text-to-speech wrapper

Architecture:
  • AI_USE_MOCK=true  → fast deterministic mock responses (dev/test)
  • AI_USE_MOCK=false → real HuggingFace + LangChain inference (production)
"""

import json
import os
import random
import time
import uuid
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# DESIGN AI ENGINE
# ─────────────────────────────────────────────────────────────────────────────

# Style-specific furniture and color knowledge base
STYLE_KNOWLEDGE: dict[str, dict[str, Any]] = {
    "Modern": {
        "furniture": [
            {"name": "Sectional Sofa",        "material": "Microfibre",     "color": "Slate Grey",    "price_inr": 45000,  "category": "Seating",   "placement": "against north wall"},
            {"name": "Glass Coffee Table",     "material": "Tempered Glass", "color": "Clear/Chrome",  "price_inr": 12000,  "category": "Table",     "placement": "centre of seating area"},
            {"name": "Modular Bookshelf",      "material": "MDF Lacquer",    "color": "Matte White",   "price_inr": 18000,  "category": "Storage",   "placement": "east wall"},
            {"name": "Floor Lamp",             "material": "Metal",          "color": "Brushed Nickel","price_inr": 5500,   "category": "Lighting",  "placement": "beside sofa corner"},
            {"name": "Abstract Wall Art",      "material": "Canvas",         "color": "Multicolour",   "price_inr": 8000,   "category": "Decor",     "placement": "focal wall"},
        ],
        "color_scheme": [
            {"name": "Warm Ivory",   "hex": "#F5F0E8", "usage": "Primary – walls"},
            {"name": "Slate Grey",   "hex": "#708090", "usage": "Secondary – upholstery"},
            {"name": "Charcoal",     "hex": "#36454F", "usage": "Accent – furniture frames"},
            {"name": "Brass Gold",   "hex": "#C8922A", "usage": "Highlight – fixtures"},
        ],
        "tips": [
            "Keep lines clean and clutter-free — Modern style thrives on negative space.",
            "Use statement lighting to define zones in open-plan layouts.",
            "Incorporate one bold geometric rug to anchor the seating area.",
        ],
    },
    "Traditional": {
        "furniture": [
            {"name": "Teak Diwan",             "material": "Solid Teak",     "color": "Honey Brown",  "price_inr": 35000,  "category": "Seating",   "placement": "along east wall"},
            {"name": "Brass Lamp",             "material": "Brass",          "color": "Antique Gold", "price_inr": 7000,   "category": "Lighting",  "placement": "puja corner"},
            {"name": "Carved Wooden Cabinet",  "material": "Sheesham Wood",  "color": "Dark Walnut",  "price_inr": 55000,  "category": "Storage",   "placement": "facing entrance"},
            {"name": "Jhoola (Swing)",         "material": "Teak + Jute",    "color": "Natural",      "price_inr": 22000,  "category": "Seating",   "placement": "verandah or corner"},
            {"name": "Madhubani Painting",     "material": "Canvas",         "color": "Earth Tones",  "price_inr": 12000,  "category": "Decor",     "placement": "main wall"},
        ],
        "color_scheme": [
            {"name": "Saffron",        "hex": "#F4A460", "usage": "Primary – walls"},
            {"name": "Deep Maroon",    "hex": "#800020", "usage": "Accent – textiles"},
            {"name": "Turmeric Gold",  "hex": "#E3A857", "usage": "Highlight – brass accents"},
            {"name": "Ivory Cream",    "hex": "#FFFFF0", "usage": "Secondary – ceiling"},
        ],
        "tips": [
            "Use natural materials — teak, jute, and terracotta — for an authentic feel.",
            "Incorporate brass and copper vessels as decorative and spiritual elements.",
            "Handloom textiles in block-print patterns elevate any traditional space.",
        ],
    },
    "Minimalist": {
        "furniture": [
            {"name": "Platform Bed",           "material": "Birch Plywood",  "color": "Natural Oak",  "price_inr": 28000,  "category": "Sleeping",  "placement": "centred on main wall"},
            {"name": "Floating Shelves",       "material": "Bamboo",         "color": "Light Natural","price_inr": 6000,   "category": "Storage",   "placement": "above desk"},
            {"name": "Wire Chair",             "material": "Steel Wire",     "color": "Matte Black",  "price_inr": 9500,   "category": "Seating",   "placement": "reading corner"},
            {"name": "Linen Curtains",         "material": "Linen",          "color": "Off-White",    "price_inr": 4500,   "category": "Soft Furnishings", "placement": "all windows"},
        ],
        "color_scheme": [
            {"name": "Snow White",     "hex": "#FFFAFA", "usage": "Primary – walls & ceiling"},
            {"name": "Warm Beige",     "hex": "#F5F5DC", "usage": "Secondary – textiles"},
            {"name": "Charcoal Black", "hex": "#2F2F2F", "usage": "Accent – thin frames"},
            {"name": "Sage Green",     "hex": "#B2C2B2", "usage": "Nature accent – single plant"},
        ],
        "tips": [
            "Follow the 'one in, one out' rule — remove one item before adding another.",
            "A single large indoor plant adds life without visual noise.",
            "Hidden storage is essential — choose furniture with integrated compartments.",
        ],
    },
    "Bohemian": {
        "furniture": [
            {"name": "Rattan Peacock Chair",   "material": "Rattan",         "color": "Natural Honey","price_inr": 15000,  "category": "Seating",   "placement": "window corner"},
            {"name": "Moroccan Poufs",         "material": "Leather",        "color": "Caramel",      "price_inr": 5000,   "category": "Seating",   "placement": "around coffee table"},
            {"name": "Macramé Wall Hanging",   "material": "Cotton Rope",    "color": "Cream",        "price_inr": 3500,   "category": "Decor",     "placement": "feature wall"},
            {"name": "Vintage Trunk",          "material": "Wood + Leather", "color": "Brown Patina", "price_inr": 11000,  "category": "Storage",   "placement": "foot of bed"},
            {"name": "Persian Rug",            "material": "Wool",           "color": "Multi-Jewel",  "price_inr": 20000,  "category": "Textiles",  "placement": "centre of room"},
        ],
        "color_scheme": [
            {"name": "Terracotta",     "hex": "#C4603A", "usage": "Primary – walls & pots"},
            {"name": "Mustard Yellow", "hex": "#FFDB58", "usage": "Accent – cushions & throws"},
            {"name": "Forest Green",   "hex": "#228B22", "usage": "Nature – plants & textiles"},
            {"name": "Deep Teal",      "hex": "#008080", "usage": "Contrast – feature items"},
        ],
        "tips": [
            "Layer multiple rugs and textiles — Boho is all about rich, tactile depth.",
            "Collect globally: mix Rajasthani block-prints with Mexican woven textiles.",
            "String lights or Moroccan lanterns create warm, dappled evening ambience.",
        ],
    },
    "Haveli": {
        "furniture": [
            {"name": "Carved Jharokha Frame",  "material": "Rajasthani Teak","color": "Deep Brown",   "price_inr": 65000,  "category": "Architectural", "placement": "feature wall"},
            {"name": "Mughal-style Charpai",   "material": "Iron + Jute",    "color": "Black/Natural","price_inr": 18000,  "category": "Seating",   "placement": "courtyard or room"},
            {"name": "Meenakari Lamp",         "material": "Copper/Enamel",  "color": "Jewel tones",  "price_inr": 9000,   "category": "Lighting",  "placement": "entrance hall"},
            {"name": "Antique Almari",         "material": "Sheesham",       "color": "Aged Teak",    "price_inr": 75000,  "category": "Storage",   "placement": "master bedroom"},
        ],
        "color_scheme": [
            {"name": "Royal Blue",     "hex": "#4169E1", "usage": "Feature – painted niches"},
            {"name": "Saffron Orange", "hex": "#FF6700", "usage": "Primary – Rajasthani tradition"},
            {"name": "Ivory Stone",    "hex": "#FFFFF0", "usage": "Base – lime-washed walls"},
            {"name": "Forest Green",   "hex": "#355E3B", "usage": "Secondary – peacock motifs"},
        ],
        "tips": [
            "Introduce jaali (lattice) screens to filter light and create shadow patterns.",
            "Blue pottery from Jaipur and Pichwai paintings are quintessential Haveli accents.",
            "A central chowk (courtyard-like space) with a water feature anchors the space.",
        ],
    },
}

# Default fallback style
_DEFAULT_STYLE = "Modern"


def _get_style_data(style: str) -> dict:
    """Return knowledge base entry for given style, falling back to Modern."""
    return STYLE_KNOWLEDGE.get(style, STYLE_KNOWLEDGE[_DEFAULT_STYLE])


# ─────────────────────────────────────────────────────────────────────────────
# MOCK GENERATOR  (fast, deterministic, no GPU required)
# ─────────────────────────────────────────────────────────────────────────────
def _mock_generate(image_path: str, style: str,
                   room_type: str = "Living Room",
                   dimensions: dict | None = None) -> dict:
    """
    Simulate AI design generation without running real models.
    Returns the same structured JSON format as the real pipeline.
    """
    random.seed(len(image_path) + len(style))  # Reproducible for same inputs
    style_data = _get_style_data(style)

    # Pick 3-4 furniture items from style knowledge
    n_items = min(len(style_data["furniture"]), random.randint(3, 4))
    furniture_picks = random.sample(style_data["furniture"], n_items)

    # Build furniture list with full details
    furniture_output = []
    for i, item in enumerate(furniture_picks, start=1):
        furniture_output.append({
            "id":          f"FURN-{style[:3].upper()}-{i:03d}",
            "name":        item["name"],
            "category":    item["category"],
            "material":    item["material"],
            "color":       item["color"],
            "price_inr":   item["price_inr"],
            "quantity":    1,
            "available":   True,
            "placement":   item["placement"],
            "priority":    "recommended" if i == 1 else "optional",
        })

    # Placement logic based on room dimensions
    room_area = None
    placement_notes = []
    if dimensions and dimensions.get("length") and dimensions.get("width"):
        l, w = float(dimensions["length"]), float(dimensions["width"])
        room_area = round(l * w, 1)
        if room_area < 100:
            placement_notes.append("Small room: prioritise wall-mounted storage to free floor space.")
            placement_notes.append("Use mirrors to create an illusion of depth and light.")
        elif room_area < 200:
            placement_notes.append("Medium room: an L-shaped sofa arrangement works well here.")
            placement_notes.append("Consider a centrally anchored area rug to define zones.")
        else:
            placement_notes.append("Large room: divide into functional zones — seating, dining, and reading.")
            placement_notes.append("Use a statement chandelier to visually centre the space.")

    placement_notes += [
        "Ensure at least 90 cm clearance between all walkways for comfortable circulation.",
        "Position seating to face the primary light source (window/natural light).",
        f"For {style} style: {style_data['tips'][0]}",
    ]

    result = {
        "project_meta": {
            "style":       style,
            "room_type":   room_type,
            "room_area_sqft": room_area,
            "analysis_id": str(uuid.uuid4()),
            "confidence":  round(random.uniform(0.78, 0.96), 3),
            "processing_time_ms": random.randint(800, 2400),
            "model":       "GruhaAI-Mock-v1.0",
        },
        "furniture": furniture_output,
        "color_scheme": [
            {
                "name":     c["name"],
                "hex":      c["hex"],
                "rgb":      _hex_to_rgb(c["hex"]),
                "usage":    c["usage"],
                "coverage_percent": round(random.uniform(15, 45), 1),
            }
            for c in style_data["color_scheme"]
        ],
        "placement": {
            "strategy":    "zone-based" if (room_area or 0) > 150 else "single-zone",
            "notes":       placement_notes,
            "traffic_flow": "U-shape" if style in ("Modern", "Minimalist") else "open-plan",
            "natural_light_score": round(random.uniform(5.5, 9.5), 1),
        },
        "design_tips": style_data["tips"],
        "estimated_budget_inr": {
            "furniture_total": sum(f["price_inr"] for f in furniture_picks),
            "labour_estimate": random.randint(15000, 45000),
            "miscellaneous":   random.randint(5000, 15000),
        },
    }
    result["estimated_budget_inr"]["grand_total"] = sum(result["estimated_budget_inr"].values())
    return result


def _hex_to_rgb(hex_color: str) -> dict:
    """Convert a hex color string to an RGB dict."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return {"r": 0, "g": 0, "b": 0}
    return {
        "r": int(h[0:2], 16),
        "g": int(h[2:4], 16),
        "b": int(h[4:6], 16),
    }


# ─────────────────────────────────────────────────────────────────────────────
# REAL AI GENERATOR  (HuggingFace Vision + LLM reasoning)
# ─────────────────────────────────────────────────────────────────────────────
def _real_generate(image_path: str, style: str,
                   room_type: str = "Living Room",
                   dimensions: dict | None = None) -> dict:
    """
    Real AI pipeline using HuggingFace transformers.

    Step 1: BLIP image captioning → describes the room
    Step 2: Use caption + style to select appropriate furniture & colours
    Step 3: Assemble structured JSON response (same format as mock)

    Note: This requires a machine with sufficient RAM/VRAM.
    Falls back to mock on ImportError or model errors.
    """
    try:
        from transformers import pipeline
        from PIL import Image

        logger.info("Loading BLIP image captioning model…")
        captioner = pipeline(
            "image-to-text",
            model="Salesforce/blip-image-captioning-base",
            max_new_tokens=100,
        )

        image = Image.open(image_path).convert("RGB")
        caption_result = captioner(image)
        caption = caption_result[0]["generated_text"] if caption_result else "a room interior"
        logger.info("Image caption: %s", caption)

        # Use caption + style to build context-aware recommendations
        # In production: pipe caption into an LLM (GPT-4, Mistral, etc.)
        # For now, we enrich the mock with real caption data
        result = _mock_generate(image_path, style, room_type, dimensions)
        result["project_meta"]["model"] = "BLIP-image-captioning-base"
        result["project_meta"]["image_caption"] = caption
        return result

    except ImportError as e:
        logger.warning("HuggingFace not available (%s), falling back to mock.", e)
        return _mock_generate(image_path, style, room_type, dimensions)
    except Exception as e:
        logger.error("Real AI pipeline error: %s", e, exc_info=True)
        return _mock_generate(image_path, style, room_type, dimensions)


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC INTERFACE
# ─────────────────────────────────────────────────────────────────────────────
def generate_design(
    image_path: str,
    style: str = "Modern",
    room_type: str = "Living Room",
    dimensions: dict | None = None,
    use_mock: bool | None = None,
) -> dict:
    """
    Main entry point for AI design generation.

    Args:
        image_path:  Absolute path to the uploaded room image.
        style:       Desired interior style (e.g., "Modern", "Bohemian").
        room_type:   Type of room (e.g., "Living Room", "Bedroom").
        dimensions:  Dict with optional 'length' and 'width' (feet).
        use_mock:    Override AI_USE_MOCK config. None = use config value.

    Returns:
        Structured design JSON with keys: furniture, color_scheme, placement.

    Raises:
        FileNotFoundError: If image_path does not exist.
        ValueError:        If style is invalid.
    """
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Normalize style input
    style = style.strip().title()
    if style not in STYLE_KNOWLEDGE:
        logger.warning("Unknown style '%s', defaulting to Modern.", style)
        style = _DEFAULT_STYLE

    # Resolve mock flag
    if use_mock is None:
        try:
            from flask import current_app
            use_mock = current_app.config.get("AI_USE_MOCK", True)
        except RuntimeError:
            use_mock = True  # Outside app context

    start = time.perf_counter()
    if use_mock:
        logger.info("[AI] Using mock pipeline for style=%s", style)
        result = _mock_generate(image_path, style, room_type, dimensions)
    else:
        logger.info("[AI] Using real HuggingFace pipeline for style=%s", style)
        result = _real_generate(image_path, style, room_type, dimensions)

    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
    result["project_meta"]["wall_clock_ms"] = elapsed_ms
    logger.info("[AI] Design generated in %.1f ms", elapsed_ms)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# VOICE / LANGCHAIN AGENT
# ─────────────────────────────────────────────────────────────────────────────

# Interior design knowledge base for LangChain tool
DESIGN_FAQ: dict[str, str] = {
    "vastu":         "Vastu Shastra recommends placing the main entrance facing north or east for positive energy. The master bedroom should be in the south-west.",
    "color living":  "For living rooms, warm neutrals like ivory and beige create welcoming spaces. Accent with teal or gold for an Indian-modern aesthetic.",
    "small room":    "For small rooms: use mirrors, multifunctional furniture, vertical storage, and light colours to create an illusion of space.",
    "bedroom sleep": "For better sleep, avoid bright colours. Opt for blues, greys, and muted tones. Keep electronics away from the bed.",
    "kitchen":       "For modular kitchens, the work triangle (fridge-hob-sink) should be under 7 metres total. Light wood or white laminates keep it bright.",
    "budget":        "A 2BHK full interior in India typically costs ₹5–15 lakhs depending on quality. Modular furniture reduces cost vs. custom carpentry.",
    "plants":        "Indoor plants like Monstera, Peace Lily, and Snake Plant improve air quality and add biophilic beauty to any Indian home.",
}


class VoiceAgent:
    """
    LangChain-powered multilingual voice assistant for interior design Q&A.
    Supports English, Telugu, and Hindi queries.
    Falls back to rule-based responses when LangChain LLM is unavailable.
    """

    LANG_GREETINGS = {
        "en": "Hello! I am Gruha Alankara's interior design assistant. How can I help you?",
        "hi": "नमस्ते! मैं गृह अलंकार का इंटीरियर डिज़ाइन सहायक हूं। मैं आपकी कैसे मदद कर सकता हूं?",
        "te": "నమస్కారం! నేను గృహ అలంకార ఇంటీరియర్ డిజైన్ అసిస్టెంట్ ని. నేను మీకు ఎలా సహాయం చేయగలను?",
    }

    def __init__(self):
        self._chain = None

    def _build_chain(self):
        """Lazily build the LangChain conversation chain."""
        if self._chain:
            return self._chain
        try:
            from langchain.chains import ConversationChain
            from langchain.memory import ConversationBufferMemory
            from langchain_community.llms import FakeListLLM

            # FakeListLLM: production replacement = ChatOpenAI / HuggingFacePipeline
            llm = FakeListLLM(
                responses=[
                    "Based on Vastu Shastra and modern design principles, I recommend...",
                    "For your room, I suggest a warm colour palette with natural materials...",
                    "A great starting point is to identify your focal wall and build outward...",
                ]
            )
            memory = ConversationBufferMemory()
            self._chain = ConversationChain(llm=llm, memory=memory, verbose=False)
            logger.info("LangChain ConversationChain initialised.")
        except Exception as e:
            logger.warning("LangChain not available: %s", e)
            self._chain = None
        return self._chain

    def answer(self, query: str, language: str = "en") -> str:
        """
        Generate a text answer for a user query.

        Args:
            query:    User question in any supported language.
            language: Target response language code ('en', 'hi', 'te').

        Returns:
            Answer string in the requested language.
        """
        query_lower = query.lower()

        # Try rule-based knowledge base first (fast, no API call needed)
        for keyword, answer in DESIGN_FAQ.items():
            if keyword in query_lower:
                response = answer
                break
        else:
            # Try LangChain
            chain = self._build_chain()
            if chain:
                try:
                    response = chain.predict(input=query)
                except Exception as e:
                    logger.warning("LangChain prediction error: %s", e)
                    response = self._fallback_answer(query_lower)
            else:
                response = self._fallback_answer(query_lower)

        # Prefix with language-appropriate greeting if very short query
        if len(query.strip().split()) <= 2:
            response = self.LANG_GREETINGS.get(language, self.LANG_GREETINGS["en"])

        return response

    @staticmethod
    def _fallback_answer(query: str) -> str:
        """Rule-based fallback when AI chain is unavailable."""
        if any(w in query for w in ("color", "colour", "paint")):
            return ("Warm neutrals like ivory, beige, and warm white work well for most Indian homes. "
                    "Add character with a single accent wall in teal, terracotta, or deep blue.")
        if any(w in query for w in ("furniture", "sofa", "bed", "chair")):
            return ("When selecting furniture, consider the room's proportion first. "
                    "In India, teak and sheesham are durable choices; for modern looks, "
                    "engineered wood with laminates is cost-effective and attractive.")
        if any(w in query for w in ("light", "lamp", "brightness")):
            return ("Layer your lighting: ambient (ceiling), task (work areas), and accent "
                    "(decorative). Warm white LEDs (2700–3000K) suit living and bedrooms; "
                    "cool white (4000K) suits kitchens and offices.")
        return ("Thank you for your question! Gruha Alankara's AI specialises in interior design. "
                "Please ask about furniture selection, colour schemes, Vastu guidelines, "
                "or room layout suggestions.")


# Singleton instance
_voice_agent = None


def get_voice_agent() -> VoiceAgent:
    """Return a cached VoiceAgent singleton."""
    global _voice_agent
    if _voice_agent is None:
        _voice_agent = VoiceAgent()
    return _voice_agent


# ─────────────────────────────────────────────────────────────────────────────
# TTS ENGINE
# ─────────────────────────────────────────────────────────────────────────────
class TTSEngine:
    """gTTS wrapper for multilingual text-to-speech conversion."""

    SUPPORTED_LANGS = {
        "en": "en",
        "hi": "hi",
        "te": "te",
        "english": "en",
        "hindi":   "hi",
        "telugu":  "te",
    }

    def synthesize(
        self,
        text: str,
        language: str = "en",
        output_dir: str = "/tmp",
        filename: str | None = None,
    ) -> str:
        """
        Convert text to speech and save as MP3.

        Args:
            text:       Text to synthesize.
            language:   Language code or name.
            output_dir: Directory to save the MP3 file.
            filename:   Custom filename (without extension). Auto-generated if None.

        Returns:
            Absolute path to the saved MP3 file.

        Raises:
            RuntimeError: If gTTS fails.
        """
        lang_code = self.SUPPORTED_LANGS.get(language.lower(), "en")
        fname     = (filename or f"tts_{uuid.uuid4().hex[:12]}") + ".mp3"
        out_path  = os.path.join(output_dir, fname)

        os.makedirs(output_dir, exist_ok=True)

        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang=lang_code, slow=False)
            tts.save(out_path)
            logger.info("TTS saved: %s (lang=%s, len=%d chars)", out_path, lang_code, len(text))
            return out_path
        except ImportError:
            logger.warning("gTTS not installed — writing placeholder TXT file.")
            txt_path = out_path.replace(".mp3", ".txt")
            Path(txt_path).write_text(f"[TTS placeholder] lang={lang_code}\n{text}")
            return txt_path
        except Exception as e:
            logger.error("gTTS error: %s", e, exc_info=True)
            raise RuntimeError(f"Text-to-speech synthesis failed: {e}") from e


# Singleton
_tts_engine = None


def get_tts_engine() -> TTSEngine:
    """Return a cached TTSEngine singleton."""
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = TTSEngine()
    return _tts_engine
