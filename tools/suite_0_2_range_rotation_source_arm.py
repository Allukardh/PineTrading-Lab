#!/usr/bin/env python3
"""BTC RANGE_ROTATION source-arm readiness comparison."""
from __future__ import annotations
import argparse,json
from collections import Counter
from pathlib import Path

from tools.execution_candidate_reference import ExecutionResearchBar
from tools.execution_historical_evidence import build_context_dirs,distribution,load_dataset,pct,sha256_file
from tools.execution_integrated_evidence import build_market_locations,to_mm_candles
from tools.market_map_offline_core import CONTEXT_TF,IntegrationSnapshot,Kernel
from tools.range_rotation_opportunity_reference import RangeIntegrationVariant,build_range_opportunity_frames
from tools.range_rotation_readiness_reference import RangeReadinessVariant,calculate_range_readiness
from tools.range_rotation_reference import RangeOutcome,RangeTrigger,classify_range_rotation,detect_range_rotations
from tools.rsi_state_reference import calculate as calculate_rsi

TIMEFRAMES=("4h","1d")

def _dist(xs): return distribution([float(x) for x in xs if x is not None])
def _per1000(n,rows): return n*1000.0/rows if rows else None

def structural_summary(eps,outs):
    n=len(eps); c=Counter(o.outcome.value for o in outs)
    return {
      "episodes":n,
      "midpoint_or_better_pct":pct(c["MID_REACHED"]+c["OPPOSITE_REACHED"],n),
      "opposite_reached_pct":pct(c["OPPOSITE_REACHED"],n),
      "failed_before_mid_pct":pct(c["FAILED_BEFORE_MID"],n),
      "censored_pct":pct(c["CENSORED"],n),
      "outcome_counts":dict(sorted(c.items()))
    }

def event_counts(samples):
    c=Counter()
    for s in samples:
        e=s.result.events
        c["PREPARING_ENTERED"]+=int(e.preparing_entered)
        c["ARMED_ENTERED"]+=int(e.armed_entered)
        c["CONFIRM"]+=int(e.confirm)
        c["CANCELED"]+=int(e.canceled)
    return c

def quick_cancel(samples,attr,max_bars=3):
    total=0
    for i,s in enumerate(samples):
        if not getattr(s.result.events,attr): continue
        for j in range(i+1,min(len(samples),i+max_bars+1)):
            if samples[j].result.events.confirm: break
            if samples[j].result.events.canceled:
                total+=1; break
    return total

def analyze(tf,datasets,tick):
    data=datasets[tf]; snaps=[]
    Kernel(to_mm_candles(data),to_mm_candles(datasets[CONTEXT_TF[tf]]),
           to_mm_candles(datasets["1d"]),to_mm_candles(datasets["1w"]),tf,tick=tick).run(
           integration_rows=snaps,emit_audit=False)
    locs=build_market_locations(snaps)
    rsi_cache={k:calculate_rsi(v["close"]) for k,v in datasets.items()}
    ctx=build_context_dirs(tf,datasets,rsi_cache)
    bars=[ExecutionResearchBar(float(o),float(h),float(l),float(c),float(v),s.map_dir,loc,ctx[i],
                               s.thesis_invalidated,s.structural_conflict,True)
          for i,(o,h,l,c,v,s,loc) in enumerate(zip(data["open"],data["high"],data["low"],data["close"],data["volume"],snaps,locs))]
    eps=[e for e in detect_range_rotations(snaps,data["high"],data["low"],data["close"])
         if e.trigger==RangeTrigger.EDGE_REJECTION]
    outs=[classify_range_rotation(e,snaps,data["high"],data["low"],data["close"]) for e in eps]
    outcome={o.episode_id:o for o in outs}
    frames=build_range_opportunity_frames(eps,snaps,data["high"],data["low"],data["close"],
                                          variant=RangeIntegrationVariant.ALL_EDGE)
    variants={}
    for variant in RangeReadinessVariant:
        samples=calculate_range_readiness(bars,frames,variant=variant)
        confirmed=[]; not_confirmed=[]; metrics=[]
        for e in eps:
            o=outcome[e.episode_id]; cb=None
            for i in range(e.confirmation_bar,min(len(samples),e.confirmation_bar+3)):
                f=frames[i]
                if f.source_bar!=e.confirmation_bar: continue
                if samples[i].result.events.confirm and samples[i].result.state.direction==e.direction:
                    cb=i; break
            row={"episode":e,"outcome":o,"confirm_bar":cb}
            (confirmed if cb is not None else not_confirmed).append(row)
            if cb is not None:
                dest=e.range_high-e.edge_band if e.direction==1 else e.range_low+e.edge_band
                room=None if e.atr is None or e.atr<=0 else e.direction*(dest-float(data["close"][cb]))/e.atr
                disp=None if e.atr is None or e.atr<=0 else e.direction*(float(data["close"][cb])-e.reference_price)/e.atr
                metrics.append({
                  "latency":cb-e.confirmation_bar,
                  "room":room,"displacement":disp,
                  "before_mid":o.midpoint_bar is None or cb<o.midpoint_bar,
                  "same_mid":o.midpoint_bar is not None and cb==o.midpoint_bar,
                  "after_mid":o.midpoint_bar is not None and cb>o.midpoint_bar,
                  "outcome":o.outcome.value,
                  "direction":"LONG" if e.direction==1 else "SHORT"
                })
        ce=[x["episode"] for x in confirmed]; co=[x["outcome"] for x in confirmed]
        ne=[x["episode"] for x in not_confirmed]; no=[x["outcome"] for x in not_confirmed]
        ev=event_counts(samples)
        variants[variant.value]={
          "confirmed_count":len(confirmed),
          "confirmed_pct":pct(len(confirmed),len(eps)),
          "confirm_latency_bars":_dist([m["latency"] for m in metrics]),
          "confirm_room_to_opposite_atr":_dist([m["room"] for m in metrics]),
          "confirm_displacement_atr":_dist([m["displacement"] for m in metrics]),
          "confirm_before_midpoint_pct":pct(sum(m["before_mid"] for m in metrics),len(metrics)),
          "confirm_same_midpoint_pct":pct(sum(m["same_mid"] for m in metrics),len(metrics)),
          "confirm_after_midpoint_pct":pct(sum(m["after_mid"] for m in metrics),len(metrics)),
          "confirm_direction_counts":dict(sorted(Counter(m["direction"] for m in metrics).items())),
          "failed_before_mid_confirmed":sum(m["outcome"]=="FAILED_BEFORE_MID" for m in metrics),
          "structural_confirmed":structural_summary(ce,co),
          "structural_not_confirmed":structural_summary(ne,no),
          "event_load":{"events":dict(sorted(ev.items())),
                        "events_per_1000":{k:_per1000(v,len(bars)) for k,v in sorted(ev.items())},
                        "quick_prep_cancel_3":quick_cancel(samples,"preparing_entered"),
                        "quick_armed_cancel_3":quick_cancel(samples,"armed_entered")}
        }
    accepted=sum(i+1<len(frames) and frames[i+1].source_bar==e.confirmation_bar and frames[i+1].stage.name=="ACCEPTED"
                 for i,e in [(e.confirmation_bar,e) for e in eps])
    return {"rows":len(bars),"episodes":len(eps),"accepted_next_bar":accepted,
            "accepted_next_bar_pct":pct(accepted,len(eps)),"structural_all":structural_summary(eps,outs),"variants":variants}

def fmt(x): return "n/a" if x is None else f"{x:.2f}"
def markdown(r):
    lines=["# Suite 0.2 — RANGE_ROTATION source-arm readiness","",
           "Pre-registered EARLY_ANY1 vs SELECTIVE_ANY2.","",
           f"- symbol: **{r['metadata']['symbol']}**",f"- code SHA: `{r['metadata']['code_sha']}`","",
           "## Results","",
           "| TF | variant | episodes | accepted +1 % | confirms | confirm % | latency med | before mid % | same mid % | room ATR med | failed confirms | cancel/1000 |",
           "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for tf,x in r["timeframes"].items():
      for name,v in x["variants"].items():
        lines.append(f"| {tf} | {name} | {x['episodes']} | {fmt(x['accepted_next_bar_pct'])} | {v['confirmed_count']} | {fmt(v['confirmed_pct'])} | {fmt(v['confirm_latency_bars']['median'])} | {fmt(v['confirm_before_midpoint_pct'])} | {fmt(v['confirm_same_midpoint_pct'])} | {fmt(v['confirm_room_to_opposite_atr']['median'])} | {v['failed_before_mid_confirmed']} | {fmt(v['event_load']['events_per_1000'].get('CANCELED'))} |")
    lines+=["","## Confirmed structural outcomes","",
            "| TF | variant | confirmed | midpoint+ % | opposite % | fail-before-mid % | censored % |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for tf,x in r["timeframes"].items():
      for name,v in x["variants"].items():
        s=v["structural_confirmed"]
        lines.append(f"| {tf} | {name} | {s['episodes']} | {fmt(s['midpoint_or_better_pct'])} | {fmt(s['opposite_reached_pct'])} | {fmt(s['failed_before_mid_pct'])} | {fmt(s['censored_pct'])} |")
    lines+=["","## Guardrails","",
            "- EDGE_REJECTION detector and +1 ACCEPTED lifecycle are unchanged.",
            "- EARLY_ANY1 and SELECTIVE_ANY2 differ only in source ignition threshold/state.",
            "- ACCEPTED confirms only a setup already ARMED at the source.",
            "- HTF RSI is not a readiness veto.",
            "- Breakout/reacceleration Opportunity v2 and frozen 0.1 remain unchanged.",
            "- Structural outcomes are not profitability claims.",""]
    return "\n".join(lines)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--data-root",type=Path,required=True); ap.add_argument("--symbol",default="BTCUSDT")
    ap.add_argument("--canonical-manifest",type=Path,required=True); ap.add_argument("--output-json",type=Path,required=True); ap.add_argument("--output-md",type=Path,required=True)
    ap.add_argument("--code-sha",default="unknown"); ap.add_argument("--tick-size",type=float,default=.01); a=ap.parse_args()
    can=json.loads(a.canonical_manifest.read_text()); exp={d["timeframe"]:d for d in can["datasets"]}; symbol=a.symbol.upper(); market=can.get("market","spot")
    ds={}; meta={}
    for tf in ("4h","1d","1w"):
      p=a.data_root/market/symbol/"consolidated"/f"{symbol}_{tf}.parquet"; dig=sha256_file(p)
      if dig!=exp[tf]["dataset_sha256"]: raise SystemExit(f"{tf} SHA mismatch")
      d=load_dataset(p)
      if len(d["close"])!=exp[tf]["candles"]: raise SystemExit(f"{tf} rows mismatch")
      ds[tf]=d; meta[tf]={"rows":len(d["close"]),"sha256":dig}
    report={"metadata":{"symbol":symbol,"code_sha":a.code_sha,"datasets":meta},
            "timeframes":{tf:analyze(tf,ds,a.tick_size) for tf in TIMEFRAMES}}
    a.output_json.parent.mkdir(parents=True,exist_ok=True); a.output_md.parent.mkdir(parents=True,exist_ok=True)
    a.output_json.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n"); md=markdown(report); a.output_md.write_text(md+"\n"); print(md); return 0
if __name__=="__main__": raise SystemExit(main())
