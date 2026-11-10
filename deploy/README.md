# Running and deploying BeatCut

## Local editor on Windows

Run `scripts/bootstrap.ps1`, then install the interface once:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Double-click **Start-BeatCut.cmd**. The editor opens at
[localhost:8501](http://localhost:8501) with a 60-minute gameplay limit and a
1024 MB upload limit per file. Keep the terminal open while using the app.
The launcher uses `tools/ffmpeg/ffmpeg.exe` and `ffprobe.exe` when present,
or the binaries on PATH. Explicit `FFMPEG_BIN` / `FFPROBE_BIN` environment
variables take precedence.

```powershell
# Change the port or source duration limit.
.\scripts\start-local.ps1 -Port 8503 -MaxDurationSeconds 7200
```

For independent human labeling, double-click **Start-Labeling.cmd** or pass
`-Annotate` to the launcher. It defaults to port 8503, reads original videos by
local path, and does not show automatic highlights. See the
[evaluation protocol](../docs/eval-protocol.md#local-independent-labeling).

## Streamlit Community Cloud

**Live demo:** [BeatCut](https://beatcut-hb8jo3fdd5dsrvthptc2qf.streamlit.app/)

1. Push the repository to GitHub.
2. Open [Streamlit Community Cloud](https://share.streamlit.io) and sign in with GitHub.
3. Create an app from `HoangThongTom/Beatcut`, branch `main`, main file
   `app/streamlit_app.py`.
4. The runner installs `requirements.txt` and the system packages in `packages.txt`.

The public demo defaults to a 60-second source limit. The Windows launcher
enables local mode. See `.streamlit/config.toml` for the shared theme.

## Docker API

The Dockerfile packages `app/api.py` with FFmpeg and OCR support. The API is
synchronous, has no authentication, and defaults to 256 MB per upload and 180
seconds of gameplay. Bind it to localhost for local testing:

```powershell
docker build -t beatcut .
docker run --rm -p 127.0.0.1:8000:8000 beatcut
```

Open [the API docs](http://localhost:8000/docs) or check `/health`.
Pass `-e BEATCUT_MAX_UPLOAD_MB=256` and `-e BEATCUT_MAX_DURATION_S=180` to
`docker run` to override those limits. `.env` files are not automatically loaded.
