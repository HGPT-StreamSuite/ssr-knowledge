"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const fs = require("node:fs");
const vm = require("node:vm");
const web = path.join(__dirname, "../web/acceptance/dist");
require(path.join(web, "data.js"));
const { schemas, samples } = globalThis.KnowledgeAcceptanceData;
const engine = require(path.join(web, "contract.js"));
const name = "record.schema.json";
const text = JSON.stringify(samples[name]);

test("all eight synthetic samples pass their actual selected schemas", () => {
  assert.equal(Object.keys(schemas).length, 8);
  for (const key of Object.keys(schemas)) assert.equal(engine.run(JSON.stringify(samples[key]), key, schemas).status, "schema_valid", key);
});
test("missing required field names the actual path", () => {
  const value = structuredClone(samples[name]); delete value.source.source_id;
  assert.deepEqual(engine.run(JSON.stringify(value), name, schemas).errors, ["$.source.source_id: required"]);
});
test("wrong types, invalid enum and additional fields are rejected", () => {
  const value = structuredClone(samples[name]); value.kind = "invented"; value.tags = [false]; value.extra = "inert";
  assert.deepEqual(engine.run(JSON.stringify(value), name, schemas).errors, ["$.kind: value is outside enum", "$.tags[0]: expected string", "$.extra: additional property is not allowed"]);
});
test("empty, malformed and unknown inputs have no success status", () => {
  for (const value of ["", " ", "{", "NaN", "undefined"]) assert.equal(engine.run(value, name, schemas).status, "input_error");
  assert.equal(engine.run(text, "unknown", schemas).status, "input_error");
});
test("false and arrays do not satisfy object root", () => {
  for (const value of ["false", "[]", "null"]) assert.equal(engine.run(value, name, schemas).status, "schema_invalid");
});
test("HTML remains data and __proto__ cannot pollute object properties", () => {
  const value = structuredClone(samples[name]); value.summary = "<script>globalThis.compromised = true</script>";
  assert.equal(engine.run(JSON.stringify(value), name, schemas).status, "schema_valid");
  const result = engine.run('{"__proto__":{"polluted":true}}', name, schemas);
  assert(result.errors.includes("$.__proto__: additional property is not allowed"));
  assert.equal({}.polluted, undefined); assert.equal(globalThis.compromised, undefined);
});
test("byte, nesting, node and numeric limits reject bounded inputs", () => {
  assert.equal(engine.run('"' + "界".repeat(100000) + '"', name, schemas).status, "input_error");
  assert.equal(engine.run("[".repeat(66) + "0" + "]".repeat(66), name, schemas).status, "input_error");
  assert.equal(engine.run(JSON.stringify(Array(10001).fill(null)), name, schemas).status, "input_error");
  for (const number of ["9007199254740993", "1e400"]) assert.equal(engine.run(number, name, schemas).status, "input_error");
});
test("repeat submission recomputes the same structural result without persistence", () => {
  const session = engine.createSession(schemas, name); session.edit(text);
  session.finish(session.begin()); const before = structuredClone(session.state.result);
  session.finish(session.begin()); assert.deepEqual(session.state.result, before);
  assert.equal(before.persisted, false);
});
test("duplicate queued submission does not add a job", () => {
  const session = engine.createSession(schemas, name); session.edit(text);
  const ticket = session.begin(); assert.equal(session.begin(), null); assert(session.finish(ticket));
});
test("cancel invalidates queued completion and preserves input", () => {
  const session = engine.createSession(schemas, name); session.edit(text); const ticket = session.begin();
  assert(session.cancel()); assert.equal(session.finish(ticket), false); assert.equal(session.state.result, null);
  assert.equal(session.state.text, text); assert.equal(session.state.phase, "cancelled");
});
test("editing or switching schemas invalidates old success and pending jobs", () => {
  const session = engine.createSession(schemas, name); session.edit(text); session.finish(session.begin());
  session.edit("{"); assert.equal(session.state.result, null);
  const ticket = session.begin(); session.select("candidate.schema.json");
  assert.equal(session.finish(ticket), false); assert.equal(session.state.result, null);
});
test("clearing then submitting produces input_error instead of an old result", () => {
  const session = engine.createSession(schemas, name); session.edit(text); session.finish(session.begin());
  session.edit(""); session.finish(session.begin()); assert.equal(session.state.result.status, "input_error");
});

// In-memory event wiring only. This is not a browser, layout or accessibility test.
function page(restoredInput = "") {
  const elements = new Map(); const timers = new Map(); let clock = 0;
  const document = { activeElement: null, handlers: {},
    getElementById(id) { assert(elements.has(id), "app references missing HTML id: " + id); return elements.get(id); },
    createElement(tag) { return element(tag); },
    addEventListener(type, callback) { this.handlers[type] = callback; }
  };
  function element(id) {
    return { id, value: "", textContent: "", disabled: false, hidden: false, className: "", children: [], handlers: {}, attributes: {},
      classList: { add() {} },
      replaceChildren(...items) { this.children = items; }, append(item) { this.children.push(item); },
      addEventListener(type, callback) { this.handlers[type] = callback; },
      setAttribute(name, value) { this.attributes[name] = value; },
      focus() { document.activeElement = this; }, scrollIntoView() { this.scrolled = true; },
      requestSubmit() { this.handlers.submit({ preventDefault() {} }); }
    };
  }
  for (const match of fs.readFileSync(path.join(web, "index.html"), "utf8").matchAll(/\bid="([^"]+)"/g)) elements.set(match[1], element(match[1]));
  elements.get("schema-box").hidden = true;
  elements.get("json-input").value = restoredInput;
  const context = { window: { KnowledgeAcceptanceData: globalThis.KnowledgeAcceptanceData, KnowledgeContract: engine }, document,
    TextEncoder, setTimeout(callback) { const ticket = ++clock; timers.set(ticket, callback); return ticket; }, clearTimeout(ticket) { timers.delete(ticket); } };
  vm.runInNewContext(fs.readFileSync(path.join(web, "app.js"), "utf8"), context, { filename: "app.js" });
  const get = id => document.getElementById(id);
  const click = id => { const target = get(id); assert(!target.disabled, id + " must be enabled"); target.handlers.click(); };
  const submit = () => get("validation-form").requestSubmit();
  const flush = () => { for (const [ticket, callback] of [...timers]) { timers.delete(ticket); callback(); } };
  return { get, click, submit, flush, document, timers, input(value) { get("json-input").value = value; get("json-input").handlers.input(); } };
}
test("page wiring: starts unexecuted, loads real sample and displays actual JSON result", () => {
  const ui = page(); assert.equal(ui.get("result-tag").textContent, "尚未執行");
  ui.click("sample"); assert(ui.get("json-input").value.includes("fixture-web-candidate"));
  ui.submit(); assert.equal(ui.get("result-tag").textContent, "待執行"); ui.flush();
  assert.equal(JSON.parse(ui.get("result-json").textContent).status, "schema_valid");
  assert.equal(ui.get("result-json").hidden, false);
});
test("page wiring: initialization discards restored form content", () => {
  const ui = page("stale synthetic input");
  assert.equal(ui.get("json-input").value, "");
  assert.equal(ui.get("result-json").hidden, true);
  assert.equal(ui.get("result-tag").textContent, "尚未執行");
});
test("page wiring: missing fields and malformed input replace a previous success", () => {
  const ui = page(); ui.click("sample"); ui.submit(); ui.flush();
  ui.click("invalid-sample"); assert.equal(ui.get("result-json").hidden, true);
  ui.submit(); ui.flush(); assert.equal(JSON.parse(ui.get("result-json").textContent).status, "schema_invalid");
  assert(ui.get("error-list").children[0].textContent.includes("candidate_id: required"));
  ui.input("{"); ui.submit(); ui.flush(); assert.equal(JSON.parse(ui.get("result-json").textContent).status, "input_error");
});
test("page wiring: repeated submit, cancel, return, clear and keyboard flows", () => {
  const ui = page(); ui.click("sample"); ui.submit(); ui.submit(); assert.equal(ui.timers.size, 1);
  ui.click("cancel"); ui.flush(); assert.equal(ui.get("result-tag").textContent, "已取消");
  assert.equal(ui.get("result-json").hidden, true); assert(ui.get("json-input").value);
  ui.get("json-input").focus();
  ui.document.handlers.keydown({ key: "Enter", ctrlKey: true, preventDefault() {} }); ui.flush();
  const first = ui.get("result-json").textContent;
  ui.submit(); ui.flush(); assert.equal(ui.get("result-json").textContent, first);
  ui.click("back-to-input"); assert.equal(ui.document.activeElement, ui.get("json-input"));
  ui.submit(); ui.document.handlers.keydown({ key: "Escape" }); ui.flush(); assert.equal(ui.get("result-tag").textContent, "已取消");
  ui.click("clear"); assert.equal(ui.get("json-input").value, ""); ui.submit(); ui.flush();
  assert.equal(JSON.parse(ui.get("result-json").textContent).status, "input_error");
});
test("page wiring: switching schemas discards output and schema details toggle", () => {
  const ui = page(); ui.click("sample"); ui.submit(); ui.flush();
  ui.get("schema-select").value = "tool-config.schema.json"; ui.get("schema-select").handlers.change();
  assert.equal(ui.get("result-tag").textContent, "尚未執行");
  ui.click("sample"); ui.submit(); ui.flush(); assert.equal(JSON.parse(ui.get("result-json").textContent).schema, "tool-config.schema.json");
  ui.click("show-schema"); assert.equal(ui.get("schema-box").hidden, false); assert.equal(ui.get("show-schema").attributes["aria-expanded"], "true");
  ui.click("show-schema"); assert.equal(ui.get("schema-box").hidden, true);
});
