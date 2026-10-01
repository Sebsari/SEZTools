# SEZDocs - Copyright (c) 2026 Mohammad Reza Sebzari
# Licensed under the GNU General Public License v3.0 (see LICENSE).
"""
SEZDocs - Offline Document Search Engine
===========================================
Part of SEZTools. 100% Local & Private PDF search application powered by Streamlit,
SentenceTransformers ('all-MiniLM-L6-v2'), FAISS vector indexing,
and PyTesseract OCR fallback.
"""

import os
import io
import sys
import glob
import html
import subprocess
from datetime import datetime
import pickle
import logging
import re
import shutil
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Safely import dependencies
try:
    import pypdf
except ImportError:
    st.error("Error: 'pypdf' package is not installed. Run: pip install pypdf")
    st.stop()

try:
    from sentence_transformers import SentenceTransformer
    import faiss
except ImportError:
    st.error("Error: 'sentence-transformers' or 'faiss-cpu' is missing. Run: pip install sentence-transformers faiss-cpu")
    st.stop()

try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


# ==========================================
# CONFIGURATION & PERSISTENCE PATHS
# ==========================================
st.set_page_config(
    page_title="SEZDocs - Offline Document Search Engine",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==========================================
# VISUAL THEME - SEZTools identity
# JetBrains Mono, SEZTools blue (#0B5FA5) on a light blueprint-grid background.
# The font file ships in ./static (served via enableStaticServing).
# ==========================================
def inject_custom_css():
    st.markdown("""
    <style>
    @font-face {
        font-family: 'JetBrains Mono';
        src: local('JetBrains Mono'), url('app/static/JetBrainsMono.ttf') format('truetype');
        font-weight: 100 800; font-display: swap;
    }
    :root {
        --bg:#E7EBEF; --surface:#FFFFFF; --surface2:#F3F5F7;
        --accent:#0B5FA5; --accent-dark:#084578;
        --ok:#256339; --warn:#A67A1E; --err:#9C3A32;
        --text:#1E2A33; --text-mid:#4A5A63; --text-muted:#8A9AA3;
        --border:#C7CDD3; --r-sm:6px; --r-md:10px;
    }
    html, body, .stApp,
    .stApp :where(p, label, span, div, input, textarea, button, li, h1, h2, h3, h4, th, td, a):not([data-testid="stIconMaterial"]) {
        font-family: 'JetBrains Mono', ui-monospace, Consolas, Menlo, monospace !important;
    }
    .stApp { background: var(--bg); color: var(--text); }
    [data-testid="stMain"], .main {
        background-image:
            linear-gradient(rgba(199,205,211,.35) 1px, transparent 1px),
            linear-gradient(90deg, rgba(199,205,211,.35) 1px, transparent 1px);
        background-size: 28px 28px;
    }
    [data-testid="stHeader"] { background: transparent; }
    #MainMenu, footer { visibility: hidden; }
    .block-container { padding-top: 2.2rem; max-width: 1240px; }

    /* Sidebar */
    [data-testid="stSidebar"] { background: var(--surface2); border-right: 1px solid var(--border); }
    [data-testid="stSidebar"] .block-container, [data-testid="stSidebarContent"] { padding-top: 1.2rem; }
    .sz-mark { display:inline-block; font-size:10px; font-weight:700; letter-spacing:4px; color:var(--accent);
               background:rgba(11,95,165,.08); padding:4px 9px; border-radius:var(--r-sm); }
    .sz-logo { font-size:26px; font-weight:700; letter-spacing:1px; margin:10px 0 2px; color:var(--text); }
    .sz-sub  { font-size:10px; color:var(--text-muted); letter-spacing:1.5px; text-transform:uppercase; margin-bottom:22px; }
    .sz-sec  { font-size:11px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:var(--text-mid); margin:6px 0 14px; }
    .sz-step { font-size:12px; font-weight:700; margin:16px 0 6px; color:var(--text); }
    .sz-status { background:rgba(37,99,57,.09); color:var(--ok); border-radius:var(--r-sm); padding:6px 10px; font-size:11px; margin:6px 0 4px; }
    .sz-total  { background:rgba(11,95,165,.08); color:var(--accent-dark); border:1px solid rgba(11,95,165,.25);
                 border-radius:var(--r-md); padding:9px 11px; font-size:11px; font-weight:600; margin:16px 0 12px; }
    .sz-row { font-size:11px; padding:8px 0; color:var(--text); word-break:break-all; }

    /* Main header */
    .sz-title { font-size:36px; font-weight:700; letter-spacing:1px; color:var(--text); margin:0 0 2px; }
    .sz-h2    { font-size:17px; font-weight:700; margin:0 0 6px; color:var(--text); }
    .sz-tag   { font-size:11px; color:var(--text-muted); letter-spacing:1.5px; text-transform:uppercase; margin-bottom:16px; }
    .sz-page  { text-align:right; font-weight:600; color:var(--text-muted); padding-top:8px; font-size:12px; }
    .sz-snip  { background:var(--surface2); border-radius:var(--r-sm); padding:10px 12px; color:var(--text-mid); line-height:1.7; font-size:12px; }
    .sz-dots  { font-size:11px; color:var(--text-mid); margin:2px 0 12px; }

    /* Controls */
    .stApp [data-testid^="stBaseButton"] { border-radius:var(--r-sm); font-weight:700; letter-spacing:.5px; min-height:42px; }
    .stApp [data-testid="stBaseButton-primary"] { background:var(--accent) !important; border-color:var(--accent) !important; color:#fff !important; }
    .stApp [data-testid="stBaseButton-primary"]:hover { background:var(--accent-dark) !important; }
    .stApp [data-testid="stBaseButton-secondary"] { background:var(--surface); color:var(--accent); border:1px solid var(--accent); }
    .stApp [data-testid="stBaseButton-secondary"]:hover { background:rgba(11,95,165,.08); }
    .stApp [data-testid^="stBaseButton"]:disabled { opacity:.45; }
    [data-baseweb="input"], [data-baseweb="select"] > div { border-radius:var(--r-md) !important; background:var(--surface) !important; }
    [data-testid="stFileUploaderDropzone"] { background:var(--surface); border:1px solid var(--border); border-radius:var(--r-md); }
    [data-testid="stAlert"] { border-radius:var(--r-md); }
    [data-testid="stVerticalBlockBorderWrapper"] { border-radius:var(--r-md) !important; border-color:var(--border) !important; background:var(--surface); }
    [data-testid="stDataFrame"] { border:1px solid var(--border); border-radius:var(--r-md); }

    @media (max-width: 640px) {
        .sz-title { font-size:26px; }
        .block-container { padding-left:1rem; padding-right:1rem; }
    }
    </style>
    """, unsafe_allow_html=True)


APP_ROOT_DIR = Path(__file__).resolve().parent
_POPPLER_CONFIG_FILE = APP_ROOT_DIR / "poppler_path.txt"


def get_poppler_bin_path() -> str | None:
    """Finds the Poppler bin folder INSTALL_WINDOWS.bat set up.

    Checked in order: the config file the installer writes next to app.py
    (most reliable - unaffected by stale Explorer/shortcut environments),
    then the SEZDOCS_POPPLER_BIN env var, then None (fall back to whatever
    Poppler is on the system PATH).
    """
    if _POPPLER_CONFIG_FILE.exists():
        try:
            configured = _POPPLER_CONFIG_FILE.read_text(encoding="utf-8").strip()
            if configured and os.path.isdir(configured):
                return configured
        except Exception as e:
            logging.warning(f"Could not read {_POPPLER_CONFIG_FILE}: {e}")
    return os.environ.get("SEZDOCS_POPPLER_BIN") or None


POPPLER_BIN_PATH = get_poppler_bin_path()

BASE_APP_DIR = Path.home() / ".my_offline_search_app"
ACTIVE_INDEX_DIR = BASE_APP_DIR / "active_index"
PROFILES_DIR = BASE_APP_DIR / "profiles"
UPLOAD_DIR = BASE_APP_DIR / "uploaded_docs"

ACTIVE_INDEX_DIR.mkdir(parents=True, exist_ok=True)
PROFILES_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

INDEX_FILE = ACTIVE_INDEX_DIR / "faiss.index"
METADATA_FILE = ACTIVE_INDEX_DIR / "metadata.pkl"
FILE_STATS_FILE = ACTIVE_INDEX_DIR / "file_stats.pkl"
MODEL_NAME = "all-MiniLM-L6-v2"


# ==========================================
# AUTOMATIC TESSERACT DETECTION
# ==========================================
def auto_detect_tesseract() -> str | None:
    """Automatically detects Tesseract executable path without user intervention."""
    if not OCR_AVAILABLE:
        return None
    
    # Check common installation paths
    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        str(Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tesseract.exe")
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
            
    # Check if available in system PATH
    tesseract_in_path = shutil.which("tesseract")
    if tesseract_in_path:
        return tesseract_in_path
        
    return None

TESSERACT_CMD = auto_detect_tesseract()
if TESSERACT_CMD and OCR_AVAILABLE:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


def detect_ocr_languages() -> list[str]:
    """Returns the list of language packs actually installed in this Tesseract,
    e.g. ['eng', 'fas', 'osd']. Empty list if Tesseract isn't reachable."""
    if not (OCR_AVAILABLE and TESSERACT_CMD):
        return []
    try:
        return pytesseract.get_languages(config="")
    except Exception as e:
        logging.warning(f"Could not query installed Tesseract languages: {e}")
        return []


INSTALLED_OCR_LANGS = detect_ocr_languages()

# Documents in this app are commonly a mix of Persian and English text.
# Tesseract only ships with 'eng' by default - 'fas' (Farsi) has to be
# installed separately (see BUILD_WINDOWS_EXE.md / INSTALL_WINDOWS.bat),
# otherwise every Persian scan silently comes back empty.
_WANTED_OCR_LANGS = ["fas", "eng"]
OCR_LANG = "+".join(l for l in _WANTED_OCR_LANGS if l in INSTALLED_OCR_LANGS) or None
OCR_MISSING_FAS = OCR_AVAILABLE and TESSERACT_CMD and "fas" not in INSTALLED_OCR_LANGS


# ==========================================
# CACHED MODEL & HELPER FUNCTIONS
# ==========================================
@st.cache_resource(show_spinner=False)
def get_embedding_model():
    """Load and cache the SentenceTransformer model locally."""
    return SentenceTransformer(MODEL_NAME)


def extract_smart_snippet(text: str, query: str, context_lines: int = 2, plain: bool = False) -> str:
    """
    Extracts the lines around the best keyword match. With plain=False the result is
    HTML-safe with matched words highlighted; plain=True returns raw text (for PDF reports).
    """
    def _fmt(s: str) -> str:
        return s if plain else html.escape(s)

    if not query.strip() or not text.strip():
        return _fmt(text[:250]) + ("..." if len(text) > 250 else "")

    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return ""

    words = [re.escape(w) for w in re.findall(r'\w+', query.lower()) if len(w) > 1]
    if not words:
        return _fmt(text[:250]) + ("..." if len(text) > 250 else "")

    pattern = re.compile(r'(' + '|'.join(words) + r')', re.IGNORECASE)

    best_line_idx = 0
    max_matches = 0
    for idx, line in enumerate(lines):
        matches = len(pattern.findall(line))
        if matches > max_matches:
            max_matches = matches
            best_line_idx = idx

    start = max(0, best_line_idx - 1)
    end = min(len(lines), best_line_idx + context_lines + 1)
    raw_snippet = " ".join(lines[start:end])

    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(lines) else ""
    if plain:
        return f"{prefix}{raw_snippet}{suffix}"

    highlighted = pattern.sub(
        r'<mark style="background-color:#f6e3a8; color:#1E2A33; padding:0 3px; border-radius:3px; font-weight:700;">\1</mark>',
        html.escape(raw_snippet),
    )
    return f"{prefix}{highlighted}{suffix}"


def extract_text_from_pdf_page(pdf_path: str, page_idx: int, page_obj) -> tuple[str, str]:
    """Extracts text from a single PDF page with automatic OCR fallback."""
    try:
        raw_text = page_obj.extract_text() or ""
        cleaned = raw_text.strip()
        if len(cleaned) > 20:
            return cleaned, "direct"
    except Exception as e:
        logging.warning(f"Direct extraction failed for {pdf_path} [p.{page_idx+1}]: {e}")

    if OCR_AVAILABLE and TESSERACT_CMD:
        try:
            images = convert_from_path(
                pdf_path,
                first_page=page_idx + 1,
                last_page=page_idx + 1,
                dpi=150,
                poppler_path=POPPLER_BIN_PATH,
            )
            if images:
                try:
                    ocr_text = pytesseract.image_to_string(images[0], lang=OCR_LANG) or ""
                except pytesseract.TesseractError as lang_err:
                    # Usually means a requested language pack (e.g. 'fas') isn't
                    # installed. Fall back to whatever Tesseract's default is
                    # rather than losing the page entirely.
                    logging.warning(
                        f"OCR with lang='{OCR_LANG}' failed for {pdf_path} [p.{page_idx+1}]: {lang_err}. "
                        f"Falling back to default language."
                    )
                    ocr_text = pytesseract.image_to_string(images[0]) or ""
                cleaned_ocr = ocr_text.strip()
                if cleaned_ocr:
                    return cleaned_ocr, "ocr"
        except Exception as ocr_err:
            logging.warning(f"OCR failed for {pdf_path} [p.{page_idx+1}]: {ocr_err}")

    return "", "empty"


def parse_pdf_document(pdf_path: str) -> tuple[list[dict], dict]:
    """Parses all pages of a PDF document."""
    documents = []
    file_name = os.path.basename(pdf_path)
    file_stat = {
        "file_name": file_name,
        "file_path": str(Path(pdf_path).resolve()),
        "total_pages": 0,
        "direct_pages": 0,
        "ocr_pages": 0,
        "empty_pages": 0,
        "readability_score": "🔴 Unreadable",
        "status_code": "red",
    }

    try:
        file_stat["size"], file_stat["mtime_ns"] = _file_signature(str(Path(pdf_path).resolve()))
    except OSError:
        pass

    try:
        reader = pypdf.PdfReader(pdf_path)
        total_pages = len(reader.pages)
        file_stat["total_pages"] = total_pages

        direct_cnt = 0
        ocr_cnt = 0
        empty_cnt = 0

        for page_idx in range(total_pages):
            page_obj = reader.pages[page_idx]
            text, method = extract_text_from_pdf_page(pdf_path, page_idx, page_obj)

            if method == "direct":
                direct_cnt += 1
            elif method == "ocr":
                ocr_cnt += 1
            else:
                empty_cnt += 1

            if text:
                documents.append({
                    "file_name": file_name,
                    "file_path": str(Path(pdf_path).resolve()),
                    "page_num": page_idx + 1,
                    "total_pages": total_pages,
                    "text": text,
                    "method": method,
                })

        file_stat["direct_pages"] = direct_cnt
        file_stat["ocr_pages"] = ocr_cnt
        file_stat["empty_pages"] = empty_cnt

        read_pages = direct_cnt + ocr_cnt
        if total_pages > 0:
            if read_pages == total_pages:
                file_stat["readability_score"] = "🟢 Fully Read"
                file_stat["status_code"] = "green"
            elif read_pages > 0:
                file_stat["readability_score"] = "🟡 Partially Read"
                file_stat["status_code"] = "yellow"
            else:
                file_stat["readability_score"] = "🔴 Unreadable / Bad Scan"
                file_stat["status_code"] = "red"

    except Exception as err:
        logging.error(f"Failed to read PDF file {pdf_path}: {err}")

    return documents, file_stat


# ==========================================
# INDEX & METADATA STORAGE
# ==========================================
def save_active_index(index, metadata: list[dict], file_stats: list[dict]):
    """Persists FAISS index, metadata, and file stats to active index directory."""
    faiss.write_index(index, str(INDEX_FILE))
    with open(METADATA_FILE, "wb") as f:
        pickle.dump(metadata, f)
    with open(FILE_STATS_FILE, "wb") as f:
        pickle.dump(file_stats, f)


def load_active_index():
    """Loads active index, metadata, and file stats from disk."""
    if INDEX_FILE.exists() and METADATA_FILE.exists():
        try:
            index = faiss.read_index(str(INDEX_FILE))
            with open(METADATA_FILE, "rb") as f:
                metadata = pickle.load(f)
            file_stats = []
            if FILE_STATS_FILE.exists():
                with open(FILE_STATS_FILE, "rb") as f:
                    file_stats = pickle.load(f)
            return index, metadata, file_stats
        except Exception as e:
            logging.error(f"Error loading active index: {e}")
            return None, None, []
    return None, None, []


ACTIVE_NAME_FILE = ACTIVE_INDEX_DIR / "active_name.txt"


def get_active_index_name() -> str | None:
    try:
        return ACTIVE_NAME_FILE.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def set_active_index_name(name: str | None):
    try:
        if name:
            ACTIVE_NAME_FILE.write_text(name, encoding="utf-8")
        elif ACTIVE_NAME_FILE.exists():
            ACTIVE_NAME_FILE.unlink()
    except OSError:
        pass


def clear_active_index():
    for f in (INDEX_FILE, METADATA_FILE, FILE_STATS_FILE):
        if f.exists():
            os.remove(f)
    set_active_index_name(None)


def _file_signature(path: str) -> tuple[int, int]:
    st_ = os.stat(path)
    return st_.st_size, st_.st_mtime_ns


# ==========================================
# INDEX PROFILE MANAGEMENT
# ==========================================
def list_saved_profiles() -> list[str]:
    """Returns list of saved profile names."""
    if not PROFILES_DIR.exists():
        return []
    profiles = [p.name for p in PROFILES_DIR.iterdir() if p.is_dir() and (p / "faiss.index").exists()]
    return sorted(profiles)


def _clean_profile_name(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name or "").strip()


def save_profile(profile_name: str) -> str | None:
    """Saves the active index as a named index. Returns the stored name, or None on failure."""
    name = _clean_profile_name(profile_name)
    if not name or not INDEX_FILE.exists():
        return None
    target_p_dir = PROFILES_DIR / name
    target_p_dir.mkdir(parents=True, exist_ok=True)
    for src, dst in ((INDEX_FILE, "faiss.index"), (METADATA_FILE, "metadata.pkl"), (FILE_STATS_FILE, "file_stats.pkl")):
        if src.exists():
            shutil.copy(src, target_p_dir / dst)
    return name


def load_profile(profile_name: str) -> bool:
    """Loads named profile into active index."""
    src_p_dir = PROFILES_DIR / profile_name
    if not src_p_dir.exists() or not (src_p_dir / "faiss.index").exists():
        return False
    
    shutil.copy(src_p_dir / "faiss.index", INDEX_FILE)
    shutil.copy(src_p_dir / "metadata.pkl", METADATA_FILE)
    if (src_p_dir / "file_stats.pkl").exists():
        shutil.copy(src_p_dir / "file_stats.pkl", FILE_STATS_FILE)
    return True


# ==========================================
# BUILDING / UPDATING THE ACTIVE INDEX
# ==========================================
def build_faiss_vector_index(pdf_sources: list[str]):
    """
    Adds the selected PDFs to the active index (creating it if none exists).
    Files already indexed and unchanged (same path, size, modified time) are skipped;
    changed files are re-processed and replace their old pages.
    Returns (index, metadata, file_stats, n_processed, n_skipped).
    """
    existing_idx, existing_meta, existing_stats = load_active_index()
    existing_meta = list(existing_meta or [])
    existing_stats = list(existing_stats or [])
    known = {s["file_path"]: s for s in existing_stats}

    to_process, skipped = [], 0
    for p in pdf_sources:
        try:
            rp = str(Path(p).resolve())
            size, mtime_ns = _file_signature(rp)
        except OSError:
            continue
        old = known.get(rp)
        if old and old.get("size") == size and old.get("mtime_ns") == mtime_ns:
            skipped += 1
        else:
            to_process.append(rp)

    if not to_process:
        st.info(f"All {skipped} selected file(s) are already indexed - nothing new to process.")
        return existing_idx, existing_meta, existing_stats, 0, skipped

    status_box = st.status("Processing and indexing PDFs ...", expanded=True)
    progress_bar = st.progress(0.0)

    new_docs, new_stats = [], []
    for i, pdf_path in enumerate(to_process):
        status_box.write(f"📄 ({i+1}/{len(to_process)}) {os.path.basename(pdf_path)}")
        docs, stat = parse_pdf_document(pdf_path)
        new_docs.extend(docs)
        new_stats.append(stat)
        progress_bar.progress((i + 1) / len(to_process))

    if not new_docs:
        status_box.update(label="❌ No readable text extracted from the selected files.", state="error")
        return existing_idx, existing_meta, existing_stats, 0, skipped

    # Drop old pages of files that are being re-processed (changed on disk)
    replaced = {s["file_path"] for s in new_stats} & set(known)
    if replaced and existing_idx is not None:
        drop = [i for i, m in enumerate(existing_meta) if m["file_path"] in replaced]
        if drop:
            existing_idx.remove_ids(np.array(drop, dtype=np.int64))
        existing_meta = [m for m in existing_meta if m["file_path"] not in replaced]
        existing_stats = [s for s in existing_stats if s["file_path"] not in replaced]

    status_box.write(f"🧠 Generating embeddings for {len(new_docs)} pages...")
    model = get_embedding_model()
    embeddings = model.encode([d["text"] for d in new_docs], show_progress_bar=False, normalize_embeddings=True)
    vectors = np.array(embeddings, dtype=np.float32)

    faiss_index = existing_idx if existing_idx is not None else faiss.IndexFlatIP(vectors.shape[1])
    faiss_index.add(vectors)
    combined_meta = existing_meta + new_docs
    combined_stats = existing_stats + new_stats

    save_active_index(faiss_index, combined_meta, combined_stats)
    status_box.update(
        label=f"✅ Done - {len(to_process)} file(s) indexed, {skipped} skipped (already indexed). Total pages: {len(combined_meta)}",
        state="complete",
    )
    return faiss_index, combined_meta, combined_stats, len(to_process), skipped


# ==========================================
# SEARCH LOGIC
# ==========================================
def calculate_keyword_score(text: str, query: str) -> float:
    words = re.findall(r'\w+', query.lower())
    if not words:
        return 0.0
    text_lower = text.lower()
    matched_words = sum(1 for w in words if w in text_lower)
    word_ratio = matched_words / len(words)
    phrase_bonus = 0.2 if query.lower() in text_lower else 0.0
    return min(1.0, word_ratio + phrase_bonus) * 100.0


def execute_search(query: str, search_type: str, index, metadata: list[dict], model, top_k: int = 15) -> list[dict]:
    results = []
    query_clean = query.strip()
    if not query_clean or not metadata:
        return results

    query_vec = model.encode([query_clean], normalize_embeddings=True).astype(np.float32)
    semantic_scores_all, semantic_indices_all = index.search(query_vec, len(metadata))

    # FAISS returns results ranked by score, not in original document order -
    # map each document index back to its own score instead of assuming
    # position idx in the results corresponds to metadata[idx].
    sem_score_by_doc_idx = {
        int(doc_idx): max(0.0, float(score)) * 100.0
        for doc_idx, score in zip(semantic_indices_all[0], semantic_scores_all[0])
    }

    for idx, doc in enumerate(metadata):
        sem_score = sem_score_by_doc_idx.get(idx, 0.0)
        kw_score = calculate_keyword_score(doc["text"], query_clean)

        if "Semantic" in search_type:
            final_score = sem_score
        elif "Keyword" in search_type:
            final_score = kw_score
        else:  # Hybrid
            final_score = 0.6 * sem_score + 0.4 * kw_score

        if final_score > 5.0:
            res = dict(doc)
            res["score"] = final_score
            results.append(res)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


# ==========================================
# PDF REPORT (search results export)
# ==========================================
_REPORT_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\tahoma.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
]
_RTL_RE = re.compile(r"[\u0590-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")


def _register_report_font() -> str:
    """Registers a system TrueType font that covers both Latin and Persian/Arabic script."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    if "SEZReport" in pdfmetrics.getRegisteredFontNames():
        return "SEZReport"
    for path in _REPORT_FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("SEZReport", path))
                return "SEZReport"
            except Exception as e:
                logging.warning(f"Report font {path} failed: {e}")
    return "Helvetica"  # Persian text will not render with this fallback


def _visual(line: str) -> str:
    """Shapes + reorders Persian/Arabic text for left-to-right PDF drawing."""
    if not _RTL_RE.search(line):
        return line
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(line))
    except Exception:
        return line


def build_report_pdf(query: str, search_type: str, index_name: str, results: list[dict]) -> bytes:
    """Builds a PDF report of the current search results and returns its bytes."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.colors import HexColor
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase.pdfmetrics import stringWidth

    font = _register_report_font()
    BLUE, INK, MUTED, PANEL = HexColor("#0B5FA5"), HexColor("#1E2A33"), HexColor("#8A9AA3"), HexColor("#F3F5F7")
    W, H = A4
    M = 46
    text_w = W - 2 * M

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle("SEZDocs Search Report")
    state = {"y": H - M, "page": 1}

    def clean(s: str) -> str:
        return "".join(ch for ch in s if ch.isprintable() or ch == " ")

    def footer():
        c.setFont(font, 8)
        c.setFillColor(MUTED)
        c.drawString(M, 26, "SEZDocs - SEZTools offline search")
        c.drawRightString(W - M, 26, f"Page {state['page']}")

    def new_page():
        footer()
        c.showPage()
        state["page"] += 1
        state["y"] = H - M

    def wrap(text: str, size: int, width: float) -> list[str]:
        lines, cur = [], ""
        for word in clean(text).split():
            trial = f"{cur} {word}".strip()
            if stringWidth(trial, font, size) <= width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines or [""]

    def draw_line(line: str, x_left: float, y: float, size: int, width: float):
        c.setFont(font, size)
        if _RTL_RE.search(line):
            c.drawRightString(x_left + width, y, _visual(line))
        else:
            c.drawString(x_left, y, line)

    # ---- header block
    c.setFillColor(BLUE)
    c.setFont(font, 9)
    c.drawString(M, state["y"], "S E Z T O O L S")
    state["y"] -= 26
    c.setFillColor(INK)
    c.setFont(font, 22)
    c.drawString(M, state["y"], "SEZDocs - Search Report")
    state["y"] -= 12
    c.setStrokeColor(BLUE)
    c.setLineWidth(1.5)
    c.line(M, state["y"], W - M, state["y"])
    state["y"] -= 20

    meta = [
        ("Query", query),
        ("Search type", search_type),
        ("Index", index_name or "Unsaved index"),
        ("Date", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ("Results", str(len(results))),
    ]
    for label, value in meta:
        c.setFillColor(MUTED)
        c.setFont(font, 9)
        c.drawString(M, state["y"], label)
        c.setFillColor(INK)
        draw_line(clean(value), M + 80, state["y"], 10, text_w - 80)
        state["y"] -= 15
    state["y"] -= 10

    # ---- results
    size, leading, pad = 9.5, 13.5, 8
    for n, res in enumerate(results, 1):
        snippet = extract_smart_snippet(res["text"], query, context_lines=4, plain=True)
        body = wrap(snippet, size, text_w - 2 * pad)
        block_h = 18 + 12 + len(body) * leading + 2 * pad + 8
        if state["y"] - block_h < M + 20:
            new_page()

        name = clean(res["file_name"])
        while stringWidth(name, font, 11) > text_w - 70 and len(name) > 8:
            name = name[:-2]
        c.setFillColor(BLUE)
        c.setFont(font, 11)
        c.drawString(M, state["y"], f"{n}.")
        c.drawString(M + 22, state["y"], _visual(name))
        c.setFillColor(MUTED)
        c.drawRightString(W - M, state["y"], f"Page {res['page_num']}")
        state["y"] -= 12
        c.setFont(font, 7.5)
        path_txt = clean(str(res["file_path"]))
        while stringWidth(path_txt, font, 7.5) > text_w and len(path_txt) > 12:
            path_txt = "..." + path_txt[4:]
        c.drawString(M, state["y"], _visual(path_txt))
        state["y"] -= 8

        panel_h = len(body) * leading + 2 * pad
        c.setFillColor(PANEL)
        c.roundRect(M, state["y"] - panel_h, text_w, panel_h, 4, stroke=0, fill=1)
        c.setFillColor(INK)
        ty = state["y"] - pad - size
        for ln in body:
            draw_line(ln, M + pad, ty, size, text_w - 2 * pad)
            ty -= leading
        state["y"] -= panel_h + 16

    footer()
    c.showPage()
    c.save()
    return buf.getvalue()


# ==========================================
# HELPERS FOR THE SIDEBAR
# ==========================================
def scan_folder_pdfs(folder: str) -> list[str]:
    found = []
    for root, _, files in os.walk(folder):
        for name in files:
            if name.lower().endswith(".pdf"):
                found.append(os.path.join(root, name))
    return found


def pick_folder_dialog() -> tuple[str | None, bool]:
    """Native folder picker in a separate process (keeps Tk away from Streamlit's threads).
    Returns (path or None if cancelled, picker_available)."""
    if getattr(sys, "frozen", False):
        return None, False
    code = (
        "import tkinter as tk\nfrom tkinter import filedialog\n"
        "r = tk.Tk(); r.withdraw(); r.attributes('-topmost', True)\n"
        "print(filedialog.askdirectory(title='Select a folder with PDFs') or '')"
    )
    try:
        out = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True,
            encoding="utf-8", timeout=600, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        if out.returncode != 0:
            return None, False
        path = out.stdout.strip()
        return (path or None), True
    except Exception:
        return None, False



def relabel_upload_button():
    """Cosmetic only: the file uploader's built-in button says 'Upload', which reads as
    'goes to the internet'. Everything is local, so relabel it to 'Browse' in the DOM."""
    components.html("""
    <script>
    const relabel = () => {
        const doc = window.parent.document;
        doc.querySelectorAll('[data-testid="stFileUploaderDropzone"] button').forEach(btn => {
            btn.querySelectorAll('*').forEach(n => {
                if (n.children.length === 0 && n.textContent.trim() === 'Upload') {
                    n.textContent = 'Browse';
                }
            });
        });
    };
    relabel();
    new MutationObserver(relabel).observe(window.parent.document.body, {childList: true, subtree: true});
    </script>
    """, height=0, width=0)


# ==========================================
# MAIN APPLICATION
# ==========================================
def main():
    inject_custom_css()
    relabel_upload_button()
    ss = st.session_state
    ss.setdefault("folder_paths", [])
    ss.setdefault("folder_scan", {})
    ss.setdefault("uploader_key", 0)
    ss.setdefault("idx_key", 0)
    ss.setdefault("folder_fallback", False)
    ss.setdefault("did_search", False)
    ss.setdefault("last_query", None)
    ss.setdefault("report_cache", None)   # (cache_key, pdf_bytes)
    ss.setdefault("report_ready", None)   # cache_key the user actually confirmed via a Report click
    if ss.get("flash"):
        st.toast(ss.pop("flash"))

    index, metadata, file_stats = load_active_index()
    has_index = index is not None and bool(metadata)
    active_name = get_active_index_name() if has_index else None

    # ---------------------------------- SIDEBAR
    with st.sidebar:
        st.markdown(
            '<span class="sz-mark">SEZTOOLS</span><div class="sz-logo">SEZDocs</div>'
            '<div class="sz-sub">Offline Search Tools</div>', unsafe_allow_html=True)

        if not OCR_AVAILABLE:
            st.warning("OCR libraries not installed - scanned PDFs won't be readable.")
        elif not TESSERACT_CMD:
            st.warning("Tesseract not found - scanned PDFs won't be OCR'd.")
        elif OCR_MISSING_FAS:
            st.warning("Persian (fas) OCR language pack missing - run INSTALL_WINDOWS.bat again.")

        st.markdown('<div class="sz-sec">Insert Sources</div>', unsafe_allow_html=True)

        # 1. Files
        st.markdown('<div class="sz-step">1. Select Files</div>', unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            "PDF files", type=["pdf"], accept_multiple_files=True,
            key=f"pdf_uploader_{ss.uploader_key}", label_visibility="collapsed")
        saved_uploaded_paths = []
        for uf in uploaded_files or []:
            save_path = UPLOAD_DIR / uf.name
            data = uf.getbuffer()
            if not save_path.exists() or save_path.stat().st_size != len(data):
                with open(save_path, "wb") as f:  # only rewrite when content differs (keeps mtime stable)
                    f.write(data)
            saved_uploaded_paths.append(str(save_path.resolve()))
        if saved_uploaded_paths:
            st.markdown(f'<div class="sz-status">{len(saved_uploaded_paths)} files added</div>', unsafe_allow_html=True)

        # 2. Directories
        st.markdown('<div class="sz-step">2. Select Directories</div>', unsafe_allow_html=True)
        if st.button("＋ Add folder", key="add_folder", use_container_width=True):
            path, available = pick_folder_dialog()
            if not available:
                ss.folder_fallback = True
            elif path and path not in ss.folder_paths:
                ss.folder_paths.append(path)
                ss.folder_scan[path] = scan_folder_pdfs(path)
        if ss.folder_fallback:
            typed = st.text_input("Folder path", placeholder="C:\\Path\\To\\PDFs", key="dir_path_input")
            if st.button("Add", key="add_typed_folder") and typed:
                if os.path.isdir(typed):
                    if typed not in ss.folder_paths:
                        ss.folder_paths.append(typed)
                        ss.folder_scan[typed] = scan_folder_pdfs(typed)
                    st.rerun()
                else:
                    st.error("Invalid directory path.")
        for i, folder in enumerate(list(ss.folder_paths)):
            c_a, c_b = st.columns([6, 1])
            c_a.markdown(f'<div class="sz-row">{html.escape(folder)}</div>', unsafe_allow_html=True)
            if c_b.button("✕", key=f"rm_dir_{i}"):
                ss.folder_paths.remove(folder)
                ss.folder_scan.pop(folder, None)
                st.rerun()
        folder_pdfs = [p for f in ss.folder_paths for p in ss.folder_scan.get(f, [])]
        if ss.folder_paths:
            st.markdown(
                f'<div class="sz-status">{len(ss.folder_paths)} folders · {len(set(folder_pdfs))} PDFs found</div>',
                unsafe_allow_html=True)

        # 3. Index
        st.markdown('<div class="sz-step">3. Select Index</div>', unsafe_allow_html=True)
        profiles = list_saved_profiles()
        choice = st.selectbox(
            "Saved index", profiles, disabled=not profiles,
            index=profiles.index(active_name) if active_name in profiles else None,
            placeholder="Choose a saved index" if profiles else "No saved indexes yet",
            key=f"sel_index_{ss.idx_key}", label_visibility="collapsed")
        if choice and choice != active_name:
            if load_profile(choice):
                set_active_index_name(choice)
                ss.idx_key += 1
                ss.did_search, ss.last_query, ss.report_cache, ss.report_ready = False, None, None, None
                st.rerun()
            else:
                st.error("Failed to load index.")
        if has_index:
            st.markdown(
                f'<div class="sz-status">{html.escape(active_name or "Unsaved index")} · {len(file_stats)} files</div>',
                unsafe_allow_html=True)
            if not active_name and profiles:
                st.caption("Unsaved index - choosing another one replaces it. Use Save Index first.")

        # Collect sources
        all_pdf_sources = list(dict.fromkeys(saved_uploaded_paths + folder_pdfs))
        if all_pdf_sources:
            st.markdown(f'<div class="sz-total">Total selected PDFs: {len(all_pdf_sources)}</div>', unsafe_allow_html=True)

        if st.button("🚀 Process & Index Documents", type="primary", use_container_width=True, key="btn_process"):
            if not all_pdf_sources:
                st.error("Please add PDF files or folders first.")
            else:
                sources = list(dict.fromkeys(saved_uploaded_paths + [p for f in ss.folder_paths for p in scan_folder_pdfs(f)]))
                new_idx, _, _, done, skipped = build_faiss_vector_index(sources)
                if new_idx is not None:
                    if active_name:
                        save_profile(active_name)  # keep the selected saved index up to date
                    ss.flash = (f"{done} file(s) indexed, {skipped} already indexed and skipped."
                                if done else f"All {skipped} file(s) were already indexed.")
                    ss.folder_paths, ss.folder_scan = [], {}
                    ss.uploader_key += 1
                    st.rerun()

    # ---------------------------------- MAIN AREA
    st.markdown('<div class="sz-title">SEZDocs</div><div class="sz-h2">Offline Search in Document Text</div>'
                '<div class="sz-tag">100% Private Local Search • FAISS Vector Engine • PyTesseract OCR • Hybrid Search</div>',
                unsafe_allow_html=True)
    st.divider()

    col_q, col_t, col_s, col_r = st.columns([5, 2.6, 1.2, 1.2])
    with col_q:
        query_input = st.text_input("Search Query", placeholder="Type keywords or a concept...",
                                    label_visibility="collapsed", disabled=not has_index)
    with col_t:
        search_type = st.selectbox("Search Type", ["Semantic (Concept)", "Keyword (Exact Match)", "Hybrid (Recommended)"],
                                   index=1, label_visibility="collapsed", disabled=not has_index)
    q = query_input.strip()

    with col_s:
        search_clicked = st.button("Search", type="primary", use_container_width=True,
                                   disabled=not has_index, key="btn_search")

    # Only a real click on Search (not typing, not clicking elsewhere) reveals results.
    # Editing the query after a search hides the old results again until Search is clicked.
    if search_clicked and q:
        ss.did_search, ss.last_query = True, q
    elif q != ss.last_query:
        ss.did_search = False
    searching = has_index and ss.did_search and bool(q)
    results = execute_search(q, search_type, index, metadata, get_embedding_model(), top_k=15) if searching else []

    with col_r:
        cache_key = (q, search_type, active_name, tuple((r["file_path"], r["page_num"]) for r in results)) if results else None
        # Two-step on purpose: a download_button that FIRST appears on a rerun the user didn't
        # trigger by clicking it (e.g. the Search rerun) can fire the download by itself in some
        # browsers. So the real download_button is only ever created on the rerun caused by this
        # very Report click - never as a side effect of Search.
        if cache_key and ss.report_ready == cache_key and ss.report_cache and ss.report_cache[0] == cache_key:
            safe_q = re.sub(r"[^A-Za-z0-9]+", "_", q).strip("_")[:40] or "report"
            st.download_button("Report", data=ss.report_cache[1], use_container_width=True, key="dl_report",
                               file_name=f"SEZDocs_Report_{safe_q}.pdf", mime="application/pdf")
        else:
            if st.button("Report", disabled=not cache_key, use_container_width=True, key="btn_report"):
                try:
                    ss.report_cache = (cache_key, build_report_pdf(q, search_type, active_name or "", results))
                    ss.report_ready = cache_key
                except Exception as e:
                    logging.error(f"Report generation failed: {e}")
                    st.error("Could not build the report.")
                st.rerun()

    # Index management: always visible once there is an index, independent of search state
    if has_index:
        h1, h2, h3 = st.columns([4, 1.3, 1.3])
        h1.markdown(f'<div class="sz-h2">Index: {html.escape(active_name or "Unsaved")}</div>', unsafe_allow_html=True)
        with h2.popover("Save Index", use_container_width=True):
            new_name = st.text_input("Index name", value=active_name or "", placeholder="e.g. Utility",
                                     key=f"save_name_{ss.idx_key}")
            if st.button("Save", type="primary", use_container_width=True, key="do_save"):
                saved = save_profile(new_name)
                if saved:
                    set_active_index_name(saved)
                    ss.idx_key += 1
                    st.rerun()
                else:
                    st.error("Enter a valid name.")
        if h3.button("Clear Index", use_container_width=True, key="clear_index"):
            clear_active_index()
            ss.idx_key += 1
            ss.did_search, ss.last_query, ss.report_cache, ss.report_ready = False, None, None, None
            st.rerun()

    if not has_index:
        if not all_pdf_sources:
            st.info("💡 Welcome! No document index loaded yet.")
            st.markdown("**Get started in 2 easy steps:**\n\n"
                        "1. Use the **Insert Sources** sidebar to add PDF files or folders.\n"
                        "2. Click **Process & Index Documents** to run extraction, OCR and FAISS indexing.")
    elif not searching:
        green = sum(1 for f in file_stats if f["status_code"] == "green")
        yellow = sum(1 for f in file_stats if f["status_code"] == "yellow")
        red = sum(1 for f in file_stats if f["status_code"] == "red")
        st.markdown(f'<div class="sz-dots">{len(file_stats)} files · 🟢 {green} fully read · 🟡 {yellow} partial · 🔴 {red} unreadable</div>',
                    unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([{
            "Status": f["readability_score"], "File": f["file_name"], "Pages": f["total_pages"],
            "Extraction": f"{f['direct_pages']} direct / {f['ocr_pages']} OCR / {f['empty_pages']} empty",
        } for f in file_stats]), use_container_width=True, hide_index=True)
    else:
        st.markdown(f'<div class="sz-h2">Results for “{html.escape(q)}” ({len(results)})</div>', unsafe_allow_html=True)
        if not results:
            st.info("No matching content found for your query.")
        for idx, res in enumerate(results):
            with st.container(border=True):
                c_link, c_page = st.columns([4, 1])
                with c_link:
                    if st.button(f"📄 {res['file_name']}", key=f"open_file_{idx}"):
                        try:
                            if os.name == "nt":
                                os.startfile(res["file_path"])
                                st.toast(f"Opening {res['file_name']}...")
                            else:
                                st.warning(f"File path: {res['file_path']}")
                        except Exception as e:
                            st.error(f"Error opening file: {e}")
                c_page.markdown(f'<div class="sz-page">Page {res["page_num"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="sz-snip">{extract_smart_snippet(res["text"], q)}</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
