# Hymnal — first-time setup

You're setting this up so people at your home church can scan a QR code
and see the hymn on their phone. Real HTTPS, no warnings, works on any
network (church WiFi, cellular, guest WiFi, anywhere).

There's a one-time setup (about 15 minutes). Once done, every service is:
double-click `start.command` → done.

---

## How it works

Your Mac runs a tiny hymnal server. **Tailscale Funnel** exposes it to the
internet at a permanent URL like `https://gracehouse.tail-XXXX.ts.net` with
a real HTTPS certificate (no scary warnings on anyone's phone). The whole
site sits behind an **access key** — a short word in the URL like
`grace-2026-x7k9m`. Only URLs that include the key show hymns; everything
else gets a blank "nothing here" page. The QR code has the key baked in,
so scanning is still one tap.

---

## 1) Mac hostname (already done)

Your Mac's **Local hostname** is set to `gracehouse` in
System Settings → General → Sharing. Leave **Dynamic Global Hostname**
alone — you don't need it.

## 2) Install Tailscale

Download the **standalone** package from
<https://tailscale.com/download/mac> (not the App Store version — the
standalone gives you cleaner CLI access from Terminal). Install it.

Click the Tailscale icon that appears in your menu bar → **Log in**. Pick
email, Google, GitHub, whatever. The free personal tier includes Funnel.

## 3) Turn on Funnel

Open Terminal (Cmd+Space, type "Terminal"), then run:

    sudo tailscale funnel --bg 8000

The first time, Tailscale walks you through a browser consent to enable
HTTPS certificates and Funnel on your account. Follow the prompts.

When it finishes, it prints your Funnel URL. If you missed it, run:

    tailscale funnel status

The URL will look like `https://gracehouse.tail-XXXX.ts.net` — that's your
permanent hymnal URL.

**Copy that URL and send it to Claude.** Claude will regenerate the QR code
so it points at `https://gracehouse.tail-XXXX.ts.net/grace-2026-x7k9m/`
(the URL + the access key).

## 4) First launch

1. Double-click `start.command`.
2. macOS will refuse to run it the first time (unknown developer). Normal.
3. Right-click `start.command` → **Open** → in the dialog, click **Open**
   again. One-time thing.
4. A Terminal window opens showing the server. Leave it open.
5. On your phone, scan the printed QR. The hymnal should load.

To stop the server: press Ctrl+C in the Terminal window, or close it.
Tailscale keeps running in the background — that's fine.

## 5) Print the QR code

`qr-code.png` is the QR to print. Drop it onto Preview, ⌘P. Tape it in the
bulletin, on a wall, wherever people will see it.

---

## The access key

The file `access-key.txt` in this folder holds a word — currently
`grace-2026-x7k9m`. It's the "password" baked into the QR URL.

If you ever want to change it (compromised, new year, etc.), edit
`access-key.txt`, save, and tell Claude the new key so a fresh QR gets made.
The old QR stops working immediately.

If you never touch it, it stays the same. There's no time limit on it.

---

## Adding a hymn

Drop a text file into the `hymns/` folder. Name pattern:

    001-amazing-grace.txt
    ^^^ ^^^^^^^^^^^^^
    number   any short name (dashes for spaces)

Basic file (no chorus, auto-numbered verses):

    Title of the hymn

    Verse 1 line 1
    Verse 1 line 2

    Verse 2 line 1
    Verse 2 line 2

File with a chorus (or any custom labels):

    It Is Well With My Soul

    1
    When peace like a river attendeth my way...

    C
    It is well with my soul,
    It is well, it is well with my soul.

    2
    Though Satan should buffet...

    3
    My sin—oh, the bliss...

Any short string (up to 6 chars, no spaces) alone on the first line of a
block is treated as that block's **label**. Use `1`, `2`, `3` for verses,
`C` for chorus, `B` for bridge, `Cd` for coda — whatever makes sense.
The `C` label gets special treatment (pink rule on the left, italic body).

To repeat the chorus after every verse, copy-paste the `C` block. The
order of blocks in the file is the order shown on the phone. Sequence
`1, C, 2, C, 3, C` is just:

    1
    ...verse 1 lines...

    C
    ...chorus lines...

    2
    ...verse 2 lines...

    C
    ...chorus lines...

    3
    ...verse 3 lines...

    C
    ...chorus lines...

The number in the filename controls the table-of-contents order.
Zero-pad (001, 002…) so they sort right.

You don't need to restart the server. Refresh the page and changes show up.

**Copyright reminder:** anything published before 1930 is public domain
in the US (as of 2026). Modern worship music (Chris Tomlin, Hillsong,
Bethel, etc.) is copyrighted; churches typically license it through CCLI.

## Editing a hymn

Open the .txt file in TextEdit or any editor and change it. Save. Refresh.

---

## The Sunday Zine (weekly bulletin page)

There's a second page linked from the top-right of the hymnal index —
a rotating "THE SUNDAY ZINE →" chip. That leads to a page with weekly
announcements, prayer requests, whatever else you want to put in front
of the congregation.

Content lives in one file: **`zine.txt`** in the hymnal folder. Rewrite
it each week; nothing gets kept once it's replaced.

**Format:**

    Title of the page

    Section heading
    Body text for this section.
    More body text.

    Another section heading
    - bullet point
    - another bullet point

    Verse of the Day
    For God so loved the world...
    — John 3:16

Rules:

- **Line 1** is the page title. Shows up as the big black tag AND as
  the chip label on the hymnal index. Change it to whatever ("SUNDAY
  ZINE", "UPDATES", "ANNOUNCEMENTS", "THIS WEEK"), both places update.
- **Sections** are separated by a blank line.
- **First line of each section** is the heading (renders as a big
  stencil header).
- **Rest of the section** is body text. Each line becomes a paragraph.
- **Lines starting with `- ` or `* `** render as bullet points.
- **No blank lines inside a section** — a blank line means "new section".

To delete the zine entirely: delete `zine.txt`. The link on the hymnal
index disappears and `/zine` returns the blank "nothing here" page.
Restore it by putting `zine.txt` back.

The last-updated date shows automatically from the file's modification
time — no need to type a date into the file.

---

## For the musician (printing chord charts)

There's a musician's-booklet link at the bottom of the hymn index —
tap **"Musician's booklet →"** or go directly to `/print` on the URL.

That page renders every hymn on its own printable page with:

- Clean black-on-white (no punk chrome, no ink-wasting textures)
- Verse labels down the left (1, 2, C, 3 — same as the digital)
- **A full blank line of space above every lyric line** for
  handwritten chord names (G, C, D, etc.)
- Each song on its own page (page-break between hymns)

To print: open the booklet page in Chrome or Safari, hit **Cmd+P**
(or Share → Print on iPhone). Print to paper, or "Save as PDF" to
keep a digital copy. To print just one hymn instead of all of them,
open that hymn's page directly and Cmd+P — same print styles apply.

In the browser's print dialog, look for "Headers and footers" and
uncheck it if you don't want the date/URL at the top and bottom of
each page. It's a per-print choice.

---

## Troubleshooting

**QR loads, but the hymnal doesn't show up (blank "nothing here" page).**
- Your access key changed but the QR wasn't regenerated. Tell Claude
  the current contents of `access-key.txt` and ask for a new QR.

**QR loads, blank page and no hymn.**
- Same as above — key mismatch.

**QR scan → "Safari cannot open the page" or similar.**
- Your Mac isn't running the hymnal server (double-click `start.command`),
  OR your Mac is offline, OR Tailscale Funnel is off.
- Check Funnel status:  `tailscale funnel status`
- If it says "Funnel off" or shows nothing, restart it:
  `sudo tailscale funnel --bg 8000`

**"Port 8000 already in use."**
- Another program is on port 8000. Run `python3 server.py 8080` in
  Terminal, then re-run Funnel:  `sudo tailscale funnel --bg 8080`
- Tell Claude — the QR needs regenerating.

**I renamed the Mac. Does the URL still work?**
- Tailscale URLs are tied to the Tailscale machine name, which usually
  follows the Mac's name. `tailscale funnel status` will tell you the
  current URL. If it changed, send it to Claude for a new QR.
