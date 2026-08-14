# Four Seasons × Salesforce — Target State Site (v2)

Static HTML site, deployed to Heroku via GitHub auto-deploy. **No password on this version.**

## What's in this folder

| File | Purpose |
|---|---|
| `index.html` | The site itself (v2 — two-act narrative). Self-contained: all CSS/JS inline. |
| `static.json` | Heroku static buildpack config. Forces HTTPS, blocks search indexing, adds security headers. No auth gate. |
| `robots.txt` | Blocks all search crawlers (belt & suspenders alongside the `X-Robots-Tag` header). |
| `make_qr.py` | Dependency-free QR-code generator. Regenerate the QR once you know the real Heroku URL. |
| `fs-target-state-qr.png` / `.svg` | **Placeholder** QR encoding `https://fs-target-state.herokuapp.com`. Regenerate with your real app name (see below). |
| `.gitignore` | Standard ignores for a static repo. |
| `README.md` | This file. |

> **This version has no Basic Auth.** Anyone with the link (or the QR) can open it. It's still marked `noindex`/`nofollow` and `robots.txt` blocks crawlers, so it won't show up in search — but it is not access-restricted. If you later want a password back, say so and I'll add the `basic_auth` block to `static.json`.

---

## Deploy — your usual flow

### 1. Create a new GitHub repo
- New repo (private is fine)
- Do NOT initialize with README, `.gitignore`, or license — this folder already has what it needs
- Note the repo URL

### 2. Push this folder to that repo
From this folder in your terminal:
```bash
git init
git add .
git commit -m "Four Seasons target-state site v2"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### 3. Create the Heroku app
- Heroku dashboard: **New → Create new app**
- App name: e.g. `fs-target-state` (becomes `fs-target-state.herokuapp.com`)
- **Whatever name you pick here is the URL the QR must encode — see "Regenerate the QR" below.**
- Region: US or EU — either is fine → **Create app**

### 4. Add the static buildpack
Heroku doesn't autodetect a static-HTML app, so tell it explicitly.
- **Settings** tab → **Buildpacks** → **Add buildpack**
- Paste this custom buildpack URL:
  ```
  https://github.com/heroku/heroku-buildpack-static
  ```
- Save

### 5. Connect GitHub and enable auto-deploy
- **Deploy** tab → **Deployment method** → **GitHub** → authorize (first time only)
- Search your repo → **Connect**
- **Automatic deploys** → select `main` → **Enable Automatic Deploys**
- **Manual deploy** → **Deploy Branch** once to trigger the first build

### 6. Open the site
- **Open app** (top right) → loads `https://YOUR-APP-NAME.herokuapp.com` over HTTPS
- No password prompt (this version)

Every future `git push` to `main` redeploys automatically within ~30 seconds.

---

## The QR code

`fs-target-state-qr.png` and `.svg` are included now, but they're a **placeholder** encoding `https://fs-target-state.herokuapp.com`. If your real Heroku app name is different, that placeholder QR will point at the wrong (or a non-existent) URL. **Regenerate it once you know the final URL.**

### Regenerate with your real URL
From this folder:
```bash
python3 make_qr.py "https://YOUR-APP-NAME.herokuapp.com" --out fs-target-state-qr
```
This overwrites `fs-target-state-qr.svg` and `fs-target-state-qr.png`.

Options:
- `--out NAME` — output base filename (default `fs-target-state-qr`)
- `--scale N` — pixels per module; bump it up for large-format print, e.g. `--scale 20`

The script needs no third-party QR library. It writes an SVG always; it also writes a PNG if Pillow (`PIL`) is installed (`pip install Pillow`). The SVG is best for print or slides (crisp at any size); the PNG is a quick drop-in.

**Colors** are Four Seasons navy (`#1c2a3a`) on white. To change them, edit the `dark`/`light` defaults near the bottom of `make_qr.py`.

### Verify a QR before you print it
Always test-scan with your phone after regenerating. A QR that looks fine can still encode the wrong text if the URL was mistyped.

---

## What the config does (`static.json`)
- **`https_only: true`** — force HTTP → HTTPS.
- **`clean_urls: true`** — `/about` resolves to `/about.html` if you add pages.
- **`X-Robots-Tag: noindex…`** — tells search engines not to index, even if they find it.
- **`Strict-Transport-Security`** — locks browsers to HTTPS for a year.
- **`X-Content-Type-Options: nosniff`** — hardening.
- **`Cache-Control: max-age=300`** — 5-minute cache; updates show up fast.

---

## Adding a hero video (optional)
`index.html` has a hero `<video>` slot that looks for `hero.mp4`. If no file is present, it falls back gracefully to a gradient — nothing breaks. To use footage, drop an **approved** Four Seasons clip named `hero.mp4` into this folder, commit, and push. (No clip is included — supply your own cleared asset.)

---

## Troubleshooting
- **"Application error" on first load** → buildpack probably missing. **Settings → Buildpacks** must show `heroku/heroku-buildpack-static`. Add it, re-deploy.
- **Site loads but no styles** → CSS is inline, so this shouldn't happen; check the deploy log for build errors.
- **QR scans to the wrong URL** → you deployed under a different app name than the QR encodes. Regenerate (see above).

---

## Cost
- Heroku **Eco** dyno: $5/mo shared pool; sleeps after 30 min idle (~5s cold start).
- Heroku **Basic** dyno: $7/mo per app, never sleeps — recommended if you're emailing the link to an exec.

Static buildpack itself is free.

---

## Removing it later
- Delete the Heroku app: **Settings → Delete app**
- Delete or archive the GitHub repo
