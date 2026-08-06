# Self-updating profile README — setup

This folder reproduces the Andrew6rant-style neofetch profile card for
`PizzaStev3/PizzaStev3`. The README is a theme-responsive `<picture>` that shows
`dark_mode.svg` or `light_mode.svg`; a GitHub Action regenerates those SVGs daily
with your live GitHub stats.

## Files

| File | Purpose |
| ---- | ------- |
| `README.md` | The `<picture>` block GitHub renders on your profile |
| `dark_mode.svg` / `light_mode.svg` | The rendered card (generated — don't hand-edit) |
| `ascii-art.txt` | The left-hand ASCII art |
| `build_svgs.py` | Renderer + **all editable card text** (layout, dot-leaders, sections) |
| `today.py` | Fetches stats via the GitHub GraphQL API, then calls `build_svgs` |
| `.github/workflows/main.yml` | Daily cron + on-push + manual trigger |

**Architecture:** `build_svgs.py` is the single source of truth for the card. It
right-aligns every value with dot leaders and recomputes them on each render, so
columns stay aligned no matter how the numbers change. `today.py` only fetches the
GitHub stats and hands them to `build_svgs.render_all(...)`. You never edit the
`.svg` files by hand — change the text in `build_svgs.py` and re-render.

## One-time setup

1. **Copy these files** into the root of your `PizzaStev3/PizzaStev3` repo
   (keep the `.github/workflows/` path intact). This replaces the current
   one-line README.

2. **Set your birth date** in `today.py` (already set to `2004-07-06`):
   ```python
   BIRTHDAY = datetime.datetime(2004, 7, 6)  # YEAR, MONTH, DAY
   ```

3. **Personalize the card text** in `build_svgs.py` (not the SVGs):
   - `NAME_HEADER` — the `ahmed@mohammed` header.
   - `STATIC` dict — OS, Host, Skills, Languages, Hobbies, LinkedIn, Discord.
   - To change the ASCII art, replace `ascii-art.txt`.
   Then re-render: `python build_svgs.py`.

4. **Create a Personal Access Token**
   (GitHub → Settings → Developer settings → Personal access tokens).
   A fine-grained token with **read-only** access to your repositories
   (Contents + Metadata) is enough. Copy the token.

5. **Add it as a repo secret**: in `PizzaStev3/PizzaStev3` →
   Settings → Secrets and variables → Actions → New repository secret →
   name it exactly `ACCESS_TOKEN`, paste the token.

6. **Trigger the workflow**: push the files, then go to the **Actions** tab and
   run **Update Profile SVGs** manually (workflow_dispatch) for the first run.
   It commits the freshly-populated SVGs back to the repo.

## Test locally (optional)

Preview the layout with placeholder stats (no token needed):
```bash
python build_svgs.py        # rewrites dark_mode.svg / light_mode.svg
```

Render with real stats:
```bash
pip install requests python-dateutil
ACCESS_TOKEN=ghp_xxx USER_NAME=PizzaStev3 python today.py
```
The first stats run scans every repo's commit history (slow); subsequent runs use
the `cache/` directory and are fast.

## Notes

- Until the first Action run, the stat numbers (Repos, Stars, Commits, Followers,
  Lines of Code) render as `0`. They populate on the first run and update daily.
- "Lines of Code" counts additions/deletions authored by you across the default
  branch of every repo you own or collaborate on. New accounts show small numbers
  — they grow as you commit.
- Alignment is character-based and assumes a monospace font (the SVG uses a
  Consolas/Menlo/DejaVu stack). The panel is 60 characters wide; if you add a very
  long value it will collapse the dot leader to a single dot rather than overflow.
  For pixel-identical spacing to Andrew6rant's across all machines, embed a web
  font as base64 in `build_svgs.py`'s `<style>`.
