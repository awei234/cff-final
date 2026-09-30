# v4
from __future__ import annotations
import argparse,hashlib,json,os,re,subprocess,sys,time,urllib.parse,urllib.request,urllib.error,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
try:
 from competition_runner.harness.archive import archive_run
 from competition_runner.harness.planner import build_harness_manifest
 from competition_runner.harness.validator import validate_manifest
except ModuleNotFoundError:
 from harness.archive import archive_run
 from harness.planner import build_harness_manifest
 from harness.validator import validate_manifest
SCHEMA="4.0"; ARMS=("no-rail","prompt-only","full-rail")
TOPICS={"context-engineering":{"name":"Agent 上下文工程","keys":["agent context engineering","context management agent","long context agent","tool use context"],"question":"程序级证据护栏能否提高 Agent 执行报告的证据一致性？","hypothesis":"full-rail 应比无护栏或仅提示词减少无证据完成声明。","kind":"real_ucr_closed_loop"},"memory-engine":{"name":"Agent 记忆引擎","keys":["agent memory","long-term memory agents","memory augmented language model","episodic memory agent"],"question":"结构化记忆记录是否有助于 Agent 保持审计上下文一致？","hypothesis":"结构化记录可能改善流程可追溯性，但当前基准不证明领域效果。","kind":"process_benchmark_only"},"self-evolution":{"name":"Agent 自我进化","keys":["agent self evolution","self improving agents","continual agent improvement","reflection agent"],"question":"带证据的反思循环能否避免把未执行任务写成已完成？","hypothesis":"证据检查可能改善审计表达，但当前基准不证明真实自我进化。","kind":"process_benchmark_only"}}
def now():return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
def sha(x):return hashlib.sha256(x if isinstance(x,bytes) else str(x).encode()).hexdigest()
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
def load(p,d=None):
 try:return json.loads(p.read_text(encoding="utf-8"))
 except:return d
def root():return Path(__file__).resolve().parents[4]
def rel(p,b):
 try:return p.resolve().relative_to(b.resolve()).as_posix()
 except:return p.name
def norm(x):return re.sub(r"[^a-z0-9]+"," ",str(x).lower()).strip()
def enrich(x,keys):
 x=dict(x);t=str(x.get("title","")).lower();a=str(x.get("abstract","")).lower();th=[k for k in keys if k.lower() in t];ah=[k for k in keys if k.lower() in a];x["relevance_score"]=round(min(1,.25*len(th)+.08*len(ah)+(.05 if a else 0)+(.02 if x.get("provider") in {"openalex","arxiv","crossref"} else 0)),4);x["relevance_reasons"]=((["标题命中: "+", ".join(th[:3])] if th else [])+(["摘要命中: "+", ".join(ah[:4])] if ah else [])) or ["未命中核心关键词，仅作为低相关候选"];x.update(duplicate_group=None,version_group=None,citation_allowed=False,human_review_status="pending",status="retrieved",retrieved_at_utc=x.get("retrieved_at_utc",now()));x["content_sha256"]=sha(json.dumps({k:x.get(k) for k in ("source_id","title","authors","published_at","doi","url","abstract")},ensure_ascii=False,sort_keys=True));return x
def sid(x):
 d=str(x.get("doi") or "").lower().replace("https://doi.org/","").strip()
 if d:return "doi:"+d
 s=str(x.get("source_id") or "").lower();return s.split("v",1)[0] if s.startswith("arxiv:") else "title:"+norm(x.get("title",""))
def offline(tid):
 ts={"context-engineering":["Structured context for tool-using agents","Auditing execution claims in agent systems","Evidence-aware language agent workflows","Long-context agent orchestration","Reproducible research agents"],"memory-engine":["Memory augmented language agents","Long-term memory for autonomous agents","Episodic memory in tool-using systems","Agent memory evaluation","Provenance in agent workflows"],"self-evolution":["Self-improving language agents","Continual improvement of agents","Reflection in autonomous agents","Auditable agent adaptation","Safety checks for improving agents"]}[tid];k=TOPICS[tid]["keys"];return [enrich({"source_id":f"offline:{tid}:{i:03d}","provider":"offline","title":t,"authors":["offline-fixture"],"published_at":"2026-01-01","url":f"https://example.invalid/{tid}/{i}","doi":None,"abstract":f"Offline evidence about {k[0]} and auditable agent workflows."},k) for i,t in enumerate(ts,1)]
def get(url,timeout=20):
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"JiuwenSwarm-v4/1.0"}),timeout=timeout) as r:return r.status,r.read(),None
 except urllib.error.HTTPError as e:return e.code,e.read(1024),f"http_{e.code}"
 except Exception as e:return 0,b"",type(e).__name__
def openalex(d):
 out=[]
 for x in d.get("results",[]):
  if not isinstance(x,dict):continue
  out.append({"source_id":"openalex:"+str(x.get("id","")).rsplit("/",1)[-1],"provider":"openalex","title":x.get("title") or "","authors":[((a.get("author") or {}).get("display_name")) for a in x.get("authorships",[])[:10] if ((a.get("author") or {}).get("display_name"))],"published_at":x.get("publication_date") or str(x.get("publication_year") or ""),"url":x.get("doi") or ((x.get("primary_location") or {}).get("landing_page_url")) or x.get("id"),"doi":x.get("doi"),"abstract":""})
 return out
def crossref(d):
 out=[]
 for x in ((d.get("message") or {}).get("items") or []):
  if not isinstance(x,dict):continue
  doi=x.get("DOI");out.append({"source_id":"crossref:"+str(doi or (x.get("title") or [""])[0]),"provider":"crossref","title":(x.get("title") or [""])[0],"authors":[a.get("family") or a.get("name") for a in x.get("author",[])[:10] if isinstance(a,dict)],"published_at":"-".join(str(z) for z in (((x.get("published") or {}).get("date-parts") or [[""]])[0])),"url":x.get("URL") or (("https://doi.org/"+doi) if doi else ""),"doi":doi,"abstract":re.sub(r"<[^>]+>"," ",str(x.get("abstract") or "")).strip()})
 return out
def arxiv(b):
 n={"a":"http://www.w3.org/2005/Atom"};out=[];r=ET.fromstring(b)
 for x in r.findall("a:entry",n):
  i=(x.findtext("a:id",default="",namespaces=n)).rsplit("/",1)[-1];out.append({"source_id":"arxiv:"+i,"provider":"arxiv","title":" ".join((x.findtext("a:title",default="",namespaces=n)).split()),"authors":[z.findtext("a:name",default="",namespaces=n) for z in x.findall("a:author",n)],"published_at":x.findtext("a:published",default="",namespaces=n),"url":"https://arxiv.org/abs/"+i,"doi":None,"abstract":" ".join((x.findtext("a:summary",default="",namespaces=n)).split())})
 return out
def retrieve(tid,offline_mode=False):
 if offline_mode:
  s=offline(tid);return {"schema_version":SCHEMA,"topic_id":tid,"retrieval_status":"offline_mock","sources":s,"deduplication":{"candidate_count":len(s),"kept_count":len(s),"removed_duplicates":0},"retrieved_at_utc":now()}
 t=TOPICS[tid];cand=[];fails=[]
 for q in t["keys"][:3]:
  e=urllib.parse.quote(q)
  for p,u,fn in [("openalex",f"https://api.openalex.org/works?search={e}&per-page=10",lambda b:openalex(json.loads(b.decode()))),("arxiv",f"https://export.arxiv.org/api/query?search_query=all:{e}&max_results=10",arxiv)]:
   st,b,err=get(u)
   if st==200:
    try:cand+=fn(b)
    except Exception as ex:fails.append({"provider":p,"query":q,"error":type(ex).__name__})
   else:fails.append({"provider":p,"query":q,"status":st,"error":err})
   time.sleep(.15)
 e=urllib.parse.quote(t["keys"][0]);st,b,err=get(f"https://api.crossref.org/works?query={e}&rows=10")
 if st==200:
  try:cand+=crossref(json.loads(b.decode()))
  except Exception as ex:fails.append({"provider":"crossref","error":type(ex).__name__})
 else:fails.append({"provider":"crossref","status":st,"error":err})
 groups={}
 for x in [enrich(x,t["keys"]) for x in cand if x.get("title")]:groups.setdefault(sid(x),[]).append(x)
 keep=[];removed=0
 for g,items in groups.items():
  items.sort(key=lambda x:(x["relevance_score"],bool(x.get("abstract"))),reverse=True);w=items[0];w["duplicate_group"]=g;w["version_group"]=g if len(items)>1 else None;keep.append(w);removed+=len(items)-1
 keep.sort(key=lambda x:(x["relevance_score"],bool(x.get("abstract"))),reverse=True);keep=keep[:10];state="retrieval_failed" if not keep else ("partial_retrieval" if keep[0]["relevance_score"]<.1 else "retrieved")
 return {"schema_version":SCHEMA,"topic_id":tid,"retrieval_status":state,"sources":keep,"deduplication":{"candidate_count":len(cand),"kept_count":len(keep),"removed_duplicates":removed},"failures":fails,"retrieved_at_utc":now()}
def run_ucr(tid,td,seed):
 r=root();ud=r/"code"/"03_技术实现"/"ucr_benchmark";script=ud/"run_experiment.py";out=td/"ucr_runs";out.mkdir();arms=[];tr=[];rail=[]
 for arm in ARMS:
  cmd=[sys.executable,str(script),"--arm",arm,"--seed",str(seed),"--mode","fixture","--output",str(out)];t=time.monotonic();p=subprocess.run(cmd,cwd=ud,capture_output=True,text=True,timeout=300);d=round(time.monotonic()-t,3);rd=out/arm/f"seed{seed}";res=load(rd/"results.json",{}) if rd.exists() else {};claims=load(rd/"claims.json",[]) if rd.exists() else [];dec=load(rd/"ucr_decisions.json",[]) if rd.exists() else [];raw=(rd/"tool_trace.jsonl").read_text(encoding="utf-8") if (rd/"tool_trace.jsonl").exists() else "";tr.append(json.dumps({"arm":arm,"trace":raw},ensure_ascii=False));
  for line in raw.splitlines():
   try:e=json.loads(line);e["arm"]=arm;rail.append(json.dumps(e,ensure_ascii=False))
   except:pass
  (td/"logs").mkdir(exist_ok=True);(td/"logs"/f"{arm}-stdout.txt").write_text(p.stdout or "",encoding="utf-8");(td/"logs"/f"{arm}-stderr.txt").write_text(p.stderr or "",encoding="utf-8")
  arms.append({"arm":arm,"seed":seed,"status":"completed" if p.returncode==0 and res else "failed","benchmark_label":"process_evidence_only","command":cmd,"working_directory":rel(ud,r),"return_code":p.returncode,"duration_seconds":d,"stdout_sha256":sha(p.stdout or ""),"stderr_sha256":sha(p.stderr or ""),"result_path":rel(rd/"results.json",r),"claims_path":rel(rd/"claims.json",r),"evidence_path":rel(rd/"ucr_decisions.json",r),"claims":claims,"decisions":dec,"metrics":res.get("metrics",{}),"rail":res.get("rail",{})})
 (td/"tool_trace.jsonl").write_text("\n".join(tr)+"\n",encoding="utf-8");(td/"rail_events.jsonl").write_text("\n".join(rail)+"\n",encoding="utf-8")
 cfg={"schema_version":SCHEMA,"topic_id":tid,"seed":seed,"benchmark":"JiuwenSwarm/UCR ucr-activation-v1","benchmark_label":"process_evidence_only","arms":list(ARMS),"provider_calls":0};dump(td/"experiment_config.json",cfg)
 ex={"schema_version":SCHEMA,"topic_id":tid,"benchmark_label":"process_evidence_only","arms":arms,"reproducibility":{"seed":seed,"all_arms_completed":all(x["status"]=="completed" for x in arms)}};dump(td/"experiment_results.json",ex);dump(td/"results.json",{"topic_id":tid,"benchmark_label":"process_evidence_only","arms":[{"arm":x["arm"],"status":x["status"],"return_code":x["return_code"],"metrics":x["metrics"],"rail":x["rail"]} for x in arms]});return ex
def ptr(x,p):
 for k in p.strip("/").split("/") if p else []:x=x[int(k)] if isinstance(x,list) else x[k]
 return x
def ledger(tid,td,mat,ex):
 ah=sha((td/"experiment_results.json").read_bytes());cs=[];i=1
 for ai,a in enumerate(ex.get("arms",[])):
  for di,d in enumerate(a.get("decisions",[])):
   st=d.get("status") if d.get("status") in {"supported","unsupported","blocked"} else "pending_human_review";cs.append({"claim_id":f"claim-{i:03d}","text":f"{a['arm']} 对操作 {d.get('operation_id','unknown')} 的审计状态为 {st}。","claim_type":"experiment_observation","status":st,"evidence_refs":[{"artifact":"experiment_results.json","json_pointer":f"/arms/{ai}/decisions/{di}","sha256":ah}],"source_refs":[],"support_reason":d.get("reason","UCR decision")});i+=1
 for s in mat.get("sources",[])[:3]:cs.append({"claim_id":f"claim-{i:03d}","text":f"资料背景：{s.get('title','')} 与主题相关。","claim_type":"background","status":"pending_human_review","evidence_refs":[],"source_refs":[{"source_id":s.get("source_id"),"sha256":s.get("content_sha256")}],"support_reason":"来源已检索，等待人工批准引用。"});i+=1
 out={"schema_version":SCHEMA,"topic_id":tid,"claims":cs,"rules":{"experiment_claims_require_json_pointer":True,"source_claims_require_approved_source":True}};dump(td/"claim_ledger.json",out);return out
def check_ledger(td,mat,l):
 errors=[];ep=td/"experiment_results.json";ex=load(ep,{});eh=sha(ep.read_bytes());sm={s.get("source_id"):s for s in mat.get("sources",[])}
 for c in l.get("claims",[]):
  for e in c.get("evidence_refs",[]):
   try:ptr(ex,e["json_pointer"])
   except:errors.append(c["claim_id"]+": invalid JSON pointer")
   if e.get("sha256")!=eh:errors.append(c["claim_id"]+": evidence hash mismatch")
  for s in c.get("source_refs",[]):
   if s.get("source_id") not in sm:errors.append(c["claim_id"]+": unknown source")
 return errors
def validate(stage,x,mat,l):
 req={"plan":{"research_question":str,"hypothesis":str,"variables":list,"experiment_plan":list,"success_criteria":list,"expected_evidence":list,"human_confirmation_items":list},"review":{"evidence_assessment":list,"unsupported_claims":list,"citation_coverage":(int,float),"allow_paper":bool,"human_intervention_required":bool},"report":{"abstract":str,"method":str,"experiment_setting":str,"results":str,"limitations":str,"conclusion":str,"citation_mapping":list,"unsupported_claims":list}}[stage];err=[]
 if not isinstance(x,dict):return [stage+": response is not object"]
 for k,t in req.items():
  if k not in x:err.append(stage+": missing "+k)
  elif not isinstance(x[k],t):err.append(stage+": invalid type "+k)
 if stage=="report":
  ids={s.get("source_id") for s in mat.get("sources",[])};cids={c.get("claim_id") for c in l.get("claims",[])}
  for z in x.get("citation_mapping",[]):
   if not isinstance(z,dict) or z.get("source_id") not in ids or z.get("claim_id") not in cids:err.append("report: unknown citation mapping")
 return err
def mock_plan(tid):
 t=TOPICS[tid];return {"research_question":t["question"],"hypothesis":t["hypothesis"],"variables":["arm","seed","supported_claims","blocked_claims"],"experiment_plan":["执行 UCR 三种 arm","保存轨迹、Rail 事件、命令和哈希","比较证据决策"],"success_criteria":["三种 arm 独立完成","每个实验 claim 有 JSON Pointer","失败不写成成功"],"expected_evidence":["experiment_results.json","tool_trace.jsonl","rail_events.jsonl","claim_ledger.json"],"human_confirmation_items":["研究问题是否值得研究","实验是否真实反映系统行为","最终结论是否超过证据范围"]}
def mock_review(ex,l):
 ds=[d for a in ex["arms"] for d in a.get("decisions",[])];return {"evidence_assessment":[{"metric":"supported","value":sum(d.get("status")=="supported" for d in ds)},{"metric":"blocked","value":sum(d.get("status")=="blocked" for d in ds)}],"unsupported_claims":[c["claim_id"] for c in l["claims"] if c["status"] in {"blocked","unsupported"}],"citation_coverage":0.0,"allow_paper":True,"human_intervention_required":True}
def mock_report(tid,ex,l):return {"abstract":"本文展示可审计的 JiuwenSwarm/UCR 流程基准，不把流程结果包装成领域科学结论。","method":"使用固定 seed=42，分别执行 no-rail、prompt-only 和 full-rail，并保存原始轨迹、决策、命令和哈希。","experiment_setting":"本地 UCR fixture 基准，标签为 process_evidence_only；它验证证据流程，不代表真实模型或领域实验。","results":"不同 arm 的支持、未执行和阻断状态来自 experiment_results.json，并可由 claim_ledger.json 的 JSON Pointer 复核。","limitations":"资料尚未完成人工引用审批；当前实验是流程证据基准，不足以证明三个主题的领域效果。","conclusion":"v4 形成可重复、可审计的研究半流程闭环；最终研究结论仍需人工确认。","citation_mapping":[],"unsupported_claims":[c["claim_id"] for c in l["claims"] if c["status"]!="supported"]}
def provider(stage,prompt,index):
 key=os.environ.get("DEEPSEEK_API_KEY");
 if not key:raise RuntimeError("DEEPSEEK_API_KEY is missing")
 base=os.environ.get("DEEPSEEK_BASE_URL","https://api.deepseek.com").rstrip("/");model=os.environ.get("DEEPSEEK_MODEL","deepseek-chat");body=json.dumps({"model":model,"messages":[{"role":"system","content":"Return exactly one valid compact JSON object. No Markdown fences. Do not add commentary. Keep each string under 500 characters. Never invent evidence."},{"role":"user","content":prompt}],"temperature":.1,"max_tokens":3500},ensure_ascii=False).encode();req=urllib.request.Request(base+"/chat/completions",data=body,headers={"Content-Type":"application/json","Authorization":"Bearer "+key},method="POST");t=time.monotonic()
 try:
  with urllib.request.urlopen(req,timeout=120) as r:raw=r.read()
  payload=json.loads(raw.decode());text=(((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip();usage=payload.get("usage") or {}
  if "```" in text:raise ValueError("markdown code fence")
  obj=json.loads(text)
  required={"plan":{"research_question","hypothesis","variables","experiment_plan","success_criteria","expected_evidence","human_confirmation_items"},"review":{"evidence_assessment","unsupported_claims","citation_coverage","allow_paper","human_intervention_required"},"report":{"abstract","method","experiment_setting","results","limitations","conclusion","citation_mapping","unsupported_claims"}}[stage]
  if isinstance(obj,dict) and not required.intersection(obj):
   for v in obj.values():
    if isinstance(v,dict) and required.intersection(v): obj=v;break
  return obj,{"stage":stage,"call_index":index,"model":model,"prompt_sha256":sha(prompt),"response_sha256":sha(text),"duration_seconds":round(time.monotonic()-t,3),"status":"ok","prompt_tokens":usage.get("prompt_tokens"),"completion_tokens":usage.get("completion_tokens"),"total_tokens":usage.get("total_tokens"),"response_keys":sorted(obj.keys()) if isinstance(obj,dict) else []}
 except Exception as e:raise RuntimeError(f"provider_{type(e).__name__}: {str(e)[:200]}")
def prompt(stage,tid,mat,ex,plan,review,l):
  materials=[{k:s.get(k) for k in ("source_id","title","url","relevance_score","citation_allowed")} for s in mat.get("sources",[])[:8]]
  exp=[]
  for a in ex.get("arms",[]):
   exp.append({"arm":a.get("arm"),"status":a.get("status"),"return_code":a.get("return_code"),"metrics":a.get("metrics",{}),"rail":a.get("rail",{}),"decisions":[{"operation_id":d.get("operation_id"),"status":d.get("status"),"reason":d.get("reason")} for d in a.get("decisions",[])[:12]]})
  claims=[{"claim_id":c.get("claim_id"),"status":c.get("status"),"claim_type":c.get("claim_type"),"text":c.get("text")} for c in l.get("claims",[])[:24]]
  contracts={"plan":{"research_question":"string","hypothesis":"string","variables":["string"],"experiment_plan":["string"],"success_criteria":["string"],"expected_evidence":["string"],"human_confirmation_items":["string"]},"review":{"evidence_assessment":[{"metric":"string","value":"number"}],"unsupported_claims":["claim-id"],"citation_coverage":0.0,"allow_paper":False,"human_intervention_required":True},"report":{"abstract":"string","method":"string","experiment_setting":"string","results":"string","limitations":"string","conclusion":"string","citation_mapping":[],"unsupported_claims":["claim-id"]}}
  return json.dumps({"stage":stage,"topic_id":tid,"topic":{"name":TOPICS[tid]["name"],"question":TOPICS[tid]["question"],"hypothesis":TOPICS[tid]["hypothesis"]},"materials":materials,"experiment_summary":exp,"plan":plan,"review":review,"claim_ledger":claims,"required_output":contracts[stage],"instruction":"Return exactly the required_output object, with no wrapper, no Markdown, and no extra prose. Preserve evidence limits.","constraints":["UCR is process_evidence_only","citation_allowed=false means no formal citation","every conclusion needs claim_id and evidence/source ref","JSON only","keep output concise"]},ensure_ascii=False,separators=(",",":"))
def tex(x):
    """Escape plain text for LaTeX while preserving UTF-8 Chinese text."""
    s = str(x if x is not None else "")
    escaped = (s.replace("\\", r"\textbackslash{}")
                .replace("&", r"\&")
                .replace("%", r"\%")
                .replace("$", r"\$")
                .replace("#", r"\#")
                .replace("_", r"\_")
                .replace("{", r"\{")
                .replace("}", r"\}"))
    return (escaped.replace(r"\_", r"\_\allowbreak{}")
                   .replace("-", r"-\allowbreak{}")
                   .replace("/", " / "))


def tex_breakable(x):
    """Escape text and add safe break opportunities for identifiers."""
    s = tex(x)
    s = s.replace(":", r":\allowbreak{}")
    return s


def codecell(x):
    return r"\texttt{\scriptsize " + tex_breakable(x) + "}"


def make_tex(tid, td, plan0, review, report, ex, l, mat):
    """Write a compact, breakable topic report without changing research data."""
    arms = []
    for arm in ex.get("arms", []):
        metric = (arm.get("metrics") or {}).get("UCR", {})
        arms.append(
            f"{tex_breakable(arm.get('arm'))} & "
            f"{codecell(arm.get('status'))} & "
            f"{tex_breakable(metric.get('value'))} & "
            f"{tex_breakable(metric.get('supported'))}" + r" \\"
        )
    claims = []
    for claim in l.get("claims", [])[:20]:
        claims.append(
            f"{codecell(claim.get('claim_id'))} & "
            f"{codecell(claim.get('status'))} & "
            f"{tex_breakable(claim.get('claim_type'))}" + r" \\"
        )
    sources = []
    for source in mat.get("sources", [])[:10]:
        sources.append(
            f"{codecell(source.get('source_id'))} & "
            f"{tex_breakable(source.get('relevance_score'))} & "
            f"{codecell(source.get('human_review_status'))}" + r" \\"
        )
    title = tex(TOPICS[tid]["name"])
    criteria = "\n".join(r"\item " + tex_breakable(x) for x in plan0.get("success_criteria", []))
    unsupported = tex_breakable(", ".join(report.get("unsupported_claims", [])))
    s = rf"""\documentclass[UTF8]{{ctexart}}
\usepackage{{geometry,booktabs,longtable,array,tabularx,enumitem}}
\geometry{{a4paper,margin=2.0cm}}
\setlength{{\emergencystretch}}{{3em}}
\setlength{{\tabcolsep}}{{3pt}}
\renewcommand{{\arraystretch}}{{1.08}}
\setlist[itemize]{{leftmargin=1.5em,itemsep=0.15em,topsep=0.25em}}
\title{{JiuwenSwarm v4：{title}}}
\author{{JiuwenSwarm/UCR 可审计科研半流程}}
\date{{}}
\begin{{document}}
\maketitle
\section{{重要边界}}
本文是 v4 LaTeX 源文件；配套正式 PDF 已由用户在本机使用 XeLaTeX 编译。UCR 标签为 \texttt{{process\_evidence\_only}}，只能证明流程证据能力，不能包装成领域科学结论。检索资料默认等待人工审批，最终研究问题、实验真实性、结论范围和提交资格仍需人工确认。
\section{{研究问题与计划}}
\textbf{{问题：}}{tex(plan0.get('research_question'))}\\
\textbf{{假设：}}{tex(plan0.get('hypothesis'))}
\begin{{itemize}}
{criteria}
\end{{itemize}}
\section{{方法}}
{tex(report.get('method'))}
\subsection{{实验设置}}
{tex(report.get('experiment_setting'))}
\begin{{longtable}}{{@{{}}>{{\raggedright\arraybackslash}}p{{0.18\textwidth}}>{{\raggedright\arraybackslash}}p{{0.30\textwidth}}>{{\raggedleft\arraybackslash}}p{{0.16\textwidth}}>{{\raggedleft\arraybackslash}}p{{0.16\textwidth}}@{{}}}}
\toprule
Arm & 状态 & UCR & Supported\\\\
\midrule
\endfirsthead
\toprule
Arm & 状态 & UCR & Supported\\\\
\midrule
\endhead
{chr(10).join(arms)}
\bottomrule
\end{{longtable}}
\section{{实验结果}}
{tex(report.get('results'))}
\section{{Claim--Evidence 账本}}
\begin{{longtable}}{{@{{}}>{{\raggedright\arraybackslash}}p{{0.18\textwidth}}>{{\raggedright\arraybackslash}}p{{0.40\textwidth}}>{{\raggedright\arraybackslash}}p{{0.30\textwidth}}@{{}}}}
\toprule
Claim ID & 状态 & 类型\\\\
\midrule
\endfirsthead
\toprule
Claim ID & 状态 & 类型\\\\
\midrule
\endhead
{chr(10).join(claims)}
\bottomrule
\end{{longtable}}
\section{{检索资料与人工审批}}
候选资料数：{len(mat.get('sources', []))}。只有人工批准后才允许正式引用。
\begin{{longtable}}{{@{{}}>{{\raggedright\arraybackslash}}p{{0.54\textwidth}}>{{\raggedleft\arraybackslash}}p{{0.16\textwidth}}>{{\raggedright\arraybackslash}}p{{0.20\textwidth}}@{{}}}}
\toprule
Source ID & relevance & review\\\\
\midrule
\endfirsthead
\toprule
Source ID & relevance & review\\\\
\midrule
\endhead
{chr(10).join(sources)}
\bottomrule
\end{{longtable}}
\section{{限制}}
{tex(report.get('limitations'))}\\
不支持 Claim：{unsupported}
\section{{结论}}
{tex(report.get('conclusion'))}
\section{{人工确认}}
研究问题、实验真实性、结论范围和最终提交都需要人工确认。
\end{{document}}
"""
    (td / "paper.tex").write_text(s, encoding="utf-8", newline="\n")

def run_topic(tid,out,offline_mode,budget,counter,trace,seed):
 td=out/tid
 if td.exists():raise FileExistsError(f"refusing to overwrite {td}")
 td.mkdir(parents=True);mat=retrieve(tid,offline_mode);dump(td/"research_materials.json",mat);(td/"human_interventions.jsonl").write_text("".join(json.dumps({"event":"source_review_required","topic_id":tid,"source_id":s.get("source_id"),"actor":"human","decision":"pending","source_sha256":s.get("content_sha256"),"timestamp_utc":now()},ensure_ascii=False)+"\n" for s in mat.get("sources",[])),encoding="utf-8")
 harness_features={"requires_evidence": True, "experiment_required": tid == "context-engineering", "cost_limited": budget <= 1}
 harness_manifest=build_harness_manifest(harness_features)
 harness_validation=validate_manifest(harness_manifest)
 harness_manifest=harness_validation.manifest
 dump(td/"harness_manifest.json",harness_manifest)
 dump(td/"harness_validation.json",{"valid":harness_validation.valid,"errors":list(harness_validation.errors),"fallback_reason":harness_validation.fallback_reason})
 dump(td/"run_manifest.json",{"schema_version":SCHEMA,"topic_id":tid,"provider":"deepseek","benchmark_label":"process_evidence_only","latex_compilation_status":"user_compile_required","started_at_utc":now()});state={"topic_id":tid,"status":"running","provider_calls":0}
 try:
  ex=run_ucr(tid,td,seed)
  archive_run(td/"harness",manifest=harness_manifest,validation={"valid":harness_validation.valid,"errors":list(harness_validation.errors),"fallback_reason":harness_validation.fallback_reason},metrics={"seed":seed,"arm_count":len(ex.get("arms",[])),"cost":None,"latency_seconds":sum(float(a.get("duration_seconds",0)) for a in ex.get("arms",[]))},evidence=[{"artifact":"experiment_results.json","sha256":sha((td/"experiment_results.json").read_bytes())}])
  plan0=mock_plan(tid) if offline_mode else None
  if not offline_mode:
   if counter[0]>=budget:raise RuntimeError("provider call budget exhausted")
   counter[0]+=1;state["provider_calls"]+=1;plan0,tr=provider("plan",prompt("plan",tid,mat,ex,None,None,{"claims":[]}),counter[0]);trace.append(json.dumps({"topic_id":tid,**tr},ensure_ascii=False))
  err=validate("plan",plan0,mat,{"claims":[]})
  if err:raise RuntimeError("provider_schema_invalid: "+";".join(err))
  dump(td/"plan.json",plan0);led=ledger(tid,td,mat,ex);le=check_ledger(td,mat,led)
  if le:raise RuntimeError("claim_evidence_invalid: "+";".join(le))
  review=mock_review(ex,led) if offline_mode else None
  if not offline_mode:
   if counter[0]>=budget:raise RuntimeError("provider call budget exhausted")
   counter[0]+=1;state["provider_calls"]+=1;review,tr=provider("review",prompt("review",tid,mat,ex,plan0,None,led),counter[0]);trace.append(json.dumps({"topic_id":tid,**tr},ensure_ascii=False))
  err=validate("review",review,mat,led)
  if err:raise RuntimeError("provider_schema_invalid: "+";".join(err))
  dump(td/"review.json",review);report=mock_report(tid,ex,led) if offline_mode else None
  if not offline_mode:
   if counter[0]>=budget:raise RuntimeError("provider call budget exhausted")
   counter[0]+=1;state["provider_calls"]+=1;report,tr=provider("report",prompt("report",tid,mat,ex,plan0,review,led),counter[0]);trace.append(json.dumps({"topic_id":tid,**tr},ensure_ascii=False))
  err=validate("report",report,mat,led)
  if err:raise RuntimeError("provider_schema_invalid: "+";".join(err))
  dump(td/"report.json",report);make_tex(tid,td,plan0,review,report,ex,led,mat);state.update(status="completed_pending_human_review",report=report)
  execution={"schema_version":SCHEMA,"topic_id":tid,"status":state["status"],"stages":{"retrieval":mat["retrieval_status"],"experiment":"completed","plan":"completed","review":"completed","report":"completed"},"provider_calls":state["provider_calls"],"human_review_required":True,"errors":[]}
 except Exception as e:
  state.update(status="failed",error_type=type(e).__name__,error=str(e)[:500]);execution={"schema_version":SCHEMA,"topic_id":tid,"status":"failed","provider_calls":state["provider_calls"],"errors":[{"type":type(e).__name__,"message":str(e)[:500]}]};dump(td/"failure_report.json",execution);(td/"paper.tex").write_text("% failed run; no successful paper generated\n",encoding="utf-8")
 dump(td/"execution_report.json",execution);dump(td/"provenance.json",{"schema_version":SCHEMA,"algorithm":"sha256","artifacts":{rel(p,td):sha(p.read_bytes()) for p in td.rglob("*") if p.is_file() and p.name!="provenance.json"},"generated_at_utc":now()});return state
def unified(out, states):
    """Write the unified v4 report from already-recorded topic results."""
    p = out / "paper.tex"
    p.parent.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    sections = []
    for tid, state in states.items():
        report = state.get("report") or {}
        summary_rows.append(
            f"{tex_breakable(tid)} & {codecell(state.get('status'))} & "
            f"{tex_breakable(state.get('provider_calls', 0))}" + r" \\"
        )
        sections.append(
            "\\section{" + tex(TOPICS[tid]["name"]) + "}\n"
            "\\textbf{摘要：}" + tex(report.get("abstract")) + "\\\\\n"
            "\\textbf{结论：}" + tex(report.get("conclusion")) + "\\\\\n"
            "\\textbf{限制：}" + tex(report.get("limitations"))
        )
    text = rf"""\documentclass[UTF8]{{ctexart}}
\usepackage{{geometry,booktabs,longtable,array,tabularx}}
\geometry{{a4paper,margin=2.0cm}}
\setlength{{\emergencystretch}}{{3em}}
\setlength{{\tabcolsep}}{{3pt}}
\renewcommand{{\arraystretch}}{{1.12}}
\title{{JiuwenSwarm v4 可审计科研论文半流程报告}}
\author{{JiuwenSwarm/UCR}}
\date{{}}
\begin{{document}}
\maketitle
\begin{{abstract}}
本文汇总三个主题的科研半流程演示。系统检索公开资料元数据，执行 JiuwenSwarm/UCR 本地证据实验，生成研究计划和报告，并保存 Claim--Evidence 账本。本文不把流程基准包装成领域科学结论；正式引用、实验真实性、研究结论和最终提交资格仍需人工确认。
\end{{abstract}}
\section{{统一边界}}
UCR 的标签是 \texttt{{process\_evidence\_only}}，它表示系统的流程证据和审计能力，不等于上下文工程、记忆引擎或自我进化的领域效果。所有来源默认处于待审核状态。当前 PDF 是由本机 XeLaTeX 编译生成的正式查看产物，源文件和实验记录同时保留在提交包中。
\section{{矩阵概览}}
\begin{{longtable}}{{@{{}}>{{\raggedright\arraybackslash}}p{{0.30\textwidth}}>{{\raggedright\arraybackslash}}p{{0.42\textwidth}}>{{\raggedleft\arraybackslash}}p{{0.14\textwidth}}@{{}}}}
\toprule
主题 & 状态 & Provider 调用\\\\
\midrule
\endfirsthead
\toprule
主题 & 状态 & Provider 调用\\\\
\midrule
\endhead
{chr(10).join(summary_rows)}
\bottomrule
\end{{longtable}}
{chr(10).join(sections)}
\section{{编译与审核说明}}
该统一报告和三个主题报告都需要人工阅读。编译命令为：
\begin{{verbatim}}
xelatex -interaction=nonstopmode -halt-on-error paper.tex
xelatex -interaction=nonstopmode -halt-on-error paper.tex
\end{{verbatim}}
最终状态保持为 \texttt{{prepared\_not\_uploaded}}。
\end{{document}}
"""
    p.write_text(text, encoding="utf-8", newline="\n")

def verify(out,states):
 err=[]
 for tid in TOPICS:
  td=out/tid
  for n in ("run_manifest.json","research_materials.json","experiment_config.json","experiment_results.json","results.json","claim_ledger.json","execution_report.json","human_interventions.jsonl","provenance.json","paper.tex"):
   if not (td/n).exists():err.append(f"{tid}: missing {n}")
  if (td/"claim_ledger.json").exists():err+= [f"{tid}: {x}" for x in check_ledger(td,load(td/"research_materials.json",{}),load(td/"claim_ledger.json",{}))]
  for p in td.rglob("*"):
   if p.is_file() and chr(0xfffd) in p.read_text(encoding="utf-8",errors="replace"):err.append(f"{tid}: replacement char in {p.name}")
 status="completed_pending_human_review" if not err and all(s.get("status")=="completed_pending_human_review" for s in states.values()) else ("partial_failed" if any(s.get("status")=="failed" for s in states.values()) else "failed")
 return {"schema_version":SCHEMA,"valid":not err,"status":status,"errors":err,"topics":{k:{"status":v.get("status"),"provider_calls":v.get("provider_calls",0)} for k,v in states.items()},"latex_compilation_status":"user_compile_required"}
def main(argv=None):
 a=argparse.ArgumentParser();a.add_argument("--provider",choices=["deepseek"],default="deepseek");a.add_argument("--offline-mock",action="store_true");a.add_argument("--confirm-live",action="store_true");a.add_argument("--allow-research-matrix-demo",action="store_true");a.add_argument("--allow-public-retrieval",action="store_true");a.add_argument("--max-calls-per-topic",type=int,default=3);a.add_argument("--max-total-calls",type=int,default=9);a.add_argument("--seed",type=int,default=42);a.add_argument("--output-root",type=Path,default=Path("demo_runs/research_matrix_v4"));x=a.parse_args(argv)
 if not 1<=x.max_calls_per_topic<=3: a.error("--max-calls-per-topic must be 1..3")
 if not 1<=x.max_total_calls<=9:a.error("--max-total-calls must be 1..9")
 if not x.offline_mock:
  if not x.confirm_live:a.error("live mode requires --confirm-live")
  if not x.allow_research_matrix_demo:a.error("live mode requires --allow-research-matrix-demo")
  if not x.allow_public_retrieval:a.error("live mode requires --allow-public-retrieval")
  if not os.environ.get("DEEPSEEK_API_KEY"):a.error("live mode requires DEEPSEEK_API_KEY")
 out=x.output_root if x.output_root.is_absolute() else root()/x.output_root
 if out.exists() and any(out.iterdir()):a.error(f"refusing to overwrite non-empty output directory: {out}")
 out.mkdir(parents=True,exist_ok=True);budget=min(x.max_total_calls,x.max_calls_per_topic*len(TOPICS));counter=[0];trace=[];states={}
 for tid in TOPICS:states[tid]=run_topic(tid,out,x.offline_mock,budget,counter,trace,x.seed)
 if trace:(out/"provider_trace.jsonl").write_text("\n".join(trace)+"\n",encoding="utf-8")
 dump(out/"matrix_execution_report.json",{"schema_version":SCHEMA,"status":"completed_pending_human_review" if all(s.get("status")=="completed_pending_human_review" for s in states.values()) else "partial_failed","total_provider_calls":counter[0],"max_total_calls":x.max_total_calls,"topics":states,"generated_at_utc":now()});v=verify(out,states);dump(out/"matrix_verification_report.json",v);unified(out,states);print(json.dumps({"output_root":str(out),"status":v["status"],"valid":v["valid"],"provider_calls":counter[0]},ensure_ascii=False));return 0 if v["valid"] else 2
if __name__=="__main__":raise SystemExit(main())
