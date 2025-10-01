# app.py
import io
import base64
import time
import streamlit as st
from gtts import gTTS
from langdetect import detect, LangDetectException
from googletrans import Translator, LANGUAGES
import pycountry
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import nltk

# ---------- Ensure NLTK resources (download only if missing) ----------
def ensure_nltk_resource(name, package=None):
    try:
        nltk.data.find(name)
    except LookupError:
        nltk.download(package or name.split('/')[-1], quiet=True)

ensure_nltk_resource('tokenizers/punkt', 'punkt')
ensure_nltk_resource('corpora/stopwords', 'stopwords')

# ---------- Helpers ----------
def get_language_name(code):
    """Return a friendly language name for a language code."""
    try:
        # try pycountry first for 2-letter codes
        if code and len(code) == 2:
            name = pycountry.languages.get(alpha_2=code)
            if name and getattr(name, "name", None):
                return name.name
    except Exception:
        pass
    # fallback to googletrans mapping
    return LANGUAGES.get(code, code).title()

def add_bg_from_local(image_file):
    """Add a background image to the Streamlit app (base64 inline)."""
    try:
        with open(image_file, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/jpg;base64,{b64}");
                background-attachment: fixed;
                background-size: cover;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
    except FileNotFoundError:
        # ignore if not present
        pass

def read_aloud_streamlit(text, lang="en"):
    """Return an in-memory mp3 and let Streamlit play it."""
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        st.audio(mp3_fp, format="audio/mp3")
    except Exception as e:
        st.warning(f"Audio generation failed for lang='{lang}': {e}")

def generate_wordcloud_figure(text):
    """Generate a matplotlib figure with a word cloud (removes stopwords & non-alpha tokens)."""
    tokens = word_tokenize(text.lower())
    try:
        stop_words = set(stopwords.words("english"))
    except LookupError:
        stop_words = set()
    filtered = [w for w in tokens if w.isalpha() and w not in stop_words]
    if not filtered:
        raise ValueError("No valid words to build a word cloud after filtering.")
    wc_text = " ".join(filtered)
    wc = WordCloud(width=800, height=400, background_color="white").generate(wc_text)
    fig = plt.figure(figsize=(10, 5))
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.tight_layout()
    return fig

def normalize_gtts_code(code):
    """Normalize some codes so gTTS accepts them (simple heuristics)."""
    if not code:
        return "en"
    gtts_code = code
    if "-" in code:
        gtts_code = code.split("-")[0]
    # map legacy / special codes
    if gtts_code == "iw":
        return "he"
    if gtts_code == "in":
        return "id"
    return gtts_code

def spell_text_audio_bytes(word, lang="en", pause=0.2):
    """
    Create an audio that spells the word letter-by-letter.
    We create the spaced string and ask gTTS to speak it.
    pause: visual delay between letters isn't directly controllable via gTTS, but using spaces
           and 'slow=True' helps. Another approach would be concatenating short audio clips per letter,
           but that is more involved. This function uses a spaced string and slow speech for clarity.
    """
    # create spaced text: "a b c" and also add small separators (commas) to improve clarity
    spaced = " ".join(list(word))
    # also create "A, B, C" style which tends to be clearer for gTTS in some languages
    dotted = ", ".join(list(word))
    # prefer dotted (with commas) for clarity
    to_speak = dotted
    gtts_lang = normalize_gtts_code(lang)
    tts = gTTS(text=to_speak, lang=gtts_lang, slow=True)
    mp3_fp = io.BytesIO()
    tts.write_to_fp(mp3_fp)
    mp3_fp.seek(0)
    return mp3_fp

# ---------- Page layout ----------
st.set_page_config(page_title="Globalize", layout="wide")
add_bg_from_local("back.jpg")

st.title("Globalize — small multilingual helper")

# create a single translator instance for the app
translator = Translator()

col1, col2 = st.columns([2, 1])

with col1:
    paragraph = st.text_area("Enter one paragraph:", height=220)

    if st.button("Detect language"):
        if paragraph.strip():
            try:
                code = detect(paragraph)
                st.success(f"Detected: {get_language_name(code)} ({code})")
            except LangDetectException:
                st.error("Language detection failed (text too short or ambiguous).")
            except Exception as e:
                st.error(f"Language detection error: {e}")
        else:
            st.info("Type or paste a paragraph first.")

    # Translate to English button (universal view)
    if st.button("Translate to English (if not already)"):
        if paragraph.strip():
            try:
                detected = detect(paragraph)
            except Exception:
                detected = None
            try:
                if detected and detected != "en":
                    translated = translator.translate(paragraph, dest="en").text
                    st.subheader("Translated to English:")
                    st.write(translated)
                else:
                    st.info("Text appears to already be English.")
                    st.write(paragraph)
            except Exception as e:
                st.error(f"Translation failed: {e}")
        else:
            st.info("Type or paste a paragraph first.")

    if st.button("Generate Word Cloud"):
        if paragraph.strip():
            # prefer English text for a clearer cloud — attempt translation
            try:
                detected = detect(paragraph)
            except Exception:
                detected = None
            text_for_cloud = paragraph
            if detected and detected != "en":
                try:
                    text_for_cloud = translator.translate(paragraph, dest="en").text
                except Exception:
                    # fallback to original if translation fails
                    text_for_cloud = paragraph
            try:
                fig = generate_wordcloud_figure(text_for_cloud)
                st.pyplot(fig)
            except Exception as e:
                st.error(f"Could not generate word cloud: {e}")
        else:
            st.info("Type or paste a paragraph first.")

with col2:
    st.subheader("Translate & read aloud")

    # Build language display list from googletrans LANGUAGES dict (name.title() -> code)
    display_map = {name.title(): code for code, name in LANGUAGES.items()}
    all_languages = sorted(display_map.keys())

    # Option to select all languages quickly
    select_all = st.checkbox("Select all languages", value=False)
    default_selection = all_languages if select_all else ["English"]

    target_languages = st.multiselect(
        "Select target languages (audio will attempt to play where supported)",
        all_languages,
        default=default_selection,
    )

    if st.button("Translate & Read Aloud"):
        if not paragraph.strip():
            st.info("Type or paste a paragraph first.")
        else:
            for name in target_languages:
                code = display_map.get(name)
                if not code:
                    st.warning(f"Unknown language selection: {name}")
                    continue

                try:
                    translated_text = translator.translate(paragraph, dest=code).text
                except Exception as e:
                    translated_text = None
                    st.error(f"Translation to {name} failed: {e}")

                if translated_text:
                    st.markdown(f"**{name}** ({code})")
                    st.write(translated_text)
                    # Play audio (gTTS supports many codes but not all; try simplified forms)
                    gtts_code = normalize_gtts_code(code)
                    try:
                        read_aloud_streamlit(translated_text, lang=gtts_code)
                    except Exception as e:
                        st.warning(f"Audio skipped for {name} (lang {gtts_code}): {e}")

    st.markdown("---")
    st.subheader("Spell a word aloud")

    # Spell feature: input word and choose language for spelling voice
    word_to_spell = st.text_input("Word to spell (single word recommended):", "")
    # Provide smaller language selector for spelling voices (use same language names)
    spell_lang = st.selectbox("Spelling voice language (gTTS):", all_languages, index=all_languages.index("English") if "English" in all_languages else 0)

    if st.button("Spell Word Aloud"):
        w = word_to_spell.strip()
        if not w:
            st.info("Type a word to spell aloud.")
        else:
            code = display_map.get(spell_lang)
            gtts_code = normalize_gtts_code(code)
            try:
                audio_fp = spell_text_audio_bytes(w, lang=gtts_code)
                st.markdown(f"**Spelling**: `{w}` (voice: {spell_lang} / {gtts_code})")
                st.audio(audio_fp, format="audio/mp3")
            except Exception as e:
                st.error(f"Could not generate spelling audio: {e}")

# Note: Tips / Troubleshooting footer intentionally removed as requested.
