# Deploying to Hugging Face Spaces

Hugging Face put **Docker Spaces behind a paywall** (credits or PRO). The free
route is the **Gradio SDK**, which is what this repository is set up for:
`app/ui.py` is a small form over the pipeline, and `requirements.txt` plus
`packages.txt` tell the Space how to install it.

The `Dockerfile` is still useful locally (`docker build` / `docker run`), it is
just not the deployment target any more.

## One-time setup on huggingface.co

1. Create an account.
2. **Settings → Access Tokens → New token**, role **Write**. Copy it — it is shown
   once.
3. **New Space**:
   - name: `beatcut`
   - SDK: **Gradio**
   - hardware: **CPU basic (free)**
   - visibility: **Public**
4. In the new Space: **Settings → Variables and secrets**, add
   `BEATCUT_MAX_DURATION_S = 60`.
   Rendering is synchronous; the default of 180 s is longer than the proxy in
   front of Spaces will hold a request.

## Publish

Spaces requires its app card at the root `README.md`, which would overwrite the
project README, so the Space is published from a throwaway branch. Run from the
repository root; `<user>` is your Hugging Face username.

```powershell
git checkout -b hf-space
Copy-Item deploy\space-README.md README.md -Force
git commit -am "Space app card"
git push --force https://huggingface.co/spaces/<user>/beatcut hf-space:main
git checkout main
git branch -D hf-space
```

When git asks for credentials, the username is your Hugging Face username and the
password is the **token**, not your account password.

`--force` is there on purpose: a new Space is initialised with its own placeholder
README commit, so a normal push is rejected as non-fast-forward.

## Verifying the Space

The Space installs `requirements.txt`, runs `packages.txt` (which apt-installs
ffmpeg), then launches `app/ui.py`. First boot takes a few minutes.

If the build fails, the **Logs** tab shows the pip and apt output. The usual
culprits are the editable install (`-e .`) and the Python version, which is pinned
to 3.11 in the app card because `numba` has no wheels for 3.13+.

## Updating it later

Re-run the publish block after any change to `src/`, `app/` or the pipeline
config. The branch is recreated each time, so nothing lingers.
