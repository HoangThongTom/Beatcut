# BeatCut roadmap — 8 weeks, 10–20 h/week

**English** | [Tiếng Việt](ROADMAP.vi.md)

One rule: **every milestone must be a working product**. If time runs out at M2,
you still have a finished project to put on a CV, not a pile of half-written code.

Where things stand: **M1 done, M2 half done** — the pipeline runs on real VODs,
has a kill detector, and the ablation is measured.

---

## M1 — vertical slice, no models (weeks 1–2)

Goal: one VOD in, one montage out, cut on the beat, no training involved.

- [x] Repo skeleton, pipeline, CLI, unit tests
- [x] Install ffmpeg and run `.\scripts\bootstrap.ps1`
- [x] Record your own VOD and drop it in `data/raw/`
- [x] Run `beatcut run`, watch the output, tune `configs/default.yaml`
- [x] Record a before/after GIF and put it at the top of the README
- [x] `git init`, commit, push a public GitHub repo

**Done when:** the README has a GIF and a stranger can clone and run it by
following the Quickstart commands.

**What you learn:** ffmpeg (seeking, re-encoding, the concat demuxer, why
`-c copy` cuts off the beat), librosa beat tracking, and processing long video
without running out of memory.

---

## M2 — in-game signals (weeks 3–4)

Goal: beat the motion+audio baseline, and **prove** it.

- [x] `killcounter` scorer: crop the kill counter in the HUD, OCR the digit,
      treat a rising number as a kill event. Shipped as `beatcut kills`.
- [x] Feed kill events into the score as a bump around each one, weighted from
      config
- [x] Measure the ablation: 2/8 → 8/8 clips containing a kill
- [ ] `enemy` scorer: fine-tune YOLOv8n on 800–1200 self-labelled frames (CVAT or
      Roboflow free tier). On 4 GB: `imgsz=640`, `batch=8`, AMP.
- [ ] Run `beatcut analyze` over several labelled VODs and compare precision@5
      before and after

**Done when:** a "baseline vs M2" table with real numbers sits in the README.

**What you learn:** labelling protocol, dataset versioning (DVC), fine-tuning
YOLO, and most importantly how to measure whether your change actually helped.

**Warning:** do not jump straight to YOLO. Reading the kill counter gives a far
more precise signal than "an enemy is on screen", and it needs no GPU. Another
lesson learned the hard way: OCR over a wide area reads icons as letters, so the
crop has to be tight.

---

## M3 — packaging (weeks 5–6)

- [ ] `docker build` + `docker run` serving `app/api.py` (the Dockerfile exists
      but has never been tested)
- [ ] GitHub Actions: `ruff check` + `pytest` on every push
- [ ] Cap upload duration — the current API is synchronous and a 1 GB video will
      time out
- [ ] Deploy a demo to Hugging Face Spaces (Docker SDK)
- [ ] Export ONNX and benchmark `onnxruntime` against PyTorch (FPS, ms/frame)

**Done when:** there is a demo link you can click, and CI is green.

**What you learn:** Docker, CI, ONNX, deployment — the part that separates
"student who trained a model on Colab" from "someone who can ship".

---

## M4 — telling the story (weeks 7–8)

- [ ] Run the full [eval protocol](docs/eval-protocol.md) over 10 VODs, split
      dev/test
- [ ] Error analysis: ten false positives, one sentence of explanation each
- [ ] Blog post of 800–1200 words: the problem, the approach, the numbers, what
      failed
- [ ] 60-second demo video (does not need to be pretty, needs to be clear)
- [ ] Clean up: delete dead code, final README, tag `v1.0`

**Done when:** an interviewer reads the README for two minutes and understands
what you built and how you measured it.

---

## Your hardware (RTX 2050, 4 GB)

This is why the numbers below matter more than "a big model":

| Task | How to do it on 4 GB |
|---|---|
| Fine-tune YOLOv8n | `imgsz=640`, `batch=8`, AMP (`amp=True`) |
| Fine-tune YOLOv8s | `imgsz=512`, `batch=4`, or free Colab |
| Train longer than an hour | Colab/Kaggle, keep checkpoints on Drive |
| Benchmark FPS | run locally, state the GPU in the README |

---

## Questions you will be asked in interviews

Prepare answers to these six — they come up almost every time:

1. Why re-encode instead of `-c copy`? (→ frame accuracy versus speed)
2. Why motion + audio instead of learning from scratch? (→ baseline first, model
   second)
3. How did you measure precision@5, and who labelled the ground truth? (→
   protocol)
4. Would a three-hour video kill the pipeline? (→ streaming, memory)
5. How do you determine downbeats, and what happens when you get it wrong? (→
   phase heuristic, admit it)
6. What does **not** work? (→ error analysis; this is the question that earns the
   most points)

---

## Signs a project will be read as "copied from a tutorial"

Avoid these five:

- The dataset is something off the shelf (`coco128`, `cifar10`) with nothing of
  yours in it
- No measurements, only screenshots of results
- The README never mentions what failed
- The commit history is a single "initial commit"
- No runnable demo, only a notebook

The opposite five earn points: self-collected data, an ablation with numbers, an
error analysis, green CI, and a demo link.
