"use strict";
let clips = [], original = "", disabled = false, duration = 0, beats = [];
const track = document.getElementById("track");
const apply = document.getElementById("apply");
const summary = document.getElementById("summary");
function send(type, fields) {
  window.parent.postMessage({isStreamlitMessage: true, type, ...fields}, "*");
}
function trim(clip, edge, value, offset, direction = 0) {
  const low = edge === "start" ? 0 : clip.start + 0.1;
  const high = edge === "start" ? clip.end - 0.1 : duration;
  value = Math.max(low, Math.min(high, value));
  // Music overlays the montage: snap cumulative cut time, never a source timestamp.
  const candidates = beats.map(beat => edge === "start"
    ? clip.end - (beat - offset) : clip.start + beat - offset)
    .filter(time => time >= low && time <= high);
  const targets = direction
    ? candidates.filter(time => direction * (time - clip[edge]) > 0.0001) : candidates;
  if (targets.length) {
    const nearest = targets.reduce((a, b) => Math.abs(a - value) <= Math.abs(b - value) ? a : b);
    if (direction || Math.abs(nearest - value) <= 0.25) value = nearest;
  }
  clip[edge] = Math.max(low, Math.min(high, Number(value.toFixed(4))));
}
function moveBefore(source, target, after = false) {
  if (source === target || disabled) return;
  const from = clips.findIndex(clip => clip.id === source);
  if (from < 0 || !clips.some(clip => clip.id === target)) return;
  const [clip] = clips.splice(from, 1);
  clips.splice(clips.findIndex(item => item.id === target) + Number(after), 0, clip);
  render();
}
function swap(index, delta) {
  const next = index + delta;
  if (disabled || next < 0 || next >= clips.length) return;
  [clips[index], clips[next]] = [clips[next], clips[index]];
  render();
  document.getElementById(`clip-${clips[next].id}`).focus();
}
function render() {
  track.replaceChildren();
  let offset = 0;
  clips.forEach((clip, index) => {
    const card = document.createElement("div");
    card.className = "clip";
    card.id = `clip-${clip.id}`;
    card.tabIndex = 0;
    card.draggable = !disabled;
    card.style.flexGrow = String(clip.end - clip.start);
    const time = document.createElement("div");
    time.className = "time";
    time.textContent = `${offset.toFixed(1)}s → ${(offset + clip.end - clip.start).toFixed(1)}s`;
    const title = document.createElement("strong");
    title.textContent = `Clip ${clip.id + 1}`;
    const source = document.createElement("div");
    source.className = "source";
    source.textContent = `${clip.start.toFixed(2)}–${clip.end.toFixed(2)}s · ${(clip.end-clip.start).toFixed(1)}s`;
    card.append(time, title, source);
    [-1, 1].forEach(delta => {
      const button = document.createElement("button");
      button.textContent = delta < 0 ? "←" : "→";
      button.setAttribute("aria-label", `Move clip ${clip.id + 1} ${delta < 0 ? "earlier" : "later"}`);
      button.disabled = disabled || index + delta < 0 || index + delta >= clips.length;
      button.onclick = () => swap(index, delta);
      card.append(button);
    });
    for (const edge of ["start", "end"]) {
      const label = document.createElement("label");
      label.textContent = edge === "start" ? "Start" : "End";
      const handle = document.createElement("input");
      handle.id = `${edge}-${clip.id}`;
      handle.type = "range";
      handle.min = edge === "start" ? "0" : String(clip.start + 0.1);
      handle.max = edge === "start" ? String(clip.end - 0.1) : String(duration);
      handle.step = "0.01";
      handle.value = String(clip[edge]);
      handle.disabled = disabled;
      handle.setAttribute("aria-label", `Clip ${clip.id + 1} ${edge} in source seconds`);
      handle.setAttribute("aria-valuetext", `${clip[edge].toFixed(2)} seconds`);
      handle.onpointerdown = event => { event.stopPropagation(); card.draggable = false; };
      handle.onpointerup = () => { card.draggable = !disabled; };
      handle.onpointercancel = handle.onpointerup;
      const clipOffset = offset;
      handle.oninput = () => {
        if (disabled) return;
        trim(clip, edge, Number(handle.value), clipOffset);
        handle.value = String(clip[edge]);
        handle.setAttribute("aria-valuetext", `${clip[edge].toFixed(2)} seconds`);
        source.textContent = `${clip.start.toFixed(2)}–${clip.end.toFixed(2)}s · ${(clip.end-clip.start).toFixed(1)}s`;
        time.textContent = `${clipOffset.toFixed(1)}s → ${(clipOffset + clip.end-clip.start).toFixed(1)}s`;
        updateSummary();
      };
      handle.onchange = () => { render(); document.getElementById(`${edge}-${clip.id}`).focus(); };
      handle.onkeydown = event => {
        if (disabled || !beats.length || !["ArrowLeft", "ArrowRight"].includes(event.key)) return;
        event.preventDefault();
        const direction = event.key === "ArrowLeft" ? -1 : 1;
        trim(clip, edge, clip[edge] + direction * 0.01, clipOffset, direction);
        render();
        document.getElementById(`${edge}-${clip.id}`).focus();
      };
      label.append(handle);
      card.append(label);
    }
    card.ondragstart = event => {
      event.dataTransfer.setData("text/plain", String(clip.id));
      event.dataTransfer.effectAllowed = "move";
      card.classList.add("dragging");
    };
    card.ondragend = () => card.classList.remove("dragging");
    card.ondragover = event => { event.preventDefault(); card.classList.add("over"); };
    card.ondragleave = () => card.classList.remove("over");
    card.ondrop = event => {
      event.preventDefault();
      card.classList.remove("over");
      const value = event.dataTransfer.getData("text/plain");
      const box = card.getBoundingClientRect();
      if (/^\d+$/.test(value)) moveBefore(Number(value), clip.id, event.clientX > box.x + box.width / 2);
    };
    track.append(card);
    offset += clip.end - clip.start;
  });
  updateSummary();
  send("streamlit:setFrameHeight", {height: document.body.scrollHeight + 8});
}
function updateSummary() {
  const changed = JSON.stringify(clips) !== original;
  apply.disabled = disabled || !changed;
  const total = clips.reduce((sum, clip) => sum + clip.end - clip.start, 0);
  summary.textContent = `${clips.length} clips · ${total.toFixed(1)}s${changed ? " · Edits not applied yet" : " · Applied edits"}`;
}
apply.onclick = () => {
  apply.disabled = true;
  send("streamlit:setComponentValue", {value: clips, dataType: "json"});
};
let lastArgs = "";
window.addEventListener("message", event => {
  if (event.source !== window.parent || event.data?.type !== "streamlit:render") return;
  const incoming = event.data.args.clips;
  duration = event.data.args.duration;
  beats = event.data.args.beats || [];
  const signature = JSON.stringify(incoming);
  disabled = Boolean(event.data.disabled);
  if (signature !== lastArgs) {
    clips = incoming.map(clip => ({...clip}));
    original = JSON.stringify(clips);
    lastArgs = signature;
  }
  render();
});
window.addEventListener("resize", () => send("streamlit:setFrameHeight", {height: document.body.scrollHeight + 8}));
send("streamlit:componentReady", {apiVersion: 1});
