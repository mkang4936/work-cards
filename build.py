# 외투법인 실무 카드 사이트 만들기
# 원본/<번호>/카드.html → c/<번호>/<장>.png 와 c/<번호>/index.html, 첫 화면 index.html
# 실행: python -I build.py
# 기계 점검(설계.md 「만드는 방법」)을 먼저 돌리고, 하나라도 걸리면 아무것도 만들지 않고 멈춘다.
import html
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
KOREAN_GUARD = Path.home() / ".claude" / "hooks" / "korean_guard.py"
W, H = 1080, 1350

# 사례집 어휘 규칙에서 카드에 그대로 쓰는 것(설계.md). 활용형이 갈리는 말은 금지된 꼴만 적는다.
BANNED_WORDS = ["뗀다", "떼는", "떼고", "떼어", "통장", "통째로", "사고가 난다", "챙겨야", "빼다"]
BANNED_STANDALONE = ["돈"]
# 공개 페이지라 거래처 이름이 들어가면 안 된다.
CLIENT_NAMES = ["엔구", "코리아스마일", "우에무라", "다이요", "에이지스", "Ajis", "TIP"]

STYLE = """
:root{--navy:#1f3a5f;--navy-soft:#e9eef5;--ink:#1d232b;--gray:#5b6573;--line:#dde2e8;--bg-soft:#f6f7f9;--ok:#2f7a5b}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--bg-soft)}
body{font-family:"Noto Sans KR","Malgun Gothic","Apple SD Gothic Neo",sans-serif;color:var(--ink);word-break:keep-all;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
.wrap{max-width:560px;margin:0 auto;padding:20px 16px 40px}
.badge{display:inline-flex;align-items:center;gap:7px;font-size:13px;font-weight:600;color:var(--ok);background:#eaf4ef;border-radius:999px;padding:5px 12px}
.badge::before{content:"";width:7px;height:7px;border-radius:50%;background:var(--ok)}
.foot{margin-top:28px;font-size:12px;color:#9aa3ae;line-height:1.6;text-align:center}
"""

# 예약 공개: 게시일(한국 날짜)이 오지 않은 카드는 목록에서 숨긴다.
TODAY_JS = "var today=new Date(Date.now()+9*3600*1000).toISOString().slice(0,10);"

INDEX = """<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>@TITLE@</title>
<meta property="og:type" content="website"><meta property="og:title" content="@TITLE@">
<meta property="og:description" content="@DESC@"><meta property="og:image" content="@OGIMG@"><meta property="og:url" content="@URL@">
<style>@STYLE@
h1{font-size:28px;font-weight:800;letter-spacing:-.5px;margin-top:14px}
.sub{font-size:15px;color:var(--gray);margin-top:8px;line-height:1.6}
.search{width:100%;margin-top:20px;font:inherit;font-size:16px;padding:12px 14px;border:1px solid var(--line);border-radius:12px;background:#fff}
.list{list-style:none;margin-top:16px;display:flex;flex-direction:column;gap:12px}
.item a{display:flex;gap:14px;background:#fff;border:1px solid var(--line);border-radius:14px;padding:12px}
.item img{width:84px;height:105px;object-fit:cover;border-radius:8px;border:1px solid var(--line);flex:none;background:#fff}
.meta{display:flex;flex-direction:column;min-width:0}
.no{font-size:12px;font-weight:700;color:var(--navy);letter-spacing:.5px}
.new{display:inline-block;margin-left:6px;font-size:11px;color:#fff;background:var(--navy);border-radius:6px;padding:1px 6px;letter-spacing:0}
.ttl{font-size:16px;font-weight:700;line-height:1.4;margin-top:3px}
.sum{font-size:13px;color:var(--gray);line-height:1.5;margin-top:4px}
.tags{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}
.tag{font-size:11.5px;color:var(--gray);background:var(--bg-soft);border:1px solid var(--line);border-radius:6px;padding:1px 6px}
.tag.season{color:var(--ok);background:#eaf4ef;border-color:#cfe6da}
.none{display:none;text-align:center;color:var(--gray);font-size:14px;margin-top:24px}
</style></head><body><div class="wrap">
<span class="badge">매주 화·금</span>
<h1>@TITLE@</h1>
<p class="sub">@DESC@</p>
<input class="search" id="q" type="search" placeholder="찾기 — 예: 경영자문료, 주재원, 배당">
<ul class="list" id="list">@ITEMS@</ul>
<p class="none" id="none">찾는 카드가 없습니다.</p>
<p class="foot">실무 참고용이며 개별 사안은 검토가 필요합니다.<br>기준일 뒤의 개정·새 해석·판례는 반영되지 않았을 수 있습니다.</p>
</div>
<script>
@TODAY@
var items=[].slice.call(document.querySelectorAll('.item')).filter(function(li){
  if(li.getAttribute('data-pub')>today){li.parentNode.removeChild(li);return false;}return true;});
var latest=items.reduce(function(m,li){var p=li.getAttribute('data-pub');return p>m?p:m;},'');
items.forEach(function(li){if(li.getAttribute('data-pub')===latest){var s=li.querySelector('.no');s.insertAdjacentHTML('beforeend','<span class="new">새 카드</span>');}});
var q=document.getElementById('q');
function filt(){var v=q.value.trim().toLowerCase(),n=0;
items.forEach(function(li){var hit=!v||li.getAttribute('data-k').toLowerCase().indexOf(v)>=0;li.style.display=hit?'':'none';if(hit)n++;});
document.getElementById('none').style.display=n?'none':'block';}
q.addEventListener('input',filt);filt();
</script>
</body></html>
"""

ITEM = """<li class="item" data-k="@KEY@" data-pub="@PUB@"><a href="c/@NO@/">
<img src="c/@NO@/1.png" alt="" loading="lazy">
<div class="meta"><span class="no">@LABEL@ · @DATE@</span><span class="ttl">@T@</span><span class="sum">@S@</span>
<span class="tags">@TAGS@</span></div></a></li>"""

VIEWER = """<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>@SHORT@ · @T@</title>
<meta property="og:type" content="article"><meta property="og:title" content="실무 @LABEL@ · @T@">
<meta property="og:description" content="@S@"><meta property="og:image" content="@OGIMG@"><meta property="og:url" content="@URL@">
<style>@STYLE@
.bar{display:flex;justify-content:space-between;align-items:center}
.home{font-size:14px;color:var(--gray)}
.track{margin-top:14px;display:flex;overflow-x:auto;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;scrollbar-width:none;border-radius:14px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.track::-webkit-scrollbar{display:none}
.track img{flex:0 0 100%;width:100%;min-width:0;height:auto;aspect-ratio:4/5;scroll-snap-align:start;display:block;background:#fff}
.ctl{display:flex;justify-content:center;align-items:center;gap:18px;margin-top:14px}
.ctl button{font:inherit;font-size:20px;width:44px;height:44px;border-radius:50%;border:1px solid var(--line);background:#fff;color:var(--navy);cursor:pointer}
.ctl button:disabled{opacity:.35;cursor:default}
.dots{display:flex;gap:7px}
.dots i{width:7px;height:7px;border-radius:50%;background:#c9d0d8}
.dots i.on{background:var(--navy);width:18px;border-radius:4px}
.info{margin-top:18px;font-size:13px;color:var(--gray);line-height:1.6;text-align:center}
.next{display:block;margin-top:16px;text-align:center;font-size:15px;font-weight:600;color:#fff;background:var(--navy);border-radius:12px;padding:13px}
</style></head><body><div class="wrap">
<div class="bar"><span class="badge">@LABEL@ · @DATE@</span><a class="home" href="../../">전체 카드 ›</a></div>
<div class="track" id="t">@IMGS@</div>
<div class="ctl"><button id="p" aria-label="이전">‹</button><span class="dots" id="d">@DOTS@</span><button id="n" aria-label="다음">›</button></div>
<p class="info">@INFO@</p>
<a class="next" href="../../">다른 카드 보기</a>
<p class="foot">실무 참고용이며 개별 사안은 검토가 필요합니다.<br>기준일 뒤의 개정·새 해석·판례는 반영되지 않았을 수 있습니다.</p>
</div>
<script>
var t=document.getElementById('t'),dots=[].slice.call(document.querySelectorAll('#d i')),N=dots.length,p=document.getElementById('p'),n=document.getElementById('n');
var idx=0,timer=null;
function clamp(i){return Math.max(0,Math.min(N-1,i));}
function paint(){dots.forEach(function(d,k){d.className=k===idx?'on':'';});p.disabled=idx<=0;n.disabled=idx>=N-1;}
function go(i){idx=clamp(i);var x=idx*t.clientWidth;t.scrollTo({left:x,behavior:'smooth'});paint();
setTimeout(function(){if(Math.abs(t.scrollLeft-idx*t.clientWidth)>2)t.scrollLeft=idx*t.clientWidth;},450);}
t.addEventListener('scroll',function(){clearTimeout(timer);timer=setTimeout(function(){idx=clamp(Math.round(t.scrollLeft/t.clientWidth));paint();},120);});
p.onclick=function(){go(idx-1);};n.onclick=function(){go(idx+1);};
document.addEventListener('keydown',function(e){if(e.key==='ArrowLeft')go(idx-1);if(e.key==='ArrowRight')go(idx+1);});
var h=parseInt(location.hash.slice(1),10);if(h>=1&&h<=N){idx=h-1;t.scrollLeft=idx*t.clientWidth;}
paint();
</script>
</body></html>
"""

# 카드 원본을 한 장씩 띄워 내용이 카드 밖으로 넘치는지 재는 스크립트(임시 사본에만 붙인다).
OVERFLOW_JS = """<script>
window.addEventListener('load',function(){var out=[];
[].slice.call(document.querySelectorAll('section.slide')).forEach(function(s,i){
var was=s.style.display;s.style.display='flex';var r=s.getBoundingClientRect();
[].slice.call(s.querySelectorAll('*')).forEach(function(e){var b=e.getBoundingClientRect();
if(b.width&&b.height&&(b.bottom>r.bottom+1||b.right>r.right+1)){out.push((i+1)+'장 '+e.tagName.toLowerCase()+' '+(e.textContent||'').trim().slice(0,20));}});
s.style.display=was;});
var pre=document.createElement('pre');pre.id='__overflow';pre.textContent=JSON.stringify(out);document.body.appendChild(pre);});
</script>"""

# 장 안의 블록 겹침·상자 간격(10px 미만)·문서번호 줄 끊김을 재는 스크립트(제작 세션 작업\점검.py에서 옮김, 2026-10-23 — 두 번 나온 검토 지적).
LAYOUT_JS = r"""<script>
window.addEventListener('load',function(){var out=[];
[].slice.call(document.querySelectorAll('section.slide')).forEach(function(s,i){
var was=s.style.display;s.style.display='flex';
var kids=[].slice.call(s.children).filter(function(e){return e.tagName!=='SCRIPT'});
for(var a=0;a<kids.length;a++)for(var b=a+1;b<kids.length;b++){
var A=kids[a].getBoundingClientRect(),B=kids[b].getBoundingClientRect();
if(A.height&&B.height&&A.bottom>B.top+1&&B.bottom>A.top+1&&A.right>B.left+1&&B.right>A.left+1)
out.push((i+1)+'장 겹침 '+(kids[a].textContent||'').trim().slice(0,12)+' / '+(kids[b].textContent||'').trim().slice(0,12));}
for(var c=1;c<kids.length;c++){var P=kids[c-1].getBoundingClientRect(),Q=kids[c].getBoundingClientRect();
var gap=Q.top-P.bottom;if(P.height&&Q.height&&kids[c].className.indexOf('arr')<0&&kids[c-1].className.indexOf('arr')<0&&kids[c].tagName!=='FOOTER'&&gap>=0&&gap<10)
out.push((i+1)+'장 상자 간격 '+Math.round(gap)+'px: '+(kids[c].textContent||'').trim().slice(0,12));}
var w=document.createTreeWalker(s,NodeFilter.SHOW_TEXT,null,false),nd,re=/[^\s·()\/,]*\d[^\s·()\/,]*-[^\s·()\/,]+/g,m;
while(nd=w.nextNode()){re.lastIndex=0;while(m=re.exec(nd.data)){var r=document.createRange();r.setStart(nd,m.index);r.setEnd(nd,m.index+m[0].length);
var tops={};[].slice.call(r.getClientRects()).forEach(function(q){if(q.width>1)tops[Math.round(q.top)]=1;});
if(Object.keys(tops).length>1)out.push((i+1)+'장 번호 줄 끊김: '+m[0]);}}
s.style.display=was;});
var pre=document.createElement('pre');pre.id='__layout';pre.textContent=JSON.stringify(out);document.body.appendChild(pre);});
</script>"""

# 「빼다」 활용형(뺀·빼고·빼서·빼면·뺍니다·빼야·뺐 등) — BANNED_WORDS의 「빼다」 꼴만으로는 빠져나간다.
BBAE_RE = r"뺀|뺍|뺐|빼(?:고|서|면|야|도|지|어|자)"

# 분량 상한(설계.md 「묶음 작업 순서」 3, 사용자 2026-10-23): 공백을 뺀 보이는 글자 수.
MAX_CARD_CHARS, MAX_SLIDE_CHARS = 2800, 700


def fill(tpl, **kw):
    for k, v in kw.items():
        tpl = tpl.replace("@" + k + "@", v)
    return tpl


def dot_date(iso):
    return iso.replace("-", ".")


def png_size(p):
    b = p.read_bytes()[:24]
    return int.from_bytes(b[16:20], "big"), int.from_bytes(b[20:24], "big")


def visible_text(src_html):
    body = re.sub(r"<(style|script)\b.*?</\1>", " ", src_html, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", "\n", body))


def slide_chars(src_html):
    body = re.sub(r"<(style|script)\b.*?</\1>", " ", src_html, flags=re.S)
    return [len(re.sub(r"\s", "", html.unescape(re.sub(r"<[^>]+>", "", s))))
            for s in re.findall(r'<section class="slide".*?</section>', body, flags=re.S)]


def load_guard():
    spec = importlib.util.spec_from_file_location("korean_guard", KOREAN_GUARD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def dom_check(src, js, pre_id, what):
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "점검.html"
        tmp.write_text(src.read_text(encoding="utf-8").replace("</body>", js + "</body>"), encoding="utf-8")
        r = subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--virtual-time-budget=3000",
                            f"--window-size={W},{H}", "--dump-dom", tmp.as_uri()],
                           capture_output=True, timeout=90)
        m = re.search(rf'<pre id="{pre_id}">(.*?)</pre>', r.stdout.decode("utf-8", "replace"), re.S)
        if not m:
            return [f"{what} 점검을 실행하지 못했습니다"]
        return json.loads(html.unescape(m.group(1)))


def overflow_check(src):
    return dom_check(src, OVERFLOW_JS, "__overflow", "넘침")


def layout_check(src):
    return dom_check(src, LAYOUT_JS, "__layout", "배치")


def check_card(c, src, guard):
    """설계.md의 기계 점검. 걸린 것을 문장으로 돌려준다."""
    no = c["no"]
    problems = []
    raw = src.read_text(encoding="utf-8")
    text = visible_text(raw)
    for w in BANNED_WORDS:
        if w in text:
            problems.append(f"{no}번 금지 어휘 「{w}」")
    for w in BANNED_STANDALONE:
        if re.search(rf"(?<![가-힣]){w}(?![가-힣])", text):
            problems.append(f"{no}번 금지 어휘 「{w}」")
    for m in sorted(set(re.findall(BBAE_RE, text))):
        problems.append(f"{no}번 금지 어휘 「빼다」 활용형 「{m}」")
    for name in CLIENT_NAMES:
        if re.search(rf"(?<![A-Za-z가-힣]){re.escape(name)}(?![A-Za-z])", text):
            problems.append(f"{no}번 거래처 이름 「{name}」")
    for s in guard.english_chunks(text, guard.MIN_WORDS_TEXT):
        problems.append(f"{no}번 영어 문장 「{s}」")
    if c.get("kind") != "안내" and not c.get("basis_date"):
        problems.append(f"{no}번 근거 확인 기준일(basis_date)이 비어 있음")
    if dot_date(c["published"]) not in raw:
        problems.append(f"{no}번 카드 안에 게시일 {dot_date(c['published'])} 표기가 없음")
    chars = slide_chars(raw)
    # 합계 상한은 사용자가 승인한 카드만 cards.json의 max_chars로 예외를 둔다. 장당 상한은 예외 없음.
    card_max = c.get("max_chars", MAX_CARD_CHARS)
    if sum(chars) > card_max:
        problems.append(f"{no}번 분량 {sum(chars)}자 — 상한 {card_max}자 초과")
    for i, n in enumerate(chars, 1):
        if n > MAX_SLIDE_CHARS:
            problems.append(f"{no}번 {i}장 분량 {n}자 — 장당 상한 {MAX_SLIDE_CHARS}자 초과")
    for o in overflow_check(src):
        problems.append(f"{no}번 넘침: {o}")
    for o in layout_check(src):
        problems.append(f"{no}번 배치: {o}")
    return problems


def render(src, out_dir, count):
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    uri = src.as_uri()
    for i in range(1, count + 1):
        subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=1", f"--window-size={W},{H}",
                        f"--screenshot={out_dir / f'{i}.png'}", f"{uri}#{i}"],
                       capture_output=True, timeout=60)
        time.sleep(0.3)


def main():
    conf = json.loads((ROOT / "cards.json").read_text(encoding="utf-8"))
    site, cards = conf["site"], conf["cards"]
    base = site["base_url"]
    esc = html.escape
    guard = load_guard()

    # 1) 기계 점검 — 걸리면 아무것도 만들지 않는다
    problems = []
    for c in cards:
        problems += check_card(c, ROOT / "원본" / c["no"] / "카드.html", guard)
    if problems:
        print("기계 점검에 걸려 만들지 않았습니다:", *problems, sep="\n  ")
        sys.exit(1)

    # 2) 이미지와 페이지
    items = []
    for c in cards:
        no = c["no"]
        # 호외는 cards.json의 label(예: 「호외 01」)로 표시한다. 정규 카드는 「카드 NN」 그대로.
        label, short = c.get("label") or f"카드 {no}", c.get("label") or no
        src = ROOT / "원본" / no / "카드.html"
        count = len(re.findall(r'<section class="slide"', src.read_text(encoding="utf-8")))
        out_dir = ROOT / "c" / no
        render(src, out_dir, count)
        for i in range(1, count + 1):
            p = out_dir / f"{i}.png"
            if not p.exists():
                problems.append(f"{no}번 {i}장 이미지 없음")
            elif png_size(p) != (W, H):
                problems.append(f"{no}번 {i}장 크기 {png_size(p)}")
        imgs = "".join(f'<img src="{i}.png" alt="{esc(c["title"])} {i}/{count}">' for i in range(1, count + 1))
        info = "옆으로 넘겨 보세요" + (f" · 근거 확인 기준 {esc(c['basis_date'])}" if c.get("basis_date") else "")
        (out_dir / "index.html").write_text(fill(
            VIEWER, STYLE=STYLE, NO=no, LABEL=esc(label), SHORT=esc(short), T=esc(c["title"]), S=esc(c["summary"]), DATE=dot_date(c["published"]),
            OGIMG=f"{base}c/{no}/1.png", URL=f"{base}c/{no}/", IMGS=imgs, DOTS="<i></i>" * count,
            INFO=info), encoding="utf-8")
        tags = ([c["season"]] + [t for t in c["tags"] if t != c["season"]]) if c.get("season") else c["tags"]
        key = " ".join([c["title"], c["summary"]] + tags)
        items.append((c["published"], no, fill(
            ITEM, KEY=esc(key), PUB=c["published"], NO=no, LABEL=esc(label), DATE=dot_date(c["published"]),
            T=esc(c["title"]), S=esc(c["summary"]),
            TAGS="".join(f'<span class="tag{" season" if t == c.get("season") else ""}">{esc(t)}</span>' for t in tags))))

    if problems:
        print("이미지 점검에 걸렸습니다:", *problems, sep="\n  ")
        sys.exit(1)

    items.sort(reverse=True)
    today = date.today().isoformat()
    shown = [i for i in items if i[0] <= today] or items
    (ROOT / "index.html").write_text(fill(
        INDEX, STYLE=STYLE, TITLE=esc(site["title"]), DESC=esc(site["description"]), TODAY=TODAY_JS,
        OGIMG=f"{base}c/{shown[0][1]}/1.png", URL=base, ITEMS="".join(i[2] for i in items)), encoding="utf-8")
    (ROOT / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")

    print(f"카드 {len(cards)}개 처리 · 기계 점검 통과 · 이미지 모두 {W}x{H}")


if __name__ == "__main__":
    main()
