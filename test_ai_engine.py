"""
tests/test_ai_engine.py
=======================
Tests for the AI engine – mock generation, TTS, and VoiceAgent.
"""

import os
import pytest
import tempfile
from PIL import Image


@pytest.fixture
def sample_image(tmp_path):
    """Create a minimal valid JPEG image for testing."""
    img_path = str(tmp_path / "test_room.jpg")
    img = Image.new("RGB", (640, 480), color=(180, 160, 140))
    img.save(img_path, "JPEG")
    return img_path


# ─────────────────────────────────────────────────────────────────────────────
# DESIGN GENERATION
# ─────────────────────────────────────────────────────────────────────────────
class TestGenerateDesign:
    def test_mock_generate_returns_structure(self, sample_image):
        from ai_engine import generate_design
        result = generate_design(sample_image, style="Modern", use_mock=True)

        assert "furniture" in result
        assert "color_scheme" in result
        assert "placement" in result
        assert "design_tips" in result
        assert "estimated_budget_inr" in result
        assert "project_meta" in result

    def test_furniture_list_not_empty(self, sample_image):
        from ai_engine import generate_design
        result = generate_design(sample_image, style="Bohemian", use_mock=True)
        assert len(result["furniture"]) >= 1

    def test_each_furniture_has_required_keys(self, sample_image):
        from ai_engine import generate_design
        result = generate_design(sample_image, style="Traditional", use_mock=True)
        for item in result["furniture"]:
            assert "id" in item
            assert "name" in item
            assert "price_inr" in item
            assert "placement" in item

    def test_color_scheme_has_hex(self, sample_image):
        from ai_engine import generate_design
        result = generate_design(sample_image, style="Minimalist", use_mock=True)
        for color in result["color_scheme"]:
            assert "hex" in color
            assert color["hex"].startswith("#")

    def test_unknown_style_falls_back_to_modern(self, sample_image):
        from ai_engine import generate_design
        result = generate_design(sample_image, style="UnknownStyle", use_mock=True)
        assert result["project_meta"]["style"] == "Modern"

    def test_budget_grand_total(self, sample_image):
        from ai_engine import generate_design
        result = generate_design(sample_image, use_mock=True)
        budget = result["estimated_budget_inr"]
        expected = budget["furniture_total"] + budget["labour_estimate"] + budget["miscellaneous"]
        assert budget["grand_total"] == expected

    def test_missing_image_raises(self):
        from ai_engine import generate_design
        with pytest.raises(FileNotFoundError):
            generate_design("/no/such/image.jpg")

    def test_with_dimensions(self, sample_image):
        from ai_engine import generate_design
        dims = {"length": 15.0, "width": 12.0}
        result = generate_design(sample_image, dimensions=dims, use_mock=True)
        assert result["project_meta"]["room_area_sqft"] == 180.0

    @pytest.mark.parametrize("style", ["Modern", "Traditional", "Minimalist", "Bohemian", "Haveli"])
    def test_all_styles(self, sample_image, style):
        from ai_engine import generate_design
        result = generate_design(sample_image, style=style, use_mock=True)
        assert result["project_meta"]["style"] == style


# ─────────────────────────────────────────────────────────────────────────────
# VOICE AGENT
# ─────────────────────────────────────────────────────────────────────────────
class TestVoiceAgent:
    def test_answer_returns_string(self):
        from ai_engine import get_voice_agent
        agent = get_voice_agent()
        result = agent.answer("What color should I paint my living room?")
        assert isinstance(result, str)
        assert len(result) > 5

    def test_vastu_query(self):
        from ai_engine import get_voice_agent
        agent = get_voice_agent()
        result = agent.answer("Tell me about vastu shastra for my home")
        assert "vastu" in result.lower() or "north" in result.lower() or "east" in result.lower()

    def test_small_room_query(self):
        from ai_engine import get_voice_agent
        agent = get_voice_agent()
        result = agent.answer("How do I design a small room?")
        assert isinstance(result, str)
        assert len(result) > 10

    def test_greetings_short_query(self):
        from ai_engine import get_voice_agent
        agent = get_voice_agent()
        result = agent.answer("Hi", language="en")
        assert isinstance(result, str)

    @pytest.mark.parametrize("lang", ["en", "hi", "te"])
    def test_multilanguage(self, lang):
        from ai_engine import get_voice_agent
        agent = get_voice_agent()
        result = agent.answer("What furniture do you recommend?", language=lang)
        assert isinstance(result, str)


# ─────────────────────────────────────────────────────────────────────────────
# TTS ENGINE
# ─────────────────────────────────────────────────────────────────────────────
class TestTTSEngine:
    def test_synthesize_creates_file(self, tmp_path):
        from ai_engine import get_tts_engine
        tts = get_tts_engine()
        out = tts.synthesize(
            text="Welcome to Gruha Alankara",
            language="en",
            output_dir=str(tmp_path),
        )
        assert os.path.isfile(out)

    def test_synthesize_hindi(self, tmp_path):
        from ai_engine import get_tts_engine
        tts = get_tts_engine()
        out = tts.synthesize(
            text="नमस्ते गृह अलंकार में आपका स्वागत है",
            language="hi",
            output_dir=str(tmp_path),
        )
        assert os.path.isfile(out)

    def test_synthesize_custom_filename(self, tmp_path):
        from ai_engine import get_tts_engine
        tts = get_tts_engine()
        out = tts.synthesize(
            text="Test",
            language="en",
            output_dir=str(tmp_path),
            filename="custom_test",
        )
        assert "custom_test" in os.path.basename(out)

    def test_unsupported_language_falls_back(self, tmp_path):
        from ai_engine import get_tts_engine
        tts = get_tts_engine()
        # Unknown language should fall back to English (no crash)
        out = tts.synthesize(
            text="Test text",
            language="zz",  # not a real code
            output_dir=str(tmp_path),
        )
        assert os.path.isfile(out)
