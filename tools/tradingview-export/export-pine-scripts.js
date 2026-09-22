(async () => {
  const LIST_URL = "https://pine-facade.tradingview.com/pine-facade/list/?filter=saved";
  const SOURCE_URL = (id, version) =>
    `https://pine-facade.tradingview.com/pine-facade/get/${encodeURIComponent(id)}/${encodeURIComponent(version || 1)}`;

  const listResponse = await fetch(LIST_URL, { credentials: "include" });
  if (!listResponse.ok) throw new Error(`List failed: HTTP ${listResponse.status}`);
  const scripts = await listResponse.json();
  if (!Array.isArray(scripts)) throw new Error("Unexpected list response");

  const results = new Array(scripts.length);
  let nextIndex = 0;

  async function worker() {
    while (true) {
      const i = nextIndex++;
      if (i >= scripts.length) return;
      const meta = scripts[i];
      const id = meta.scriptIdPart;
      const version = meta.version || 1;
      const name = meta.scriptName || meta.scriptTitle || `Untitled_${i + 1}`;
      const principal = /^\.\[.+\]$/.test(name.trim());

      try {
        if (!id) throw new Error("scriptIdPart missing");
        const response = await fetch(SOURCE_URL(id, version), { credentials: "include" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        const source = typeof data.source === "string" ? data.source : "";
        if (!source) throw new Error("empty source");
        results[i] = {
          ok:true, principal, name, id, version,
          modified:meta.modified ?? null,
          metadata:meta,
          stats:{characters:source.length, lines:source.split("\n").length},
          source
        };
        console.log(`[${i+1}/${scripts.length}] OK ${principal?"★ ":""}${name}`);
      } catch (error) {
        results[i] = {
          ok:false, principal, name, id:id ?? null, version,
          metadata:meta, error:String(error?.message || error), source:null
        };
        console.error(`[${i+1}/${scripts.length}] ERROR ${name}`, error);
      }
    }
  }

  await Promise.all(Array.from({length:Math.min(4,Math.max(1,scripts.length))},()=>worker()));

  const success=results.filter(x=>x?.ok);
  const failed=results.filter(x=>!x?.ok);
  const principals=success.filter(x=>x.principal);
  const backup={
    format:"TradingView-Pine-Backup",
    formatVersion:1,
    exportedAt:new Date().toISOString(),
    source:"pine-facade / read-only",
    totals:{discovered:scripts.length,exported:success.length,failed:failed.length,principalScripts:principals.length},
    scripts:results
  };

  window.__TV_PINE_BACKUP__=backup;
  console.table(results.map((x,i)=>({
    "#":i+1, principal:x?.principal?"★":"", name:x?.name, version:x?.version,
    lines:x?.stats?.lines ?? "", chars:x?.stats?.characters ?? "",
    status:x?.ok?"OK":"ERROR", error:x?.error ?? ""
  })));

  const blob=new Blob([JSON.stringify(backup,null,2)],{type:"application/json;charset=utf-8"});
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.href=url;
  a.download=`TradingView_Pine_Backup_${new Date().toISOString().replace(/[:.]/g,"-")}.json`;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),5000);
  return backup.totals;
})();