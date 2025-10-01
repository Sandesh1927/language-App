# app.py
import io
import base64
import streamlit as st
from gtts import gTTS
from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator, single_detection
import pycountry
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import nltk

# ---------- Ensure NLTK resources ----------
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
        if code and len(code) == 2:
            name = pycountry.languages.get(alpha_2=code)
            if name and getattr(name, "name", None):
                return name.name
    except Exception:
        pass
    return code

def add_bg_from_local(image_file):
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
        pass

def read_aloud_streamlit(text, lang="en"):
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        st.audio(mp3_fp, format="audio/mp3")
    except Exception as e:
        st.warning(f"Audio generation failed for lang='{lang}': {e}")

def generate_wordcloud_figure(text):
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
    if not code:
        return "en"
    gtts_code = code
    if "-" in code:
        gtts_code = code.split("-")[0]
    if gtts_code == "iw":
        return "he"
    if gtts_code == "in":
        return "id"
    return gtts_code

def spell_text_audio_bytes(word, lang="en"):
    dotted = ", ".join(list(word))
    gtts_lang = normalize_gtts_code(lang)
    tts = gTTS(text=dotted, lang=gtts_lang, slow=True)
    mp3_fp = io.BytesIO()
    tts.write_to_fp(mp3_fp)
    mp3_fp.seek(0)
    return mp3_fp

# ---------- Page layout ----------
st.set_page_config(page_title="Globalize", layout="wide")
add_bg_from_local("back.jpg")

st.title("Globalize — small multilingual helper")

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

    if st.button("Translate to English (if not already)"):
        if paragraph.strip():
            try:
                translated = GoogleTranslator(source='auto', target='en').translate(paragraph)
                st.subheader("Translated to English:")
                st.write(translated)
            except Exception as e:
                st.error(f"Translation failed: {e}")
        else:
            st.info("Type or paste a paragraph first.")

    if st.button("Generate Word Cloud"):
        if paragraph.strip():
            text_for_cloud = paragraph
            try:
                translated = GoogleTranslator(source='auto', target='en').translate(paragraph)
                text_for_cloud = translated
            except:
                pass
            try:
                fig = generate_wordcloud_figure(text_for_cloud)
                st.pyplot(fig)
            except Exception as e:
                st.error(f"Could not generate word cloud: {e}")
        else:
            st.info("Type or paste a paragraph first.")

with col2:
    st.subheader("Translate & read aloud")

    # Build a language dict from deep-translator supported languages
    deep_languages = {
        'ar':'Arabic','bn':'Bengali','cs':'Czech','da':'Danish','de':'German',
        'en':'English','es':'Spanish','fr':'French','hi':'Hindi','it':'Italian',
        'ja':'Japanese','ko':'Korean','ml':'Malayalam','mr':'Marathi','nl':'Dutch',
        'pa':'Punjabi','pt':'Portuguese','ru':'Russian','ta':'Tamil','te':'Telugu',
        'tr':'Turkish','uk':'Ukrainian','zh':'Chinese'
    }

    all_languages = list(deep_languages.values())
    select_all = st.checkbox("Select all languages", value=False)
    default_selection = all_languages if select_all else ["English"]

    target_languages = st.multiselect(
        "Select target languages (audio will attempt to play where supported):",
        all_languages,
        default=default_selection
    )

    if st.button("Translate & Read Aloud"):
        if not paragraph.strip():
            st.info("Type or paste a paragraph first.")
        else:
            for name in target_languages:
                code = [k for k,v in deep_languages.items() if v==name][0]
                try:
                    translated_text = GoogleTranslator(source='auto', target=code).translate(paragraph)
                    st.markdown(f"**{name}** ({code})")
                    st.write(translated_text)
                    read_aloud_streamlit(translated_text, lang=normalize_gtts_code(code))
                except Exception as e:
                    st.error(f"Translation to {name} failed: {e}")

    st.markdown("---")
    st.subheader("Spell a word aloud")
    word_to_spell = st.text_input("Word to spell (single word recommended):", "")
    spell_lang = st.selectbox("Spelling voice language:", all_languages, index=all_languages.index("English"))

    if st.button("Spell Word Aloud"):
        w = word_to_spell.strip()
        if not w:
            st.info("Type a word to spell aloud.")
        else:
            code = [k for k,v in deep_languages.items() if v==spell_lang][0]
            try:
                audio_fp = spell_text_audio_bytes(w, lang=normalize_gtts_code(code))
                st.markdown(f"**Spelling**: `{w}` (voice: {spell_lang} / {code})")
                st.audio(audio_fp, format="audio/mp3")
            except Exception as e:
                st.error(f"Could not generate spelling audio: {e}")
