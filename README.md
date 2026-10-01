# SEZDocs

Offline PDF search app (Streamlit + FAISS + sentence-transformers + OCR
fallback), styled with a "blueprint" visual identity to match the
engineering-document subject matter.

## What's in this folder

| File | Purpose |
|---|---|
| `app.py` | The Streamlit app itself (search, indexing, UI) |
| `.streamlit/config.toml` | Theme + makes the server reachable on your LAN |
| `desktop_launcher.py` | Wraps the app in a native window instead of a browser tab |
| `BUILD_WINDOWS_EXE.md` | Exact steps to turn that into `SEZDocs.exe` |
| `INSTALL_WINDOWS.bat` | **One-click installer** — put this on GitHub, users download and run it |
| `requirements.txt` | Everything needed, including packaging tools |

## OCR now reads Persian + English

Tesseract only ships with the English language pack by default. If your
scanned PDFs are Persian (or a mix of Persian and English, like most
engineering docs here), OCR silently returned nothing for the Persian pages
before — not an error, just an empty page, which is why it looked like "it
doesn't recognize scans at all."

Fixed:
- `app.py` now asks Tesseract for `lang="fas+eng"` and checks at startup
  which language packs are actually installed, showing a clear warning in
  the sidebar if `fas` (Persian) is missing instead of failing silently.
- `INSTALL_WINDOWS.bat` downloads the official `fas.traineddata` file into
  Tesseract's `tessdata` folder automatically.
- If you already have Tesseract installed manually, you only need that one
  file: download it from
  https://github.com/tesseract-ocr/tessdata/raw/main/fas.traineddata and
  copy it into `C:\Program Files\Tesseract-OCR\tessdata\`, then restart the
  app — the sidebar warning will disappear once it's found.

## Publishing `INSTALL_WINDOWS.bat` on GitHub

1. Push this whole folder to a GitHub repo (e.g. `github.com/you/sezdocs`).
2. Open `INSTALL_WINDOWS.bat` and fill in the three lines near the top:
   ```
   set "GITHUB_USER=you"
   set "GITHUB_REPO=sezdocs"
   set "GITHUB_BRANCH=main"
   ```
3. Commit that change. Anyone can now download and run just that one file
   from:
   `https://raw.githubusercontent.com/you/sezdocs/main/INSTALL_WINDOWS.bat`
   (right-click → "Save link as", or use a GitHub Release asset for a
   friendlier download page).
4. Running it installs Python, Tesseract (with the Persian language pack),
   Poppler, and SEZDocs itself — no manual setup needed — then creates a
   **SEZDocs** icon on the desktop for future launches.

**Honest caveats:**
- It needs Administrator rights once (to install Tesseract's language
  files into Program Files) — it re-launches itself elevated and Windows
  will show the UAC prompt.
- On a machine with zero prior setup, the very first run installs Python
  and then asks you to run the file a second time, because Windows won't
  see the updated PATH inside the same terminal session.
- The script pins specific download versions (Python 3.12.4, Poppler
  24.07.0) that will eventually go stale — check those URLs occasionally
  and bump the version numbers if a download starts failing.

## Running it normally (any OS)

```
pip install -r requirements.txt
streamlit run app.py
```

## "Windows app" — what you actually get

A native-feeling desktop window (no browser address bar/tabs) that you can
pin to the Start Menu / taskbar, built by `desktop_launcher.py` +
PyInstaller. Follow `BUILD_WINDOWS_EXE.md`. This isn't a from-scratch
rewrite — it's the same app running a local server in the background with a
window wrapped around it, which is the standard way Python data-science
apps like this become desktop apps.

## "Mobile app" — the honest version

Being direct about this one: a true native iOS/Android app (something
installable from the App Store / Play Store) isn't realistic to build on
top of this codebase without a major separate rewrite. The reason is
`sentence-transformers`, `faiss`, and `pytesseract`/Tesseract are native
libraries that don't run inside a phone's app sandbox the way they run on a
desktop — a real mobile port means either (a) rebuilding the search/OCR
layer with mobile-native ML tooling, or (b) keeping this as a server your
phone talks to over the network.

**(b) is what I've set up for you** — it's the practical win and works today:

1. Run `streamlit run app.py` on your Windows PC (or the exe, once built).
2. Find that PC's local IP address: `ipconfig` → look for "IPv4 Address"
   (something like `192.168.1.23`).
3. On your phone, connect to the **same Wi-Fi network**, then visit
   `http://192.168.1.23:8501` in the phone's browser.
4. In the phone browser's menu, choose "Add to Home Screen" — you get an
   icon that opens straight to the app, full-screen, no address bar. It
   behaves like an app for day-to-day use, it's just not something you'd
   submit to an app store.

The CSS already includes mobile breakpoints (bigger touch targets, stacked
layout, resized headers) so this should look right on a phone screen, not
just shrunk-down desktop UI.

If you do want a real native mobile app down the line, the realistic path
is: keep this Streamlit app as the "engine" running on a PC or small server
on your network, and build a thin Flutter/React Native app that just talks
to it over HTTP — that's a separate, scoped project.


## What's new (UI + Report)

- **SEZTools look:** JetBrains Mono (bundled in `static/`, OFL license included), SEZTools blue `#0B5FA5`, light blueprint grid.
- **Sidebar = Insert Sources:** 1. Select Files, 2. Select Directories (native folder picker), 3. Select Index. Each step shows its own status line; "Total selected PDFs" counts files + folder PDFs.
- **No more "Merge" checkbox:** files already indexed and unchanged (same path, size, modified time) are skipped automatically; changed files are re-processed and replace their old pages. With an index loaded, new files are added to it; use **Clear Index** to start over and **Save Index** to keep a named copy.
- **Report:** one click exports the current search results as a PDF (query, index, date, file, page, snippet). Persian text is supported using the system font (Tahoma/Arial on Windows).
- **Truly offline after install:** `INSTALL_WINDOWS.bat` now also pre-downloads the search AI model (~90MB, one time) during setup, so the very first search works without internet too.

## License

Copyright (c) 2026 Mohammad Reza Sebzari

SEZDocs is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License v3.0. See the [LICENSE](LICENSE) file.
