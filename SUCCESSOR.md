# Grace House Hymnal — How to Run This

Hi. If you're reading this, you're probably the person now looking after
the hymnal site. Welcome. It's simple, and this document is everything
you need. There are no servers to babysit, no bills to pay, no software
to install. Everything happens in your web browser.

## What this is

A little website that shows the Grace House hymnal on people's phones.
The URL is unlisted — only people with the exact link can see it — and
the link has a "key" in it (something like `grace-34vm3plb`) so it can't
be guessed. Change the key any time and the old link stops working.

The site is hosted for free on GitHub Pages. As long as GitHub exists,
this works.

## The one thing to remember

**Every hymn is a text file in the `hymns/` folder.** To change what
appears on the site, you change those files. That's it. When you save
a change, the site rebuilds itself in about 30 seconds.

## How to add a new hymn

1. Go to the repo on github.com (bookmark it now if you haven't).
2. Click into the `hymns/` folder.
3. Click the "Add file" button (top right) → "Create new file".
4. Name the file like this: `042-name-of-hymn.txt`
   - The first three digits are the hymn number (use the next unused one).
   - After the dash, any short name. Lowercase, hyphens instead of spaces.
5. In the big text box, type the hymn like this:

   ```
   Title of the Hymn

   1
   First line of verse one
   Second line of verse one

   C
   First line of chorus
   Second line of chorus

   2
   First line of verse two
   Second line of verse two
   ```

   Rules:
   - First line is the title.
   - A blank line separates blocks.
   - The first line of a block is a *label* if it's short (6 characters
     or less) and has no spaces. Use `1`, `2`, `3` for verses and `C`
     for the chorus. `C` gets a pink line and italics automatically.
   - If you don't put a label, blocks get numbered 1, 2, 3 automatically.

6. Scroll to the bottom, type a short note in the "Commit changes" box
   (e.g. "Add Amazing Grace"), and click the green **Commit changes**
   button.
7. Wait ~30 seconds. The site is updated.

## How to fix a typo in an existing hymn

1. Click on the file in the `hymns/` folder.
2. Click the pencil icon (top right of the file view).
3. Fix the text.
4. Scroll down, click **Commit changes**.
5. Wait ~30 seconds.

## How to delete a hymn

1. Click on the file in `hymns/`.
2. Click the trash-can icon (top right).
3. Click **Commit changes**.

## How to change the "about" page

Edit `zine.txt` at the top of the repo, same way as a hymn. Its format
is the page title on line 1, then a blank line, then repeating blocks
of `Heading` + body lines. Lines starting with `- ` become bullet points.

## How to change the access key (the code in the URL)

Edit `access-key.txt`. Put whatever you want on the first line — letters,
numbers, dashes, underscores. Save. The old URL stops working, the new
URL (with your new key) starts working.

**After you change the key, regenerate the QR code** so it points at the
new URL. Any free QR generator online works; the QR should encode:
`https://[your-github-pages-url]/[the-new-key]/`. Save the resulting
image as `qr-code.png` at the top of the repo, replacing the old one.

## What if something breaks

1. Look at the "Actions" tab at the top of the repo. Every save triggers
   a build. If the most recent one has a red X, click into it to see
   what went wrong. Usually it's a typo in a filename.
2. Every change is in the repo history. To undo a bad change, click
   "History" on the file, find a version you liked, and copy its
   contents back.
3. If you're really stuck, the site keeps showing the last version that
   built successfully — nothing is ever suddenly offline.

## What the other files are

- `server.py` — a small Python program that runs the site on your own
  computer, for previewing. You don't need it. It's there if a future
  helper wants to see changes before committing.
- `build.py` — the program GitHub runs to turn the hymn files into the
  actual website. Don't edit this unless you know what you're doing.
- `.github/workflows/deploy.yml` — tells GitHub to run `build.py` on
  every save. Don't touch.
- `dist/` — if you see this locally, it's the built site. Not committed
  to the repo; GitHub builds its own copy each time.

## Cost

Zero. GitHub Pages is free for public repos, no card, no trial.

That's the whole system. It's designed to be boring in the best way.
