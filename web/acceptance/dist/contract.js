/* Browser-local contract subset. Source of truth: ssr_knowledge/contracts.py. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.KnowledgeContract = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const LIMITS = Object.freeze({ bytes: 256000, depth: 64, nodes: 10000 });
  const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
  const object = value => value !== null && typeof value === "object" && !Array.isArray(value);
  const isType = (value, expected) => {
    switch (expected) {
      case "object": return object(value);
      case "array": return Array.isArray(value);
      case "string": return typeof value === "string";
      case "integer": return Number.isInteger(value);
      case "number": return typeof value === "number";
      case "boolean": return typeof value === "boolean";
      case "null": return value === null;
      default: throw new Error("unsupported schema type: " + expected);
    }
  };
  function equal(a, b) {
    if (a === b) return true;
    if (Array.isArray(a) && Array.isArray(b)) return a.length === b.length && a.every((v, i) => equal(v, b[i]));
    if (object(a) && object(b)) return Object.keys(a).length === Object.keys(b).length && Object.keys(a).every(k => own(b, k) && equal(a[k], b[k]));
    return false;
  }
  function validate(value, schema, path = "$") {
    const errors = [];
    const expected = schema.type;
    if (expected && !(Array.isArray(expected) ? expected.some(t => isType(value, t)) : isType(value, expected))) {
      const label = Array.isArray(expected) ? "[" + expected.map(t => "'" + t + "'").join(", ") + "]" : expected;
      return [path + ": expected " + label];
    }
    if (own(schema, "enum") && !schema.enum.some(item => equal(item, value))) errors.push(path + ": value is outside enum");
    if (object(value)) {
      for (const key of schema.required || []) if (!own(value, key)) errors.push(path + "." + key + ": required");
      const properties = schema.properties || {};
      for (const [key, item] of Object.entries(value)) {
        if (own(properties, key)) errors.push(...validate(item, properties[key], path + "." + key));
        else if (schema.additionalProperties === false) errors.push(path + "." + key + ": additional property is not allowed");
      }
    }
    if (Array.isArray(value) && schema.items) value.forEach((item, i) => errors.push(...validate(item, schema.items, path + "[" + i + "]")));
    return errors;
  }
  function bounded(value) {
    const pending = [{ value, depth: 0 }];
    let nodes = 0;
    while (pending.length) {
      const item = pending.pop();
      if (++nodes > LIMITS.nodes) throw new Error("超過 " + LIMITS.nodes.toLocaleString("en-US") + " 個 JSON 節點。");
      if (item.depth > LIMITS.depth) throw new Error("JSON 深度超過 " + LIMITS.depth + " 層。");
      if (typeof item.value === "number" && (!Number.isFinite(item.value) || (Number.isInteger(item.value) && !Number.isSafeInteger(item.value)))) throw new Error("數字必須有限，整數必須位於 JavaScript 安全整數範圍。");
      if (item.value !== null && typeof item.value === "object") {
        for (const child of Object.values(item.value)) pending.push({ value: child, depth: item.depth + 1 });
        if (pending.length + nodes > LIMITS.nodes) throw new Error("超過 " + LIMITS.nodes.toLocaleString("en-US") + " 個 JSON 節點。");
      }
    }
  }
  function run(text, name, schemas) {
    const base = { engine: "browser-contract-subset-v1", schema: name, scope: "structure_only", persisted: false };
    try {
      if (!own(schemas, name)) throw new Error("未知的契約；請重新選擇。");
      if (typeof text !== "string" || !text.trim()) throw new Error("請先輸入 JSON 或載入合成範例。");
      if (new TextEncoder().encode(text).length > LIMITS.bytes) throw new Error("輸入超過 256,000 UTF-8 bytes。");
      let value;
      try { value = JSON.parse(text); } catch (error) { throw new Error("JSON 語法錯誤：" + error.message); }
      bounded(value);
      const errors = validate(value, schemas[name]);
      return { ...base, status: errors.length ? "schema_invalid" : "schema_valid", errors,
        note: "僅檢查契約結構；未入庫、未核對來源、未批准、未發布。" };
    } catch (error) {
      return { ...base, status: "input_error", errors: [error.message] };
    }
  }
  function createSession(schemas, initialSchema) {
    let generation = 0;
    const state = { schema: initialSchema, text: "", phase: "idle", result: null };
    return {
      state,
      edit(text) { generation++; state.text = text; state.phase = "idle"; state.result = null; },
      select(schema) { generation++; state.schema = schema; state.phase = "idle"; state.result = null; },
      begin() { if (state.phase === "queued") return null; state.result = null; state.phase = "queued"; return ++generation; },
      finish(ticket) { if (ticket !== generation || state.phase !== "queued") return false; state.result = run(state.text, state.schema, schemas); state.phase = "done"; return true; },
      cancel() { if (state.phase !== "queued") return false; generation++; state.phase = "cancelled"; state.result = null; return true; }
    };
  }
  return Object.freeze({ LIMITS, validate, run, createSession });
});
