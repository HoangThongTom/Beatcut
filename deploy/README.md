# Deploying the demo

**Live app:** <https://beatcut-hb8jo3fdd5dsrvthptc2qf.streamlit.app/>

## Streamlit Community Cloud (free, no card) — the current target

Hugging Face now offers free accounts **ZeroGPU only** when creating a Space:
CPU Basic is greyed out. ZeroGPU refuses to start an app that has no
`@spaces.GPU` function, and this pipeline is pure CPU, so buying GPU quota to run
it would be both wasteful and misleading.

Streamlit Community Cloud runs the app straight from the public GitHub repo.

1. Push the repository to GitHub (it must be public).
2. Sign in at <https://share.streamlit.io> with GitHub.
3. **New app** → repository `HoangThongTom/beatcut` → branch `main` → main file
   path `app/streamlit_app.py` → **Deploy**.
4. First boot installs `requirements.txt` and apt-installs the packages in
   `packages.txt` (ffmpeg). It takes a few minutes.

Set `BEATCUT_MAX_DURATION_S` in the app's **Settings → Secrets** if 60 seconds is
not what you want:

```toml
BEATCUT_MAX_DURATION_S = "60"
```

## Hugging Face Spaces (blocked for free accounts)

The Space configuration is kept for anyone with PRO:
[`space-README.md`](space-README.md) is the app card, and `app/ui.py` is the
Gradio entry point.

Publish it from a throwaway branch, since Spaces requires its app card at the
repository root and that would overwrite the project README:

```powershell
git checkout -b hf
Copy-Item deploy\space-README.md README.md -Force
git add -A
git rm --cached docs/assets/demo.gif
git commit -m "Space snapshot"
git push --force "https://<user>:<token>@huggingface.co/spaces/<user>/beatcut" "hf:main"
git checkout main
```

Two things that bite:

- the Hub rejects **binary files** over git, hence removing the GIF from the
  branch (it is only ever an orphan snapshot, so the blob is not in history)
- a new Space starts with a placeholder README, so the push needs `--force`

## Docker

The `Dockerfile` still builds a working API (`app/api.py`) and is verified
locally; it is not a free deployment target any more.
