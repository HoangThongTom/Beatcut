# Evaluation protocol

**English** | [Tiếng Việt](eval-protocol.vi.md)

Unit tests prove the code does what it claims. They say nothing about whether
the *selected clips are good*. This document defines how to measure that, so the
number in the README means something.

## What counts as a highlight

Pick one definition and never change it mid-dataset:

> A highlight is a moment a human would keep in a 45-second montage: a kill, a
> clutch, a funny fail, a big play — an event with a clear start and end.

"Clear start and end" matters. Vague definitions produce labels nobody can
reproduce, including you in two weeks.

## Building the ground truth

1. Record or select **10 VODs**, each 10–60 minutes, from your own gameplay.
   Different maps, different sessions — not ten clips of the same match.
2. For each VOD, have **two people** independently mark highlight ranges
   (start, end) without seeing the other's marks and without seeing BeatCut's
   output.
3. Keep intervals where the two annotators agree within ±2 seconds. Drop the
   rest. This is your ground truth.
4. Store as JSON next to the video:

```json
{
  "video": "match_01.mp4",
  "annotators": ["A", "B"],
  "highlights": [
    {"start": 412.0, "end": 419.5},
    {"start": 1305.0, "end": 1311.0}
  ]
}
```

5. Split into `dev` (6 VODs, tune weights/config) and `test` (4 VODs, report
   once). Tuning on the test set and then reporting it is how the number becomes
   meaningless.

## Metrics

### Local independent labeling

On Windows, double-click **Start-Labeling.cmd** or run
`scripts/start-local.ps1 -Annotate`. Open [localhost:8503](http://localhost:8503),
enter your annotator ID and a local path to the original video, then open it.
Add source start/end intervals, apply table corrections/removals, and save your
own annotation JSON before switching videos or IDs. Resume only your own file.
This screen shows no automatic predictions or the other person's ranges.
Videos are read locally; no video upload is required. Empty labels can be saved.

After both people independently finish, combine their files:

```powershell
beatcut agree data\labels\match_02.A.annotations.json data\labels\match_02.B.annotations.json -o data\labels\match_02.json
```

The command requires matching video SHA-256 and duration, and distinct annotator
IDs. Distinct IDs do not establish actual independence; people must follow the
protocol. Both endpoints must be within 2 seconds. Only mutually unique pairs
are kept; ambiguous/unmatched labels are excluded and counted. Agreed endpoints
are the averages of the two annotations. Original files are never overwritten;
choose a fresh output path to rerun. The result is accepted by `beatcut score`.
No agreed highlights means the current score CLI cannot evaluate that VOD.

Keep the raw annotations. Files contain source identity and labels, not media or
local paths. Projects/predictions are not independent annotations and cannot be
imported by this tool. The 10-VOD, 6-dev/4-test requirement above still applies.

### Scoring

Run `beatcut analyze VIDEO MUSIC --json out.json`, then score the selection
against the labels:

```powershell
beatcut score data\labels\match_01.json out.json -k 5
```

The metrics below are exactly what that command reports.

**Precision@k** — of the k clips BeatCut picked, how many overlap a real
highlight by at least 50% of the clip's duration?

```
P@k = |{picked clip i ≤ k : overlap_i ≥ 0.5 × duration_i}| / k
```

This is the headline number. It answers "if a creator keeps the first k clips,
how many are usable?".

**Temporal IoU** — for each picked clip, `intersection / union` with the matched
highlight. Report the mean over matched pairs; it captures whether the cut
starts and ends in the right place, not just whether it is in the right area.

**Recall / coverage** — of all labelled highlights, what fraction did BeatCut
find at all? A model that always picks the same three spectacular moments has
high precision and terrible recall.

**Beat alignment error** — for each cut point, the absolute distance in
milliseconds to the nearest downbeat. Report mean and p95. This is the one
number that is cheap to measure and immediately comparable between versions.

## Reporting

Put a table in the README with `dev` and `test` columns, the number of VODs, and
the config hash. If precision is 0.62, report 0.62 — an intern who reports an
honest 0.62 with a clear error analysis is more convincing than one who reports
0.95 that nobody can reproduce.

## Error analysis (do this, it is the interview material)

For every false positive, write one sentence about why it was picked. After ten
examples a pattern usually appears, and the pattern becomes the M2 change:
"picked menu screens because static UI still has motion", "missed quiet clutch
rounds because audio weight dominated", "cut 0.3 s too early because downbeat
phase was off by one beat". That list is worth more in an interview than the
metric itself.
