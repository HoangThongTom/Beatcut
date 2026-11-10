// Exercises the actual component event handlers without a browser dependency.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
test('drag, arrow controls and apply send the new order to Streamlit', () => {
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
  listeners.message({source: parent, data: {type: 'streamlit:render', args: {clips: [
    {id: 0, start: 1, end: 4}, {id: 1, start: 10, end: 14}, {id: 2, start: 20, end: 25},
  ]}}});
  assert.equal(elements.get('apply').disabled, true);
  const transfer = {setData(key, value) { this.value = value; }, getData() { return this.value; }};
  elements.get('clip-0').ondragstart({dataTransfer: transfer});
  elements.get('clip-2').ondrop({preventDefault(){}, dataTransfer: transfer, clientX: 90});
  assert.deepEqual(elements.get('track').children.map(e => e.id), ['clip-1', 'clip-2', 'clip-0']);
  elements.get('apply').onclick();
  let applied = messages.findLast(m => m.type === 'streamlit:setComponentValue');
  assert.deepEqual(Array.from(applied.value), [1, 2, 0]);
  elements.get('clip-0').children[3].onclick(); // move earlier
  assert.deepEqual(elements.get('track').children.map(e => e.id), ['clip-1', 'clip-0', 'clip-2']);
  elements.get('apply').onclick();
  applied = messages.findLast(m => m.type === 'streamlit:setComponentValue');
  assert.deepEqual(Array.from(applied.value), [1, 0, 2]);
});
