(function () {
  "use strict";
  const data = window.KnowledgeAcceptanceData;
  const engine = window.KnowledgeContract;
  const el = id => document.getElementById(id);
  if (!data || !engine) {
    el("result-title").textContent = "頁面元件未載入";
    el("result-description").textContent = "請確認整個 dist 資料夾都存在，並查閱本機頁面說明。尚未執行驗證。";
    return;
  }
  const names = Object.keys(data.schemas).sort();
  const session = engine.createSession(data.schemas, names[0]);
  let pending = null;
  let runCount = 0;
  const input = el("json-input");
  const selector = el("schema-select");
  input.value = ""; // Start without restored form content or a stale validation state.
  selector.replaceChildren(...names.map(name => { const option = document.createElement("option"); option.value = name; option.textContent = data.labels[name]; return option; }));
  selector.value = names[0];
  el("version").textContent = data.version.branch + " · " + data.version.base_commit.slice(0, 8);
  el("version").title = data.version.base_commit;
  el("source-fingerprint").textContent = JSON.stringify({ version: data.version, source_sha256: data.source_sha256 }, null, 2);
  for (const id of ["schema-select", "json-input", "sample", "invalid-sample", "show-schema", "validate", "clear", "back-to-input"]) el(id).disabled = false;
  function stopTimer() { if (pending !== null) { clearTimeout(pending); pending = null; } }
  function render() {
    const state = session.state;
    const queued = state.phase === "queued";
    el("validate").disabled = queued;
    el("cancel").disabled = !queued;
    el("input-size").textContent = new TextEncoder().encode(state.text).length.toLocaleString("en-US") + " bytes";
    el("schema-description").textContent = data.schemas[state.schema].title + " · " + state.schema;
    el("schema-box").textContent = JSON.stringify(data.schemas[state.schema], null, 2);
    const tag = el("result-tag"); tag.className = "tag";
    const result = state.result;
    el("result-json").hidden = !result;
    el("error-list").hidden = !result || !result.errors.length;
    el("result-empty").hidden = Boolean(result);
    el("error-list").replaceChildren();
    el("result-json").textContent = result ? JSON.stringify(result, null, 2) : "";
    if (result) {
      const valid = result.status === "schema_valid";
      tag.classList.add(valid ? "pass" : "fail"); tag.textContent = valid ? "結構通過" : result.status === "schema_invalid" ? "結構不符" : "輸入錯誤";
      el("result-title").textContent = valid ? "結構檢查通過" : result.status === "schema_invalid" ? "請依錯誤路徑修正" : "無法開始驗證";
      el("result-description").textContent = "第 " + runCount + " 次實際執行。" + (valid ? "符合所選契約的支援子集。未執行入庫、批准或發布。" : "這是本次輸入的實際結果，沒有沿用先前輸出。");
      for (const message of result.errors) { const item = document.createElement("li"); item.textContent = message; el("error-list").append(item); }
    } else if (queued) {
      tag.classList.add("queued"); tag.textContent = "待執行";
      el("result-title").textContent = "等待開始驗證";
      el("result-description").textContent = "可按取消或 Escape。這只會取消尚未開始的排程。";
    } else if (state.phase === "cancelled") {
      tag.textContent = "已取消"; el("result-title").textContent = "已取消待執行";
      el("result-description").textContent = "未執行本次驗證；輸入仍保留，可修改後再送出。";
    } else {
      tag.textContent = "尚未執行"; el("result-title").textContent = "等待你的輸入";
      el("result-description").textContent = "選擇契約並載入範例，再執行一次結構驗證。編輯後舊結果已失效。";
    }
  }
  input.addEventListener("input", () => { stopTimer(); session.edit(input.value); render(); });
  selector.addEventListener("change", () => { stopTimer(); session.select(selector.value); render(); });
  function loadSample(invalid) {
    stopTimer();
    const sample = JSON.parse(JSON.stringify(data.samples[session.state.schema]));
    if (invalid) delete sample[data.schemas[session.state.schema].required[0]];
    input.value = JSON.stringify(sample, null, 2); session.edit(input.value); render(); input.focus();
  }
  el("sample").addEventListener("click", () => loadSample(false));
  el("invalid-sample").addEventListener("click", () => loadSample(true));
  el("clear").addEventListener("click", () => { stopTimer(); input.value = ""; session.edit(""); render(); input.focus(); });
  el("show-schema").addEventListener("click", () => { const box = el("schema-box"); box.hidden = !box.hidden; el("show-schema").setAttribute("aria-expanded", String(!box.hidden)); });
  el("back-to-input").addEventListener("click", () => { input.focus(); input.scrollIntoView({ block: "center" }); });
  function cancel() { stopTimer(); if (session.cancel()) render(); }
  el("cancel").addEventListener("click", cancel);
  el("validation-form").addEventListener("submit", event => {
    event.preventDefault(); const ticket = session.begin(); if (ticket === null) return; render();
    pending = setTimeout(() => { pending = null; if (session.finish(ticket)) { runCount++; render(); } }, 180);
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape") cancel();
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && document.activeElement === input) { event.preventDefault(); el("validation-form").requestSubmit(); }
  });
  render();
})();
