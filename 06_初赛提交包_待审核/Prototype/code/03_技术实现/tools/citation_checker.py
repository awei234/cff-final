"""引用在线核验（F04 配套）：arXiv + OpenAlex 双通道。
用法：python citation_checker.py --pool <references目录> [--file paper.tex]
容错规则：网络失败/超时 → ambiguous，绝不误杀。
2026-08-14 服务器实测：S2 429 限流弃用；OpenAlex 为主通道。
2026-08-14 v2 修复（敏感性分析 c03 漏杀）：search= 相关性检索会假通过捏造标题
→ 改 filter=title.search 短语搜索 + 标题规范化相似度阈值（≥0.92 verified /
≥0.60 ambiguous / <0.60 not_found），防漏杀同时保留拼写宽容与网络失败不误杀。
"""
import argparse, difflib, json, re, sys, time, urllib.request, urllib.parse, pathlib

CITE_RE = re.compile(r"\\cite[a-z]*\{([^}]*)\}")
ARXIV_API = "https://export.arxiv.org/api/query?id_list={}"
# 短语搜索 + 只取标题/年份（select 减小响应）
OPENALEX_API = ("https://api.openalex.org/works?filter=title.search:{}"
                "&per-page=1&select=title,publication_year")


def _norm_title(t: str) -> str:
    """标题规范化：小写 + 非字母数字折叠为空格 + 压缩空白。"""
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def _title_ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _norm_title(a), _norm_title(b)).ratio()


def check_openalex(title):
    if not title or not title.strip():
        return "not_found"              # 空标题直接拒绝（防 _norm_title 空串 ratio=1.0 假通过）
    try:
        q = urllib.parse.quote(f'"{title}"')          # 短语搜索：必须整体出现
        url = OPENALEX_API.format(q)
        req = urllib.request.Request(url, headers={"User-Agent": "CCF-ResearchBot/1.0 (mailto:vergil@local)"})
        data = None
        last_err = None
        for attempt in range(2):                       # 429 只重试 1 次（IP 级限流重试无意义）
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    data = json.loads(r.read().decode("utf-8", "ignore"))
                break
            except urllib.error.HTTPError as e:
                last_err = e
                if e.code in (429, 500, 502, 503, 504):
                    time.sleep(2 * (attempt + 1))
                    continue
                return "ambiguous"
            except Exception:
                return "ambiguous"
        if data is None:
            return "ambiguous" if isinstance(last_err, urllib.error.HTTPError) else "not_found"
        hits = data.get("results") or []
        if not hits or not hits[0].get("publication_year"):
            return "not_found"
        top_title = hits[0].get("title") or ""
        ratio = _title_ratio(title, top_title)
        if ratio >= 0.92:
            return "verified"
        if ratio >= 0.60:
            return "ambiguous"     # 疑似命中但标题不吻合：不误杀，提示人工复核
        return "not_found"         # 完全无关 → 视为查无此文
    except Exception:
        return "ambiguous"

def check_arxiv(arxiv_id):
    try:
        req = urllib.request.Request(ARXIV_API.format(arxiv_id), headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read().decode("utf-8", "ignore")
        return "verified" if "<entry>" in body else "not_found"
    except Exception:
        return "ambiguous"

def verify_pool(pool_dir):
    ref = pathlib.Path(pool_dir)
    total = verified = not_found = ambiguous = 0
    rows = []
    for sub in sorted(ref.iterdir()):
        if not sub.is_dir():
            continue
        meta = sub / "meta" / "meta_info.txt"
        title = ""
        arxiv_id = ""
        if meta.exists():
            for line in meta.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.lower().startswith("title:"):
                    title = line.split(":", 1)[1].strip()
                if "arxiv.org/abs/" in line:
                    m = re.search(r"abs/([0-9.]+)", line)
                    if m: arxiv_id = m.group(1)
        status = "skip(无标题)"
        if title or arxiv_id:
            # 双通道取并集证据：arXiv id（强证据、API 稳定）优先；OpenAlex 标题兜底
            results = []
            if arxiv_id:
                results.append(check_arxiv(arxiv_id))
            if title:
                results.append(check_openalex(title))
            if "verified" in results:
                status = "verified"
            elif results and all(r == "not_found" for r in results):
                status = "not_found"
            else:
                status = "ambiguous"
            time.sleep(0.6)  # 温和限速（免费层，重试退避内嵌 check_openalex）
        total += 1
        if status == "verified": verified += 1
        elif status == "not_found": not_found += 1
        elif status == "ambiguous": ambiguous += 1
        rows.append((sub.name, status, title[:45], arxiv_id))
        print(f"{status:10s} {sub.name:28s} {title[:45]}")
    print(f"\n总计 {total} | verified {verified} | not_found {not_found} | ambiguous {ambiguous}")
    return verified, total

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", default="references")
    args = ap.parse_args()
    verify_pool(args.pool)
