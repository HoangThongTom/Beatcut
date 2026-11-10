// Exercises the actual component event handlers without a browser dependency.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
function setup(beats = []) {
  const elements = new Map(), listeners = {}, messages = [];
  class Element {
    constructor() { this.children = []; this.style = {}; this.classList = {add(){}, remove(){}}; }
    set id(value) { this._id = value; elements.set(value, this); }
    get id() { return this._id; }
    append(...children) { this.children.push(...children); }
    replaceChildren() { this.children = []; }
    setAttribute() {}
    focus() {}
    getBoundingClientRect() { return {x: 0, width: 100}; }
  }
  for (const id of ['track', 'apply', 'summary']) { const e = new Element(); e.id = id; }
  const parent = {postMessage(message) { messages.push(message); }};
  const context = {
    document: {getElementById: id => elements.get(id), createElement: () => new Element(),
               body: {scrollHeight: 200}},
    window: {parent, addEventListener(type, callback) { listeners[type] = callback; }},
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../app/timeline/timeline.js'), 'utf8'), context);
  assert.equal(messages[0].type, 'streamlit:componentReady');
  listeners.message({source: parent, data: {type: 'streamlit:render', args: {duration: 40, beats, clips: [
    {id: 0, start: 1, end: 4}, {id: 1, start: 10, end: 14}, {id: 2, start: 20, end: 25},
  ]}}});
  return {elements, messages, listeners, parent};
}

test('drag, arrow controls and apply send the new order to Streamlit', () => {
  const {elements, messages} = setup();
  assert.equal(elements.get('apply').disabled, true);
  const transfer = {setData(key, value) { this.value = value; }, getData() { return this.value; }};
  elements.get('clip-0').ondragstart({dataTransfer: transfer});
  elements.get('clip-2').ondrop({preventDefault(){}, dataTransfer: transfer, clientX: 90});
  assert.deepEqual(elements.get('track').children.map(e => e.id), ['clip-1', 'clip-2', 'clip-0']);
  elements.get('apply').onclick();
  let applied = messages.findLast(m => m.type === 'streamlit:setComponentValue');
  assert.deepEqual(Array.from(applied.value, clip => clip.id), [1, 2, 0]);
  elements.get('clip-0').children[3].onclick(); // move earlier
  assert.deepEqual(elements.get('track').children.map(e => e.id), ['clip-1', 'clip-0', 'clip-2']);
  elements.get('apply').onclick();
  applied = messages.findLast(m => m.type === 'streamlit:setComponentValue');
  assert.deepEqual(Array.from(applied.value, clip => clip.id), [1, 0, 2]);
});

test('trim handles clamp to the source and keep a 0.1s minimum', () => {
  const {elements, messages} = setup();
  let handle = elements.get('end-0');
  handle.value = '50'; handle.oninput(); handle.onchange();
  assert.equal(elements.get('end-0').value, '40');
  handle = elements.get('start-0');
  handle.value = '45'; handle.oninput(); handle.onchange();
  assert.equal(elements.get('start-0').value, '39.9');
  elements.get('apply').onclick();
  const first = messages.findLast(m => m.type === 'streamlit:setComponentValue').value[0];
  assert.equal(first.start, 39.9);
  assert.equal(first.end, 40);
});

test('snap targets cumulative music cuts, respects bounds and supports either handle', () => {
  const {elements} = setup([3.2, 7.4, 50]);
  let handle = elements.get('end-1');
  handle.value = '14.3'; handle.oninput(); handle.onchange();
  // First clip is 3s, so the second duration snaps to 7.4 - 3 = 4.4s.
  assert.equal(elements.get('end-1').value, '14.4');
  handle = elements.get('start-0');
  handle.value = '0.9'; handle.oninput(); handle.onchange();
  assert.equal(elements.get('start-0').value, '0.8');
  handle = elements.get('end-2');
  handle.value = '40'; handle.oninput(); handle.onchange();
  assert.equal(elements.get('end-2').value, '40');
});

test('keyboard snapping moves to the next beat instead of sticking at the current beat', () => {
  const {elements} = setup([3, 3.5, 4]);
  elements.get('end-0').onkeydown({key: 'ArrowRight', preventDefault(){}});
  assert.equal(elements.get('end-0').value, '4.5');
  elements.get('end-0').onkeydown({key: 'ArrowLeft', preventDefault(){}});
  assert.equal(elements.get('end-0').value, '4');
});
