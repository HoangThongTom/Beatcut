# Deploying to Hugging Face Spaces

The Space is a *separate* git repository, and Spaces requires its app card at the
root `README.md`. Rather than overwrite the project README, the Space is published
from a throwaway branch built from [`space-README.md`](space-README.md).

## One-time setup on huggingface.co

1. Create an account.
2. **Settings → Access Tokens → New token**, role **Write**. Copy it — it is shown
   once.
3. **New Space**:
   - name: `beatcut`
   - SDK: **Docker**
   - hardware: **CPU basic (free)**
   - visibility: **Public**
4. In the new Space: **Settings → Variables and secrets**, add
   `BEATCUT_MAX_DURATION_S = 60`.
   The defaults (180 s) are too long for the proxy in front of Spaces.

## Publish

Run from the repository root. `<user>` is your Hugging Face username.

```powershell
git checkout -b hf-space
Copy-Item deploy\space-README.md README.md -Force
git commit -am "Space app card"
git push --force https://huggingface.co/spaces/<user>/beatcut hf-space:main
git checkout main
git branch -D hf-space
```

`--force` is there on purpose: a new Space is initialised with its own placeholder
README commit, so a normal push is rejected as non-fast-forward. The space is
yours and the placeholder has no content worth keeping.

When git asks for credentials, the username is your Hugging Face username and the
password is the **token**, not your account password.

The first build takes about ten minutes: the base image, ffmpeg, and the Python
dependencies. Later pushes rebuild only what changed.

## Verifying the Space

- `/health` should return the caps it is running with.
- Upload a clip under the limit and a music track; the response is the montage.

If the build fails, the Space's **Logs** tab shows the Docker build output, which
is the same output `docker build` produces locally.
