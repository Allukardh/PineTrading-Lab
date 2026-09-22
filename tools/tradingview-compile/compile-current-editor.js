(async () => {
  // TradingView Pine compile helper.
  // READS the currently open Pine Editor and sends the source to TradingView's
  // own translate_light compiler endpoint. It does not modify or save the editor.

  function findMonacoEditor() {
    const container = document.querySelector(".monaco-editor.pine-editor-monaco");
    if (!container) return null;

    let el = container;
    let fiberKey;

    for (let i = 0; i < 20; i++) {
      if (!el) break;
      fiberKey = Object.keys(el).find(k => k.startsWith("__reactFiber$"));
      if (fiberKey) break;
      el = el.parentElement;
    }

    if (!fiberKey || !el) return null;

    let current = el[fiberKey];
    for (let depth = 0; depth < 15; depth++) {
      if (!current) break;

      const env = current.memoizedProps?.value?.monacoEnv;
      if (env?.editor && typeof env.editor.getEditors === "function") {
        const editors = env.editor.getEditors();
        if (editors.length > 0) return editors[0];
      }

      current = current.return;
    }

    return null;
  }

  const editor = findMonacoEditor();
  if (!editor) {
    throw new Error(
      "Pine Monaco editor not found. Open the Pine Editor, load the candidate source, and retry."
    );
  }

  const source = editor.getValue();
  if (!source || !source.trim()) {
    throw new Error("The Pine Editor is empty.");
  }

  const body = new URLSearchParams();
  body.append("source", source);

  const endpoint =
    "https://pine-facade.tradingview.com/pine-facade/translate_light" +
    "?user_name=Guest&pine_id=00000000-0000-0000-0000-000000000000";

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body
  });

  if (!response.ok) {
    throw new Error(`TradingView compiler returned HTTP ${response.status} ${response.statusText}`);
  }

  const payload = await response.json();
  const inner = payload?.result;
  const errors = [];
  const warnings = [];

  for (const e of inner?.errors2 ?? []) {
    errors.push({
      severity: "ERROR",
      line: e.start?.line ?? null,
      column: e.start?.column ?? null,
      endLine: e.end?.line ?? null,
      endColumn: e.end?.column ?? null,
      message: e.message ?? String(e)
    });
  }

  for (const w of inner?.warnings2 ?? []) {
    warnings.push({
      severity: "WARNING",
      line: w.start?.line ?? null,
      column: w.start?.column ?? null,
      message: w.message ?? String(w)
    });
  }

  if (typeof payload?.error === "string" && payload.error) {
    errors.push({
      severity: "ERROR",
      line: null,
      column: null,
      message: payload.error
    });
  }

  const compiled = errors.length === 0;

  const summary = {
    compiled,
    characters: source.length,
    lines: source.split("\n").length,
    errors: errors.length,
    warnings: warnings.length
  };

  console.log("══════════════════════════════════════════");
  console.log(" PineTrading-Lab — TradingView Compile");
  console.log(" MODE: READ EDITOR + COMPILE ONLY / NO SAVE");
  console.log("══════════════════════════════════════════");
  console.table([summary]);

  if (errors.length) {
    console.error("Compiler errors:");
    console.table(errors);
  }

  if (warnings.length) {
    console.warn("Compiler warnings:");
    console.table(warnings);
  }

  if (compiled) {
    console.log("✅ COMPILE PASS");
  } else {
    console.error("❌ COMPILE FAIL");
  }

  window.__PINE_TRADING_COMPILE_RESULT__ = {
    summary,
    errors,
    warnings,
    raw: payload
  };

  return { summary, errors, warnings };
})();