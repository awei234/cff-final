"""Bounded, auditable v3 research matrix pipeline."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib, json, os, re, subprocess, sys
from pathlib import Path
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from .paper_pdf import derive_paper_pdf
from .providers import resolve_provider

MATRIX_SCHEMA_VERSION="3.0"
REQUIRED_TOPIC_ARTIFACTS=("run_manifest.json","prompt.txt","tool_trace.jsonl","rail_events.jsonl","research_materials.json","plan.json","experiment_config.json","experiment_results.json","results.json","paper.tex","paper.pdf","resource.json","execution_report.json","human_interventions.jsonl","provenance.json","verification_report.json")
class ResearchMatrixError(RuntimeError):
    def __init__(self,code,message): super().__init__(message); self.code=code
def now(): return datetime.now(timezone.utc).isoformat()
def digest(b): return hashlib.sha256(b).hexdigest().upper()
def file_digest(p): return digest(p.read_bytes())
def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def norm_title(v): return re.sub(r"[^a-z0-9]+"," ",v.lower()).strip()
def write_bytes(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists(): raise ResearchMatrixError("output_exists",f"refusing to overwrite existing artifact: {p}")
    p.write_bytes(v)
def write_text(p,v): write_bytes(p,v.encode("utf-8"))
def write_json(p,v): write_text(p,json.dumps(v,ensure_ascii=False,indent=2)+"\n")
def write_jsonl(p,vs): write_text(p,"".join(json.dumps(v,ensure_ascii=False)+"\n" for v in vs))
def redact(v,secret=""):
    r=str(v).replace(secret,"[REDACTED]") if secret else str(v)
    for n in ("DEEPSEEK_API_KEY","OPENAI_COMPAT_API_KEY","ZHIPUAI_API_KEY","DASHSCOPE_API_KEY"):
        if os.environ.get(n): r=r.replace(os.environ[n],"[REDACTED]")
    return r

def http_json(url,timeout,cache):
    if cache and cache.is_file():
        b=cache.read_bytes(); return json.loads(b.decode()),digest(b),True
    with urlopen(Request(url,headers={"User-Agent":"JiuwenSwarm-v3-research-matrix/1.0"}),timeout=timeout) as r: b=r.read()
    if cache: cache.parent.mkdir(parents=True,exist_ok=True); cache.write_bytes(b)
    return json.loads(b.decode()),digest(b),False
def http_text(url,timeout,cache):
    if cache and cache.is_file():
        b=cache.read_bytes(); return b.decode("utf-8","replace"),digest(b),True
    with urlopen(Request(url,headers={"User-Agent":"JiuwenSwarm-v3-research-matrix/1.0"}),timeout=timeout) as r: b=r.read()
    if cache: cache.parent.mkdir(parents=True,exist_ok=True); cache.write_bytes(b)
    return b.decode("utf-8","replace"),digest(b),False
def abstract_openalex(w):
    inv=w.get("abstract_inverted_index")
    if not isinstance(inv,dict): return ""
    out=[]
    for word,poss in inv.items():
        for pos in poss if isinstance(poss,list) else []:
            if isinstance(pos,int): out.append((pos,word))
    return " ".join(x[1] for x in sorted(out))
def source(provider,sid,title,authors,published,url,doi,abstract,response_hash):
    base={"source_id":sid,"provider":provider,"title":title,"authors":authors,"published_at":published,"url":url,"doi":doi,"abstract":abstract}
    return {**base,"retrieved_at_utc":now(),"content_sha256":digest(canon(base)),"status":"retrieved","response_sha256":response_hash}
def parse_openalex(v,rh):
    out=[]
    for w in v.get("results",[]) if isinstance(v,dict) else []:
        if not isinstance(w,dict): continue
        title=str(w.get("title") or "").strip(); wid=str(w.get("id") or "").rstrip("/").split("/")[-1]
        if not title or not wid: continue
        authors=[]
        for a in w.get("authorships",[]) or []:
            x=a.get("author") if isinstance(a,dict) else None
            if isinstance(x,dict) and x.get("display_name"): authors.append(str(x["display_name"]))
        doi=w.get("doi"); doi=str(doi).replace("https://doi.org/","") if doi else None
        loc=w.get("primary_location") if isinstance(w.get("primary_location"),dict) else {}
        out.append(source("openalex","openalex:"+wid,title,authors,str(w.get("publication_year")) if w.get("publication_year") else None,str(loc.get("landing_page_url") or w.get("id") or ""),doi,abstract_openalex(w),rh))
    return out
def parse_arxiv(text,rh):
    out=[]
    try: root=ET.fromstring(text)
    except ET.ParseError: return out
    ns={"a":"http://www.w3.org/2005/Atom"}
    for e in root.findall("a:entry",ns):
        title=" ".join((e.findtext("a:title",default="",namespaces=ns)).split()); ident=e.findtext("a:id",default="",namespaces=ns).strip()
        if not title or not ident: continue
        aid=ident.rstrip("/").split("/")[-1]; authors=[a.findtext("a:name",default="",namespaces=ns).strip() for a in e.findall("a:author",ns)]
        doi=None
        for l in e.findall("a:link",ns):
            if l.attrib.get("title")=="doi": doi=l.attrib.get("href")
        out.append(source("arxiv","arxiv:"+aid,title,[a for a in authors if a],e.findtext("a:published",default=None,namespaces=ns),ident,doi," ".join(e.findtext("a:summary",default="",namespaces=ns).split()),rh))
    return out
def parse_crossref(v,rh):
    out=[]; m=v.get("message",{}) if isinstance(v,dict) else {}
    for x in m.get("items",[]) if isinstance(m,dict) else []:
        if not isinstance(x,dict): continue
        ts=x.get("title") or []; title=str(ts[0]).strip() if ts else ""; doi=str(x.get("DOI") or "").strip() or None
        if not title or not doi: continue
        authors=[]
        for a in x.get("author",[]) or []:
            if isinstance(a,dict):
                n=" ".join(filter(None,[a.get("given"),a.get("family")])).strip()
                if n: authors.append(n)
        dp=x.get("published",{}).get("date-parts",[[]]); year=str(dp[0][0]) if dp and dp[0] else None
        abstract=re.sub(r"<[^>]+>"," ",str(x.get("abstract") or ""))
        out.append(source("crossref","doi:"+doi.lower(),title,authors,year,str(x.get("URL") or "https://doi.org/"+doi),doi," ".join(abstract.split()),rh))
    return out
@dataclass(frozen=True)
class RetrievalResult:
    document:dict[str,Any]; records:list[dict[str,Any]]; events:list[dict[str,Any]]
def retrieve_materials(topic,cache_root,timeout=20):
    tid=str(topic["topic_id"]); candidates=[]; events=[]; errors=[]
    for kw in list(topic.get("keywords",[]))[:3]:
        q=quote_plus(str(kw)); queries=[("openalex",f"https://api.openalex.org/works?search={q}&per-page=10"),("arxiv",f"https://export.arxiv.org/api/query?search_query=all:{q}&start=0&max_results=10"),("crossref",f"https://api.crossref.org/works?query={q}&rows=10&select=DOI,title,author,published,URL,abstract")]
        for provider,url in queries:
            cp=cache_root/tid/(hashlib.sha256(url.encode()).hexdigest()+(".xml" if provider=="arxiv" else ".json"))
            try:
                if provider=="arxiv": raw,rh,cached=http_text(url,timeout,cp); parsed=parse_arxiv(raw,rh)
                else: val,rh,cached=http_json(url,timeout,cp); parsed=parse_openalex(val,rh) if provider=="openalex" else parse_crossref(val,rh)
                candidates.extend(parsed); events.append({"event":"retrieval","provider":provider,"keyword":kw,"cached":cached,"candidate_count":len(parsed),"status":"ok","timestamp_utc":now()})
            except (HTTPError,URLError,TimeoutError,OSError,ValueError,ET.ParseError) as exc:
                errors.append({"provider":provider,"keyword":str(kw),"error":redact(str(exc))[:500]}); events.append({"event":"retrieval","provider":provider,"keyword":kw,"status":"failed","error_type":type(exc).__name__,"timestamp_utc":now()})
    seen=set(); kept=[]
    for x in candidates:
        key=str(x.get("doi") or "").lower().strip() or str(x.get("source_id") or "").lower() or norm_title(str(x.get("title") or ""))
        if key and key not in seen: seen.add(key); kept.append(x)
    kept.sort(key=lambda x:(not bool(x.get("abstract")),str(x.get("title","")).lower(),str(x.get("source_id","")))); kept=kept[:10]
    status="retrieved" if kept and not errors else ("partial_retrieval" if kept else "retrieval_failed")
    doc={"schema_version":MATRIX_SCHEMA_VERSION,"topic_id":tid,"status":status,"sources":kept,"deduplication":{"candidate_count":len(candidates),"kept_count":len(kept),"removed_duplicates":max(0,len(candidates)-len(seen))},"retrieval_errors":errors,"retrieved_at_utc":now(),"policy":"metadata_and_abstract_only; no unlicensed full text is packaged"}
    return RetrievalResult(doc,kept,events)

BENCH=r'''import hashlib,json,sys
from random import Random
topic=sys.argv[1]; seed=int(sys.argv[2]); rng=Random(seed)
claims=[{"id":"C1","evidence":"input_hash"},{"id":"C2","evidence":"rail_decision"},{"id":"C3","evidence":None}]
p={"topic_id":topic,"seed":seed,"fixed_input":["alpha","beta","gamma"]}; ih=hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest().upper()
baseline=[{"claim_id":c["id"],"decision":"accepted","evidence_ref":c["evidence"]} for c in claims]
full=[{"claim_id":c["id"],"decision":"accepted" if c["evidence"] else "blocked_missing_evidence","evidence_ref":c["evidence"]} for c in claims]
r={"benchmark_kind":"pipeline_process_evidence_not_topic_scientific_result","topic_id":topic,"seed":seed,"input_hash":ih,"arms":{"baseline":{"claims_total":3,"accepted":3,"blocked":0,"decisions":baseline},"full_rail":{"claims_total":3,"accepted":2,"blocked":1,"decisions":full}},"reproducibility_token":hashlib.sha256(json.dumps(full,sort_keys=True).encode()).hexdigest().upper(),"random_probe":rng.random()}
print(json.dumps(r,ensure_ascii=False,sort_keys=True))'''
def run_local_benchmark(topic_id,run_dir,seed):
    cfg={"schema_version":MATRIX_SCHEMA_VERSION,"benchmark_id":"ucr-evidence-process-benchmark-v1","topic_id":topic_id,"seed":seed,"command":[sys.executable,"-c","<embedded deterministic benchmark>",topic_id,str(seed)],"working_directory":str(run_dir),"baseline_arm":"no-rail","evidence_arm":"full-rail","interpretation":"These are process/evidence-control measurements, not scientific conclusions about the topic."}
    write_json(run_dir/"experiment_config.json",cfg); p=subprocess.run([sys.executable,"-c",BENCH,topic_id,str(seed)],cwd=run_dir,text=True,capture_output=True,check=False,timeout=60)
    out=p.stdout or ""; err=p.stderr or ""; write_text(run_dir/"experiment_stdout.txt",out); write_text(run_dir/"experiment_stderr.txt",err)
    events=[{"event":"local_experiment","command":cfg["command"],"returncode":p.returncode,"stdout_sha256":digest(out.encode()),"stderr_sha256":digest(err.encode()),"timestamp_utc":now()}]
    try: result=json.loads(out) if p.returncode==0 else {"status":"failed","error":"benchmark command failed"}
    except json.JSONDecodeError: result={"status":"failed","error":"benchmark stdout was not JSON"}
    result["status"]="completed" if "arms" in result else "failed"; result["benchmark_kind"]="pipeline_process_evidence_not_topic_scientific_result"; result["stdout_sha256"]=digest(out.encode()); result["stderr_sha256"]=digest(err.encode())
    return cfg,result,events
PLAN=("research_question","hypotheses","variables","experiment_plan","success_criteria","expected_evidence","human_confirmation_points")
REVIEW=("evidence_supported_claims","unsupported_claims","citation_coverage","allow_paper","human_intervention_required")
REPORT=("abstract","methods","experiment_setup","results","limitations","conclusion","citation_mapping","unsupported_claims")
def validate_stage(v,required,stage):
    if not isinstance(v,dict): raise ResearchMatrixError("provider_invalid_json",f"{stage} output must be a JSON object")
    miss=[x for x in required if x not in v or v[x] in (None,"")]
    if miss: raise ResearchMatrixError("provider_schema_invalid",f"{stage} output missing fields: {', '.join(miss)}")
    return v
def parse_provider(text,stage):
    raw=text.strip()
    if raw.startswith(chr(96)*3):
        raw=re.sub(r"^"+chr(96)*3+r"(?:json)?\s*","",raw,flags=re.I)
        raw=re.sub(r"\s*"+chr(96)*3+"$","",raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Providers sometimes add a short preface around an otherwise valid JSON object.
        start=raw.find("{")
        if start >= 0:
            depth=0; quoted=False; escaped=False
            for i in range(start,len(raw)):
                ch=raw[i]
                if quoted:
                    if escaped: escaped=False
                    elif ch=="\\": escaped=True
                    elif ch=='"': quoted=False
                    continue
                if ch=='"': quoted=True
                elif ch=="{": depth+=1
                elif ch=="}":
                    depth-=1
                    if depth==0:
                        try: return json.loads(raw[start:i+1])
                        except json.JSONDecodeError: break
        raise ResearchMatrixError("provider_invalid_json",f"{stage} returned invalid JSON")

def compact_materials(materials):
    if not isinstance(materials,dict): return materials
    out=dict(materials)
    rows=[]
    for source in list(materials.get("sources",[]))[:6]:
        if not isinstance(source,dict): continue
        item=dict(source); item["abstract"]=str(item.get("abstract") or "")[:600]; item.pop("response_sha256",None); rows.append(item)
    out["sources"]=rows
    out["retrieval_errors"]=list(materials.get("retrieval_errors",[]))[:5]
    return out
class DeepSeekClient:
    def __init__(self,config,environ):
        r=resolve_provider(provider="deepseek",config_path=config,environ=environ); self.base=r.api_base; self.model=r.model_id; self.key=r.load_api_key(environ); self.calls=0
    def call(self,stage,prompt,limit):
        if self.calls>=limit: raise ResearchMatrixError("call_budget_exceeded",f"provider call budget exceeded before {stage}")
        payload={"model":self.model,"messages":[{"role":"system","content":"Return exactly one JSON object, no Markdown fences. Do not invent retrieval or experiment results. Distinguish process benchmark evidence from topic scientific evidence. Missing evidence must remain missing. Keep every string under 500 characters, each list under 6 items, and the complete JSON concise so it is never truncated."},{"role":"user","content":prompt}],"temperature":0.1,"max_tokens":4096,"thinking":{"type":"disabled"},"response_format":{"type":"json_object"}}
        req=Request(self.base.rstrip("/")+"/chat/completions",data=json.dumps(payload,ensure_ascii=False).encode(),headers={"Authorization":"Bearer "+self.key,"Content-Type":"application/json"},method="POST"); self.calls+=1; started=datetime.now(timezone.utc)
        try:
            with urlopen(req,timeout=180) as resp: val=json.loads(resp.read().decode())
            content=val["choices"][0]["message"]["content"]
            return parse_provider(content,stage),{"event":"provider_call","stage":stage,"call_index":self.calls,"model":self.model,"status":"ok","duration_seconds":(datetime.now(timezone.utc)-started).total_seconds(),"timestamp_utc":now()}
        except (HTTPError,URLError,TimeoutError,OSError,KeyError,IndexError,TypeError,ValueError,json.JSONDecodeError,ResearchMatrixError) as exc:
            raise ResearchMatrixError("provider_call_failed",redact(f"{stage} failed: {exc}",self.key)[:1000]) from exc
class MockClient:
    def __init__(self): self.calls=0
    def call(self,stage,prompt,limit):
        self.calls+=1
        if stage=="plan": v={"research_question":"Can an audited process distinguish supported from unsupported claims?","hypotheses":["Explicit evidence gates improve auditability."],"variables":{"independent":"evidence gate","dependent":"audit decision"},"experiment_plan":["Run fixed deterministic benchmark with baseline and full-rail arms."],"success_criteria":["Every accepted claim has a saved evidence reference."],"expected_evidence":["benchmark output and source IDs"],"human_confirmation_points":["research_question","source_suitability","experiment_validity","conclusion_scope","final_submission"]}
        elif stage=="review": v={"evidence_supported_claims":["The benchmark recorded fixed inputs and rail decisions."],"unsupported_claims":["The benchmark proves a scientific improvement for the topic."],"citation_coverage":{"covered":1,"total":1},"allow_paper":True,"human_intervention_required":True}
        else: v={"abstract":"This run demonstrates an auditable process benchmark.","methods":"A fixed local benchmark was executed with baseline and full-rail arms.","experiment_setup":"Seed 42 and fixed inputs were used.","results":"The evidence arm blocked one claim without evidence.","limitations":"The result is not scientific evidence for the topic.","conclusion":"The implementation preserves evidence boundaries.","citation_mapping":[],"unsupported_claims":["Any topic-level scientific improvement."]}
        return v,{"event":"provider_call","stage":stage,"call_index":self.calls,"model":"mock-v3","status":"ok","timestamp_utc":now()}
def prompt_base(topic,materials,experiment): return json.dumps({"topic":topic,"research_materials":compact_materials(materials),"experiment_config":experiment,"boundary":"Do not claim that the process benchmark proves a domain scientific result. Cite only source_id values in research_materials. Missing evidence must remain missing."},ensure_ascii=False,indent=2)
def paper_tex(topic,plan,review,report,status):
    def c(v):
        if isinstance(v,list): return "; ".join(c(x) for x in v)
        if isinstance(v,dict): return "; ".join(f"{c(k)}: {c(vv)}" for k,vv in v.items())
        return str(v).replace("%","\\%").replace("&","\\&").replace("_","\\_").replace("#","\\#")
    return "\n".join(["\\documentclass{article}","\\begin{document}",f"\\title{{JiuwenSwarm v3: {c(topic['topic_name'])}}}","\\maketitle",f"\\section*{{Status}} {c(status)}.","\\section*{Abstract}",c(report.get("abstract","No report was generated; see execution report.")),"\\section*{Research question and plan}",c(plan.get("research_question","Unavailable")),"\\subsection*{Hypotheses}",c(plan.get("hypotheses",[])),"\\section*{Methods}",c(report.get("methods","No methods were approved.")),"\\section*{Experiment setup}",c(report.get("experiment_setup","The local benchmark did not complete.")),"\\section*{Results}",c(report.get("results","No supported result was generated.")),"\\section*{Evidence review}",c(review.get("evidence_supported_claims",[])),"\\subsection*{Unsupported claims}",c(report.get("unsupported_claims",[]) or review.get("unsupported_claims",[])),"\\section*{Citations}",c(report.get("citation_mapping",[])) if report.get("citation_mapping") else "No citation mapping was supplied.","\\section*{Limitations}",c(report.get("limitations","This is an auditable semi-pipeline demonstration, not a fully autonomous scientific system.")),"\\section*{Conclusion}",c(report.get("conclusion","No conclusion was approved.")),"\\end{document}",""])
def verify_matrix_run(run_dir):
    checks=[]; errors=[]
    def check(n,ok,d): checks.append({"name":n,"passed":bool(ok),"detail":d}); errors.extend([] if ok else [n+": "+d])
    for n in REQUIRED_TOPIC_ARTIFACTS:
        if n == "verification_report.json" and not (run_dir/n).exists():
            continue
        check("required:"+n,(run_dir/n).is_file(),"required artifact exists")
    docs={}
    for n in ("run_manifest.json","research_materials.json","plan.json","experiment_config.json","experiment_results.json","results.json","resource.json","execution_report.json","provenance.json"):
        p=run_dir/n
        if p.is_file():
            try: docs[n]=json.loads(p.read_text(encoding="utf-8")); check("json:"+n,isinstance(docs[n],dict),"valid JSON object")
            except Exception as exc: check("json:"+n,False,redact(exc))
    m=docs.get("run_manifest.json",{}); materials=docs.get("research_materials.json",{}); sources=materials.get("sources",[]) if isinstance(materials,dict) else []; ids={x.get("source_id") for x in sources if isinstance(x,dict)}; result=docs.get("results.json",{}); report=result.get("report",{}) if isinstance(result,dict) else {}; cids=[x.get("source_id") for x in report.get("citation_mapping",[]) if isinstance(x,dict)] if isinstance(report,dict) else []
    check("topic_id",bool(m.get("topic_id")),"topic_id is present"); check("citations_map_to_sources",all(x in ids for x in cids),"citation source IDs exist in research_materials"); check("process_benchmark_label","process_evidence_not_topic_scientific_result" in json.dumps(docs.get("experiment_results.json",{}),ensure_ascii=False),"benchmark is explicitly bounded")
    prov=docs.get("provenance.json",{}); hashes=prov.get("artifact_hashes",{}) if isinstance(prov,dict) else {}
    for n,expected in hashes.items(): check("hash:"+n,(run_dir/n).is_file() and file_digest(run_dir/n)==expected,"artifact hash matches provenance")
    check("no_replacement_character",not any(chr(0xfffd) in p.read_text(encoding="utf-8",errors="replace") for p in run_dir.glob("*.json") if p.is_file()),"JSON has no replacement character")
    return {"schema_version":MATRIX_SCHEMA_VERSION,"valid":not errors,"topic_id":m.get("topic_id"),"execution_status":m.get("status","unknown"),"checks":checks,"errors":errors,"verified_at_utc":now(),"run_manifest_sha256":file_digest(run_dir/"run_manifest.json") if (run_dir/"run_manifest.json").is_file() else None,"provenance_sha256":file_digest(run_dir/"provenance.json") if (run_dir/"provenance.json").is_file() else None}
def failure_artifacts(run_dir,status,reason,calls):
    vals={"plan.json":{"status":"unavailable","reason":reason},"results.json":{"status":status,"review":{"allow_paper":False,"unsupported_claims":[reason]},"report":{"unsupported_claims":[reason]}},"resource.json":{"schema_version":MATRIX_SCHEMA_VERSION,"measurement_status":"not_applicable","provider_calls":calls},"execution_report.json":{"status":status,"failure_reason":reason,"provider_calls":calls},"experiment_results.json":{"status":"not_run","reason":"retrieval or provider precondition failed","benchmark_kind":"pipeline_process_evidence_not_topic_scientific_result"}}
    for n,v in vals.items():
        if not (run_dir/n).exists(): write_json(run_dir/n,v)
def mock_materials(topic):
    tid=str(topic["topic_id"])
    rows=[]
    for i in range(2):
        base={"source_id":f"mock:source-{tid}-{i+1}","provider":"offline-fixture","title":f"Auditable agent process source {i+1} for {tid}","authors":["v3 fixture"],"published_at":"2026","url":"https://example.invalid/v3-fixture/"+tid+"/"+str(i+1),"doi":None,"abstract":"Offline fixture metadata used only to validate citation and evidence contracts."}
        rows.append({**base,"retrieved_at_utc":now(),"content_sha256":digest(canon(base)),"status":"retrieved"})
    doc={"schema_version":MATRIX_SCHEMA_VERSION,"topic_id":tid,"status":"retrieved","sources":rows,"deduplication":{"candidate_count":2,"kept_count":2,"removed_duplicates":0},"retrieval_errors":[],"retrieved_at_utc":now(),"policy":"offline fixture metadata; not public retrieval"}
    return RetrievalResult(doc,rows,[{"event":"retrieval","provider":"offline-fixture","status":"ok","candidate_count":2,"timestamp_utc":now()}])

def run_topic(topic,output_root,cache_root,provider_config,allow_retrieval,max_calls,seed,mock=False):
    tid=str(topic["topic_id"]); run_dir=output_root/tid
    if run_dir.exists(): raise ResearchMatrixError("output_exists",f"topic output already exists: {run_dir}")
    run_dir.mkdir(parents=True); manifest={"schema_version":MATRIX_SCHEMA_VERSION,"topic_id":tid,"topic_name":topic["topic_name"],"provider":"mock-v3" if mock else "deepseek","model":"mock-v3" if mock else None,"seed":seed,"status":"running","started_at_utc":now(),"max_model_calls":max_calls,"model_api_calls":0,"human_review_status":"pending","required_artifacts":list(REQUIRED_TOPIC_ARTIFACTS)}; write_json(run_dir/"run_manifest.json",manifest)
    events=[{"event":"run_started","topic_id":tid,"timestamp_utc":now()}]; rails=[{"event":"rail_initialized","policy":"block_claims_without_evidence","timestamp_utc":now()}]; prompts=[]; calls=0; retrieval=mock_materials(topic) if mock else (retrieve_materials(topic,cache_root) if allow_retrieval else RetrievalResult({"schema_version":MATRIX_SCHEMA_VERSION,"topic_id":tid,"status":"retrieval_failed","sources":[],"retrieval_errors":[{"error":"public retrieval flag was not enabled"}],"deduplication":{"candidate_count":0,"kept_count":0,"removed_duplicates":0}},[],[]))
    write_json(run_dir/"research_materials.json",retrieval.document); events.extend(retrieval.events); cfg={"status":"not_started"}; exp={"status":"not_run","benchmark_kind":"pipeline_process_evidence_not_topic_scientific_result"}; plan={"status":"not_started"}; review={"status":"not_started"}; report={"status":"not_started"}; status="failed"; reason=None; client=MockClient() if mock else None
    try:
        if retrieval.document.get("status")=="retrieval_failed": raise ResearchMatrixError("retrieval_failed","no public research materials were retrieved")
        cfg,exp,e=run_local_benchmark(tid,run_dir,seed); events.extend(e); base=prompt_base(topic,retrieval.document,cfg)
        p1="Stage 1 (research plan). Return JSON fields: "+", ".join(PLAN)+".\n"+base; prompts.append(p1); client=client or DeepSeekClient(provider_config,os.environ); manifest["model"]=getattr(client,"model","mock-v3"); plan,e=client.call("plan",p1,max_calls); calls=client.calls; plan=validate_stage(plan,PLAN,"plan"); events.append(e)
        p2="Stage 2 (experiment evidence review). Return JSON fields: "+", ".join(REVIEW)+". Never change raw experiment results.\n"+json.dumps({"plan":plan,"experiment_results":exp,"research_materials":compact_materials(retrieval.document),"boundary":"The benchmark is process evidence only."},ensure_ascii=False,indent=2); prompts.append(p2); review,e=client.call("review",p2,max_calls); calls=client.calls; review=validate_stage(review,REVIEW,"review"); events.append(e)
        p3="Stage 3 (research report). Return JSON fields: "+", ".join(REPORT)+". Include citation_mapping entries with source_id only from research_materials. Keep unsupported claims explicit.\n"+json.dumps({"plan":plan,"review":review,"experiment_results":exp,"research_materials":compact_materials(retrieval.document),"human_review":"not yet approved; mark pending"},ensure_ascii=False,indent=2); prompts.append(p3); report,e=client.call("report",p3,max_calls); calls=client.calls; report=validate_stage(report,REPORT,"report"); events.append(e)
        valid_source_ids={s.get("source_id") for s in retrieval.records}
        invalid_citations=[x for x in report.get("citation_mapping",[]) if isinstance(x,dict) and x.get("source_id") not in valid_source_ids]
        if invalid_citations:
            report["citation_mapping"]=[x for x in report.get("citation_mapping",[]) if isinstance(x,dict) and x.get("source_id") in valid_source_ids]
            report["unsupported_claims"]=list(report.get("unsupported_claims",[]))+["Provider citation mapping contained source IDs not present in the saved retrieval materials; those mappings were blocked and require human review."]
            rails.append({"event":"citation_mapping_blocked","blocked_count":len(invalid_citations),"policy":"only_saved_source_ids_are_allowed","timestamp_utc":now()})
        status="completed_pending_human_review"; rails.append({"event":"claim_reviewed","blocked_unsupported_claims":len(review.get("unsupported_claims",[])),"timestamp_utc":now()})
    except ResearchMatrixError as exc:
        calls=max(calls,int(getattr(client,"calls",0)))
        reason=redact(str(exc)); failure_artifacts(run_dir,status,reason,calls)
    finally:
        if not (run_dir/"experiment_config.json").exists(): write_json(run_dir/"experiment_config.json",cfg)
        if not (run_dir/"experiment_results.json").exists(): write_json(run_dir/"experiment_results.json",exp)
        if not (run_dir/"plan.json").exists(): write_json(run_dir/"plan.json",plan)
        if not (run_dir/"results.json").exists():
            write_json(run_dir/"results.json",{"status":status,"review":review,"report":report})
        tex=paper_tex(topic,plan,review,report,status)
        write_text(run_dir/"paper.tex",tex)
        write_bytes(run_dir/"paper.pdf",derive_paper_pdf(tex))
        if not (run_dir/"resource.json").exists(): write_json(run_dir/"resource.json",{"schema_version":MATRIX_SCHEMA_VERSION,"measurement_status":"mock_provider" if mock else "live_provider","provider_calls":calls})
        if not (run_dir/"execution_report.json").exists(): write_json(run_dir/"execution_report.json",{"status":status,"failure_reason":reason,"provider_calls":calls,"retrieval_status":retrieval.document.get("status")})
        write_jsonl(run_dir/"human_interventions.jsonl",[{"event":"pending_human_review","topic_id":tid,"actor":"human","decision":"pending","reason":"Final research question, source suitability, experiment validity, conclusion scope, and submission must be confirmed by a human.","timestamp_utc":now()}]); write_jsonl(run_dir/"rail_events.jsonl",rails); write_text(run_dir/"prompt.txt","\n\n===== STAGE BREAK =====\n\n".join(prompts) if prompts else "No provider prompt was executed because the precondition failed: "+(reason or "unknown")); events.append({"event":"run_finished","status":status,"provider_calls":calls,"timestamp_utc":now()})
        manifest.update({"status":status,"model_api_calls":calls,"retrieval_status":retrieval.document.get("status"),"retrieved_source_count":len(retrieval.records),"finished_at_utc":now(),"failure_reason":reason}); (run_dir/"run_manifest.json").unlink(); write_json(run_dir/"run_manifest.json",manifest); write_jsonl(run_dir/"tool_trace.jsonl",events)
        hashes={n:file_digest(run_dir/n) for n in REQUIRED_TOPIC_ARTIFACTS if n not in ("provenance.json","verification_report.json") and (run_dir/n).is_file()}; write_json(run_dir/"provenance.json",{"schema_version":MATRIX_SCHEMA_VERSION,"topic_id":tid,"artifact_hashes":hashes,"research_source_hashes":{s.get("source_id"):s.get("content_sha256") for s in retrieval.records},"provider":{"name":manifest["provider"],"model":manifest.get("model"),"model_api_calls":calls},"created_at_utc":now()}); write_json(run_dir/"verification_report.json",verify_matrix_run(run_dir))
    return {"topic_id":tid,"status":status,"model_api_calls":calls,"retrieved_source_count":len(retrieval.records),"verification_valid":json.loads((run_dir/"verification_report.json").read_text()).get("valid") is True,"path":str(run_dir),"failure_reason":reason}
def load_matrix_config(path):
    try: v=json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError,json.JSONDecodeError) as exc: raise ResearchMatrixError("matrix_config_invalid",f"unable to read matrix config: {exc}") from exc
    if not isinstance(v,dict) or v.get("schema_version")!=MATRIX_SCHEMA_VERSION or not isinstance(v.get("topics"),list): raise ResearchMatrixError("matrix_config_invalid","matrix config has an unsupported schema")
    ids=[x.get("topic_id") for x in v["topics"] if isinstance(x,dict)]
    if ids != ["context-engineering","memory-engine","self-evolution"]: raise ResearchMatrixError("matrix_config_invalid","matrix config must contain exactly the three fixed topics")
    return v
def run_matrix(config_path,provider_config,output_root,cache_root,provider,confirm_live,allow_demo,allow_retrieval,max_calls_per_topic,max_total_calls,seed,mock=False):
    if provider!="deepseek" and not mock: raise ResearchMatrixError("provider_not_allowed","v3 matrix live mode only permits provider=deepseek")
    if not confirm_live and not mock: raise ResearchMatrixError("live_confirmation_required","--confirm-live is required")
    if not allow_demo and not mock: raise ResearchMatrixError("demo_permission_required","--allow-research-matrix-demo is required")
    if not allow_retrieval and not mock: raise ResearchMatrixError("retrieval_permission_required","--allow-public-retrieval is required")
    if not 1<=max_calls_per_topic<=3: raise ResearchMatrixError("call_limit_invalid","--max-calls-per-topic must be between 1 and 3")
    if not 1<=max_total_calls<=9: raise ResearchMatrixError("call_limit_invalid","--max-total-calls must be between 1 and 9")
    matrix=load_matrix_config(config_path)
    if not mock:
        try:
            resolve_provider(provider="deepseek",config_path=provider_config,environ=os.environ).load_api_key(os.environ)
        except Exception as exc:
            raise ResearchMatrixError("api_key_missing", redact(str(exc))) from exc
    if output_root.exists() and any(output_root.iterdir()): raise ResearchMatrixError("output_exists",f"refusing to use non-empty output root: {output_root}")
    output_root.mkdir(parents=True,exist_ok=True); cache_root.mkdir(parents=True,exist_ok=True); reports=[]; total=0
    for topic in matrix["topics"]:
        if total+max_calls_per_topic>max_total_calls: raise ResearchMatrixError("call_limit_invalid","topic budgets exceed global call limit")
        r=run_topic(topic,output_root,cache_root,provider_config,allow_retrieval,max_calls_per_topic,seed,mock); reports.append(r); total+=int(r["model_api_calls"])
    good=sum(1 for r in reports if r["status"]=="completed_pending_human_review"); overall="completed_pending_human_review" if good==len(reports) else ("partial_failed" if good else "failed")
    summary={"schema_version":MATRIX_SCHEMA_VERSION,"matrix_id":matrix["matrix_id"],"status":overall,"provider":"mock-v3" if mock else provider,"max_calls_per_topic":max_calls_per_topic,"max_total_calls":max_total_calls,"total_model_api_calls":total,"human_review_status":"pending","topics":reports,"prepared_not_uploaded":True,"created_at_utc":now()}; write_json(output_root/"matrix_execution_report.json",summary); write_text(output_root/"README.md","# JiuwenSwarm v3 research matrix\n\nThree independent topic runs. Human review is pending. The local benchmark measures process evidence, not a topic scientific result.\n"); return summary
__all__=["ResearchMatrixError","load_matrix_config","retrieve_materials","run_local_benchmark","verify_matrix_run","run_matrix"]
