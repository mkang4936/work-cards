# 외투법인 실무 카드 사이트 만들기
# 원본/<번호>/카드.html → c/<번호>/<장>.png 와 c/<번호>/index.html, 첫 화면 index.html
# 실행: python -I build.py
import html
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
W, H = 1080, 1350

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
.no{font-size:12px;font-weight:700;color:var(--navy);letter-spacing:1px}
.new{display:inline-block;margin-left:6px;font-size:11px;color:#fff;background:var(--navy);border-radius:6px;padding:1px 6px;letter-spacing:0}
.ttl{font-size:16px;font-weight:700;line-height:1.4;margin-top:3px}
.sum{font-size:13px;color:var(--gray);line-height:1.5;margin-top:4px}
.tags{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}
.tag{font-size:11.5px;color:var(--gray);background:var(--bg-soft);border:1px solid var(--line);border-radius:6px;padding:1px 6px}
.none{display:none;text-align:center;color:var(--gray);font-size:14px;margin-top:24px}
</style></head><body><div class="wrap">
<span class="badge">매주 한 장</span>
<h1>@TITLE@</h1>
<p class="sub">@DESC@</p>
<input class="search" id="q" type="search" placeholder="찾기 — 예: 배당, 조세조약, 주재원">
<ul class="list" id="list">@ITEMS@</ul>
<p class="none" id="none">찾는 카드가 없습니다.</p>
<p class="foot">실무 참고용이며 개별 사안은 검토가 필요합니다.<br>카드마다 근거 확인 기준일이 적혀 있습니다.</p>
</div>
<script>
var q=document.getElementById('q'),items=[].slice.call(document.querySelectorAll('.item'));
q.addEventListener('input',function(){var v=q.value.trim().toLowerCase(),n=0;
items.forEach(function(li){var hit=!v||li.getAttribute('data-k').toLowerCase().indexOf(v)>=0;li.style.display=hit?'':'none';if(hit)n++;});
document.getElementById('none').style.display=n?'none':'block';});
</script>
</body></html>
"""

ITEM = """<li class="item" data-k="@KEY@"><a href="c/@NO@/">
<img src="c/@NO@/1.png" alt="" loading="lazy">
<div class="meta"><span class="no">카드 @NO@@NEW@</span><span class="ttl">@T@</span><span class="sum">@S@</span>
<span class="tags">@TAGS@</span></div></a></li>"""

VIEWER = """<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>@NO@ · @T@</title>
<meta property="og:type" content="article"><meta property="og:title" content="실무 카드 @NO@ · @T@">
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
<div class="bar"><span class="badge">외투법인 실무 카드 · @NO@</span><a class="home" href="../../">전체 카드 ›</a></div>
<div class="track" id="t">@IMGS@</div>
<div class="ctl"><button id="p" aria-label="이전">‹</button><span class="dots" id="d">@DOTS@</span><button id="n" aria-label="다음">›</button></div>
<p class="info">옆으로 넘겨 보세요 · 근거 확인 기준 @BASIS@</p>
<a class="next" href="../../">다른 카드 보기</a>
<p class="foot">실무 참고용이며 개별 사안은 검토가 필요합니다.</p>
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


def fill(tpl, **kw):
    for k, v in kw.items():
        tpl = tpl.replace("@" + k + "@", v)
    return tpl


def png_size(p):
    b = p.read_bytes()[:24]
    return int.from_bytes(b[16:20], "big"), int.from_bytes(b[20:24], "big")


def render(src, out_dir, count):
    out_dir.mkdir(parents=True, exist_ok=True)
    uri = src.as_uri()
    for i in range(1, count + 1):
        out = out_dir / f"{i}.png"
        if out.exists():
            out.unlink()
        subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=1", f"--window-size={W},{H}",
                        f"--screenshot={out}", f"{uri}#{i}"],
                       capture_output=True, timeout=60)
        time.sleep(0.3)


def main():
    conf = json.loads((ROOT / "cards.json").read_text(encoding="utf-8"))
    site, cards = conf["site"], conf["cards"]
    base = site["base_url"]
    esc = html.escape
    problems = []
    items = []
    latest = max(c["published"] for c in cards)

    for c in cards:
        no = c["no"]
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
        dots = "<i></i>" * count
        (out_dir / "index.html").write_text(fill(
            VIEWER, STYLE=STYLE, NO=no, T=esc(c["title"]), S=esc(c["summary"]),
            OGIMG=f"{base}c/{no}/1.png", URL=f"{base}c/{no}/", IMGS=imgs, DOTS=dots,
            BASIS=esc(c["basis_date"])), encoding="utf-8")
        key = " ".join([c["title"], c["summary"]] + c["tags"])
        items.append((c["published"], no, fill(
            ITEM, KEY=esc(key), NO=no, T=esc(c["title"]), S=esc(c["summary"]),
            NEW='<span class="new">새 카드</span>' if c["published"] == latest else "",
            TAGS="".join(f'<span class="tag">{esc(t)}</span>' for t in c["tags"]))))

    items.sort(reverse=True)
    newest = items[0][1]
    (ROOT / "index.html").write_text(fill(
        INDEX, STYLE=STYLE, TITLE=esc(site["title"]), DESC=esc(site["description"]),
        OGIMG=f"{base}c/{newest}/1.png", URL=base, ITEMS="".join(i[2] for i in items)), encoding="utf-8")
    (ROOT / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")

    print(f"카드 {len(cards)}개 처리")
    if problems:
        print("문제:", *problems, sep="\n  ")
        sys.exit(1)
    print("이미지 확인: 모두 1080x1350")


if __name__ == "__main__":
    main()
