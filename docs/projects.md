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

Timeline reordering becomes part of the project after **Apply timeline order**.
Drag before/after a clip or use its arrow buttons, then apply. Applying creates
an undo checkpoint and leaves source timestamps unchanged. Timeline edits not
yet applied, like pending table edits, are not included in a saved project.

The format is versioned (`format: beatcut-project`, `version: 1`). Unknown versions,
invalid timestamps and settings, and files over 1 MB are rejected. Restoring
also validates timestamps against the actual video and available music. The web
demo's source-duration limit still applies. Undo history and exported MP4s are
not included; reopening starts a new undo history.

Manual edits preserve exact source timestamps and do not automatically snap cuts
to musical bars. A saved selection is not an independent highlight annotation
for the evaluation protocol: it was derived from BeatCut's proposed highlights.
