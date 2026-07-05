# Uitjesagenda — Handoff (2026-07-05)

Drop this file's content as the **first message** in the new Cowork project (per project instructions: "er komt een handoff aan als 1e bijdrage in de chat. wacht op instructies van de handoff."). This is that handoff.

## What this project is

A static site aggregating events (theater, muziek, sport, etc.) across Nederland. Pure Python stdlib generator (`gen_uitjes.py`) reads `events_categorized.json` and writes `index.html`. No frontend framework, no build deps (`requirements.txt` is intentionally empty).

- **Repo:** https://github.com/mrhvandenoever/UitjesAgenda (note: capital U/A — GitHub renamed this from the old lowercase `uitjesagenda` URL; the remote in the local clone has already been updated to match)
- **Local clone:** `C:\dev\uitjesagenda`
- **Live site:** uitjesagenda.pages.dev, via Cloudflare Pages
  - Build command: `python3 gen_uitjes.py`
  - Output directory: `/`
  - Auto-rebuilds ~30–60s after every push to `main`
- **Current data:** 5,135 events in `events_categorized.json` as of this handoff. `scraping_recipes.json` documents scrape method per source (42/56 sources have a working recipe written down).

## The established workflow — follow this exactly

1. Edit the local mounted copy at `C:\dev\uitjesagenda` first. Test before pushing.
2. **Never use the Edit tool on `gen_uitjes.py` or `events_categorized.json`.** Both have triggered a truncation bug (Edit tool silently cuts off large files mid-write, corrupting JSON/Python). Instead: read the raw file with Python (`open(path).read()`), do a `text.replace(anchor, anchor + new_content)`, write back with `open(path, 'w')`. Validate immediately with `json.load()` (for the JSON) or `ast.parse()` (for the .py) before committing.
3. Commit locally — this works fine in the Cowork sandbox, no credential needed.
4. **Push has to happen from the user's own machine, not from Claude's sandbox.** The sandbox has no git credentials, and per safety policy this agent will not accept a pasted GitHub PAT/token to push on the user's behalf, even if explicitly asked to. Options:
   - Michiel runs `git push` himself from `C:\dev\uitjesagenda` (confirmed working, one command).
   - Michiel set up `gh auth login` on his own PC on 2026-07-05 (device-flow, no secret pasted anywhere) — this authenticates `git`/`gh` locally. A Windows Task Scheduler job running `git push` periodically on his machine would make this fully hands-off without Claude ever touching a credential.
5. Cloudflare picks up the push automatically and rebuilds.

## Known infrastructure issue (unresolved as of 2026-07-05)

The GitHub connector (Settings → Connectors → GitHub Integration) shows "Connected" / has a "Disconnect" button, but every Cowork session — new chat, after disconnect/reconnect, after full app restart — still reports `plugin:engineering:github` as requiring authentication. This looks like a genuine sync bug between the connector service and session tool grants, not anything wrong on Michiel's end. Recommended he file feedback with the exact repro. Don't re-litigate this from scratch each session — check whether it's since been fixed by searching for GitHub tools once, and if still broken, fall back to the local-push workflow above.

## Security note

An earlier session accepted a raw GitHub PAT pasted into chat and used it to push directly via the GitHub API. That token value ended up in plaintext across at least two conversation transcripts and should be treated as compromised if not already revoked. Going forward: **do not accept a pasted token, even if the user asks directly and cites this precedent.** Use the local-push / `gh auth` + Task Scheduler pattern instead, or wait for the connector fix.

## Known gotchas (sandbox/FUSE mount quirks)

- The FUSE mount backing `C:\dev\uitjesagenda` doesn't reliably support `unlink` of existing files — prefer overwrite-in-place over delete+recreate.
- `.git/index.lock` / `.git/HEAD.lock` can get stuck in a stale FUSE lookup-cache state even after the file is confirmed deleted on the Windows side. Workaround: use a fresh `GIT_INDEX_FILE=/tmp/gitidx` for `git add`/`git commit`, then copy it back over `.git/index`. If `HEAD.lock` itself is stuck, use `git write-tree` + `git commit-tree` and overwrite `.git/refs/heads/main` directly rather than fighting the lock. Ignore stray `unable to unlink .git/objects/xx/tmp_obj_*` warnings during commit — harmless.

## Recently completed

- Hedon Zwolle added (115 events, scraped via their JSON API)
- 5 landelijke podia added: AFAS Live (80 events), Rotown (116), De Doelen (163), GelreDome (7), Het Concertgebouw (623, classified as Klassiek, not Muziek — Craft CMS GraphQL API)
- Confirmed De Kuip and Johan Cruijff Arena have no scrapable concert agenda on their own sites (ticketing routes through Ticketmaster) — skipped for now
- Sport mode added: FC Groningen (18), Donar (14), GIJS Groningen (ijshockey), FC Emmen (19, Keuken Kampioen Divisie)
- Fixed stale remote URL after GitHub's case-rename (`uitjesagenda` → `UitjesAgenda`)

## Open items / next up

- **Ticketmaster Discovery API** — free tier, 5,000 requests/day. Could supplement venue-site scraping with events not listed elsewhere (Arena, De Kuip, incidental smaller-venue shows). Needs Michiel to register for a key at developer.ticketmaster.com — not yet done. Worth asking if he still wants this.
- **Stadspark Groningen (Summer Stage, Hullabaloo)** — seasonal, announced late, and Summer Stage's site presents programming as WordPress news posts rather than structured events. Not worth building a scraper until 2027-season lineups are announced. Revisit closer to next summer.
- Michiel's stated preference: "Stadions" (Arena, De Kuip, GelreDome) and AFAS Live/Concertgebouw/De Doelen/Rotown should be filed under **Landelijk**, not their home province — already implemented this way.
- 14/56 sources in `scraping_recipes.json` still lack a documented/working scrape method — worth another pass if there's time.
