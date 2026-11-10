# BeatCut project files

After applying edits in **Make it yours**, click **Save project** to download
`beatcut-project.json`. Keep the original gameplay and music alongside it.

To continue in another session:

1. Upload the same original gameplay and music in the two media upload fields.
2. Expand **Open a saved project**, upload the JSON and click **Open project**.
3. Continue editing, then click **Export edited MP4**. No highlight analysis is needed.

Only applied edits are saved. The JSON contains the clip keep flags, source
start/end times, playback order, music start, audio mix settings and SHA-256
identities of both source files. The original filenames are hints; contents must
match, even if you rename the files. No media, server paths or credentials are saved.

Timeline order and trims become part of the project after **Apply timeline edits**.
Drag before/after a clip or use its arrow buttons; use Start / End handles to trim
or extend the source range. Applying creates an undo checkpoint. Timeline edits not
yet applied, like pending table edits, are not included in a saved project.

The format is versioned (`format: beatcut-project`, `version: 1`). Unknown versions,
invalid timestamps and settings, and files over 1 MB are rejected. Restoring
also validates timestamps against the actual video and available music. The web
demo's source-duration limit still applies. Undo history and exported MP4s are
not included; reopening starts a new undo history.

Table edits preserve exact source timestamps. Optional **Snap to music beats**
on the timeline aligns the edited clip's outgoing montage cut to a detected beat
within 0.25s (including the music offset and earlier clip lengths). Keyboard
arrows on a focused handle jump between beats with Snap enabled. Source bounds
and the 0.1s minimum still apply. Reordering or trimming can shift later cuts;
there is no automatic realignment of all cuts. Beats are loaded from the shared
music cache, or detected without analyzing gameplay when a project is reopened.
Only the resulting times are saved; the Snap toggle is a session preference.

**Audio mix** changes music/game volume and whether game audio is kept. Click
**Apply audio mix** before saving or exporting. These settings participate in
the same undo history as clip edits, and reopen with the saved project. Export
an edited MP4 to hear the applied mix; sliders do not alter an already rendered
preview. Music volume also applies when game audio is disabled or absent.

A saved selection is not an independent highlight annotation
for the evaluation protocol: it was derived from BeatCut's proposed highlights.
