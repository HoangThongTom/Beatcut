"use strict";
let clips = [], original = "", disabled = false;
const track = document.getElementById("track");
const apply = document.getElementById("apply");
const summary = document.getElementById("summary");
function send(type, fields) {
  window.parent.postMessage({isStreamlitMessage: true, type, ...fields}, "*");
}
function ids() { return clips.map(clip => clip.id); }
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
  const changed = JSON.stringify(ids()) !== original;
  apply.disabled = disabled || !changed;
  summary.textContent = `${clips.length} clips · ${offset.toFixed(1)}s${changed ? " · Order not applied yet" : " · Applied order"}`;
  send("streamlit:setFrameHeight", {height: document.body.scrollHeight + 8});
}
apply.onclick = () => {
  apply.disabled = true;
  send("streamlit:setComponentValue", {value: ids(), dataType: "json"});
};
let lastArgs = "";
window.addEventListener("message", event => {
  if (event.source !== window.parent || event.data?.type !== "streamlit:render") return;
  const incoming = event.data.args.clips;
  const signature = JSON.stringify(incoming);
  disabled = Boolean(event.data.disabled);
  if (signature !== lastArgs) {
    clips = incoming.map(clip => ({...clip}));
    original = JSON.stringify(ids());
    lastArgs = signature;
  }
  render();
});
window.addEventListener("resize", () => send("streamlit:setFrameHeight", {height: document.body.scrollHeight + 8}));
send("streamlit:componentReady", {apiVersion: 1});
