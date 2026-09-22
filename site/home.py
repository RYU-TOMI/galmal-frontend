# -*- coding: utf-8 -*-
"""발견 홈(docs/index.html) 렌더러 — 지도+피드+필터 도크 셸.

데이터(deals.json)·지도(world.geojson)를 인라인해 file://에서도 열린다.
스타일은 assets/discover.css, 로직은 assets/discover.js.

**`collector/discover_home.py` 에서 인수했다**(레포 분리, SPLIT.md M2).
이 파일은 원래도 프론트 소유였는데 `labels`·`theme`(백엔드 모듈)을 import 하는
**경계 역행** 상태였다. 이제 `shell`(프론트) 만 본다.

노선 이름은 `city(코드)` 로 뽑던 것을 계약이 주는 `o_name`·`d_name` 으로 바꿨다 —
표시명은 참조 데이터라 백엔드가 준다(`CONTRACT.md` §v1).
"""
import html
import json

from shell import BASE_URL, OG_IMAGE, SITE_NAME, logo, verification_meta

# 로고는 `shell.logo()` 가 그린다 — 모든 페이지가 같은 함수를 쓴다(DESIGN.md §로고, B53).
# 예전엔 같은 기하를 여기 손으로 옮겨 적은 사본이 있었다(각도 `-28.6` 을 숫자로). 지금 출력은 그 사본과 바이트까지 같다.
# `gid` 는 SVG 그라디언트 id — 예전 값을 그대로 둬서 홈 HTML 이 한 글자도 안 바뀐다.
HOME_LOGO_GID = "gmlg"

_FILTER_DOCK = """
    <div class="filterdock" id="fdock">
      <button type="button" class="fdtoggle" id="fdtoggle"><span id="fdsum">필터</span><i>▾</i></button>
      <div class="fdbody">
        <div class="fdrow"><span class="fdlabel">언제 갈래요?</span>
          <div class="chips">
            <button type="button" class="fchip date on" data-date="">아무때</button>
@@WHEN_FIXED@@
            <button type="button" class="fchip date" data-date="rest">그 이후<i></i></button>
            <button type="button" class="fchip date" data-date="custom">날짜 지정</button>
          </div>
          <div class="customdates" id="customdates">
            <input type="date" id="cdStart"><span>~</span><input type="date" id="cdEnd">
          </div></div>
        <div class="fdrow"><span class="fdlabel">며칠 갈래요?</span>
          <div class="chips">
            <button type="button" class="fchip nights on" data-nights="">상관없어</button>
            <button type="button" class="fchip nights" data-nights="1-3">1~3박<i></i></button>
            <button type="button" class="fchip nights" data-nights="4-6">4~6박<i></i></button>
            <button type="button" class="fchip nights" data-nights="7-13">7~13박<i></i></button>
            <button type="button" class="fchip nights" data-nights="14+">2주 이상<i></i></button>
          </div></div>
        <div class="fdrow"><span class="fdlabel">분위기</span>
          <div class="chips">
@@MOODS@@
          </div></div>
        <div class="fdrow"><span class="fdlabel">예산</span>
          <div class="budgetwrap">
            <div class="btrack"><div class="bhist" id="bhist" aria-hidden="true"></div><input id="budget" type="range" min="100000" max="1000000" step="50000" value="1000000"></div>
            <b id="budgetVal">제한 없음</b></div>
          <div class="chips">
            <button type="button" class="fchip budget" data-budget="300000">30만<i></i></button>
            <button type="button" class="fchip budget" data-budget="500000">50만<i></i></button>
            <button type="button" class="fchip budget" data-budget="1000000">100만<i></i></button>
            <button type="button" class="fchip budget on" data-budget="">상관없어</button>
          </div></div>
      </div>
    </div>"""


def filter_dock(vocab):
    """필터 도크. **어휘 칩은 `/v1/vocab.json` 에서 만든다**(CONTRACT §5).

    예전엔 분위기 칩 6개·날짜 칩 5개를 여기 손으로 적었다. 백엔드가 어휘를 바꾸면 칩은 옛
    이름으로 남고 **필터가 조용히 0건**이 됐다. 이제 목록은 한 곳(계약)에서만 온다.

    - 분위기 칩 = `tags.top` **순서 그대로**(필터 칩 순서라는 게 계약에 적힌 뜻이다)
    - 날짜 칩 중 고정값 = `when.fixed` 순서 그대로. **`data-when` 표식을 단다** —
      `discover.js` 가 이 표식으로 어휘 칩만 골라 읽는다. 「아무때」·「그 이후」·「날짜 지정」은
      **화면 전용 칩**이라 어휘가 아니고 표식도 없다. 제외 목록을 JS 에 두면 그게 또 하나의
      손 사본이 되고, 화면 전용 칩이 늘 때 어휘로 잘못 읽힌다 — 표식이면 새 칩은 저절로 빠진다.

    `discover.js` 의 `TAG_TOP`·`WHEN_CHIPS` 는 **이 칩에서 읽는다.** 그래서 빌드가 이 칩이
    계약과 같은지 확인한다(`build.py` — 틀리면 배포하지 않는다).
    """
    esc = lambda x: html.escape(x, quote=True)
    ind = "            "
    when = "\n".join(
        ind + '<button type="button" class="fchip date" data-date="%s" data-when>%s<i></i></button>'
        % (esc(w), esc(w)) for w in vocab["when"]["fixed"])
    moods = "\n".join(
        ind + '<button type="button" class="fchip moodf" data-mood="%s">%s<i></i></button>'
        % (esc(t), esc(t)) for t in vocab["tags"]["top"])
    return _FILTER_DOCK.replace("@@WHEN_FIXED@@", when).replace("@@MOODS@@", moods)


def chip_problems(page_html, vocab):
    """그려진 홈의 어휘 칩이 계약과 **순서까지** 같은지. 틀리면 문장 목록, 맞으면 빈 목록.

    `discover.js` 는 `TAG_TOP`·`WHEN_CHIPS` 를 **이 칩에서 읽는다.** 칩이 비거나 모자라면
    `TAG_TOP = []` → 모든 태그가 하위로 분류 → **카드 태그가 조용히 틀린다.**
    런타임 경고는 아무것도 멈추지 않으므로 빌드가 막는다.
    """
    import re
    got_mood = [html.unescape(x) for x in re.findall(
        r'class="fchip moodf" data-mood="([^"]*)"', page_html)]
    got_when = [html.unescape(x) for x in re.findall(
        r'class="fchip date" data-date="([^"]*)" data-when>', page_html)]
    out = []
    if got_mood != vocab["tags"]["top"]:
        out.append("분위기 칩 %s != tags.top %s" % (got_mood, vocab["tags"]["top"]))
    if got_when != vocab["when"]["fixed"]:
        out.append("날짜 어휘 칩 %s != when.fixed %s" % (got_when, vocab["when"]["fixed"]))
    return out


def render_home(payload, deals_json, world_json, index, vocab):
    # `generated`(ISO 8601 + 오프셋) -> 화면 문자열. 표시는 프론트 몫이라고 계약이
    # 명시한 자리다(P7). 현행 `updated` 와 같은 모양 `YYYY-MM-DD HH:MM` 을 만든다.
    updated = html.escape(payload["generated"][:16].replace("T", " "))
    deals = payload.get("deals", [])
    top = sorted(deals, key=lambda x: x["price"])[:30]
    # 딜 0건인 날의 대안. **그날 발견 홈이 줄 게 없어도 노선 시세는 살아 있다.** (SPEC §CH3 F1)
    # JS 는 노선 목록을 갖고 있지 않으므로 셸에서 만든다.
    empty_routes = "".join(
        f'<a class="rlink" href="{BASE_URL}/routes/{r["code"]}.html">'
        f'{html.escape(r["o_name"])} → {html.escape(r["d_name"])}</a>'
        for r in index["routes"][:8])
    ns_deals = "\n".join(
        f"      <li>{html.escape(d['ko'])} · {d['price']:,}원~ · {html.escape(d['when'])} 출발</li>"
        for d in top) or "      <li>수집된 특가가 아직 없습니다.</li>"
    ns_routes = "\n".join(
        f'      <li><a href="{BASE_URL}/routes/{r["code"]}.html">{html.escape(r["o_name"])} → '
        f'{html.escape(r["d_name"])} 최저가 분석</a></li>'
        for r in index["routes"])

    title = f"{SITE_NAME} — 어디, 갈까? 항공권 특가 발견 지도"
    desc = ("시간 남는데 어디 싸게 갈까? 한국 출발 항공권을 매일 스캔해 지도에서 "
            "오늘 싼 여행지를 골라줍니다. 목적지를 정해주는 발견 서비스.")
    # 공유 카드(OG) — `<title>`·`description`을 재사용하지 않는다. 자리가 다르다. (COPY.md §2c)
    #   `<title>`은 **검색 결과**에 뜬다 → 검색어가 들어간다.
    #   `og:title`은 **카톡 말풍선**이다 → 이미 아는 사람이 친구에게 보내는 자리라 태그라인만 쓴다.
    #   `og:description`은 위 74자를 그대로 못 쓴다 — 카톡이 두 줄쯤에서 자른다.
    og_title = f"{SITE_NAME} — 어디, 갈까?"
    og_desc = ("시간 남는데 싸게 다녀올 곳. 한국 출발 항공권을 매일 스캔해 "
               "오늘 싼 여행지를 지도에 펼칩니다.")

    scripts = (
        f"<script>window.__DEALS={deals_json};</script>\n"
        f"<script>window.__WORLD={world_json};</script>\n"
        '<script src="assets/d3-array.min.js"></script>\n'
        '<script src="assets/d3-geo.min.js"></script>\n'
        '<script src="assets/discover.js"></script>'
    )

    return f"""<!doctype html><html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{BASE_URL}/">
{verification_meta()}<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{og_desc}">
<meta property="og:url" content="{BASE_URL}/">
<meta property="og:locale" content="ko_KR">
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{SITE_NAME} — 어디, 갈까? 세계 지도에 오늘 싼 여행지가 찍혀 있다">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link rel="stylesheet" href="assets/discover.css">
</head><body>
<div class="hdr">
  {logo(gid=HOME_LOGO_GID)}
  <span class="nav"><span class="on">발견</span><span class="muted">노선별</span></span>
  <span class="tools"><span class="originwrap">
    <button type="button" class="pill origin" id="originPill" aria-haspopup="listbox" aria-expanded="false">출발지 ▾</button>
    <div class="origindrop" id="originDrop" role="listbox" hidden></div>
  </span></span>
</div>
<div class="firstnote" id="firstnote" hidden>
  <span id="fnText"></span>
  <button type="button" class="fn-go" id="fnChange">바꾸기</button>
  <button type="button" class="fn-x" id="fnClose" aria-label="이 안내 닫기">×</button>
</div>
<div class="layout">
  <div class="feed" id="feed"></div>
  <div class="stage">
    <svg class="map" id="map" preserveAspectRatio="xMidYMid slice" role="img" aria-label="여행지 발견 지도">
      <g id="lands"></g><path id="arc" class="arc" d=""/><g id="origin"></g><g id="pins"></g>
    </svg>
    <div class="prompt"><b>카드에 올리면</b> 지도에 항로가 · <b>핀 클릭</b>하면 상세가 열려요</div>
    <div class="stagebar"><span class="pill on">가까운 곳</span><span class="pill">조금 더 멀리</span><span class="pill">아주 멀리</span></div>
    <div class="stepper" id="stepper">
      <button type="button" data-step="out" aria-label="더 멀리" title="더 멀리"><i>＋</i><em>더 멀리</em></button>
      <button type="button" data-step="in" aria-label="가까이" title="가까이"><i>－</i><em>가까이</em></button>
    </div>{filter_dock(vocab)}
    <div class="hovercard" id="hc"></div>
    <div class="emptyday" id="emptyday" hidden>
      <h2>오늘은 조용하네요</h2>
      <p>수집한 특가가 없어요. 내일 아침에 다시 채워집니다.</p>
      <p class="ed-alt">노선별 최저가는 그대로 볼 수 있어요</p>
      <div class="rlinks">{empty_routes}</div>
    </div>
  </div>
</div>
<noscript>
  <div class="noscript-fallback">
    <p class="ns-note">JavaScript가 꺼져 있어 지도를 표시하지 못했습니다. 오늘의 특가와 노선별 분석은 아래에서 볼 수 있어요. (갱신 {updated})</p>
    <h2>오늘의 특가</h2>
    <ul>
{ns_deals}
    </ul>
    <h2>노선별 최저가 분석</h2>
    <ul>
{ns_routes}
    </ul>
  </div>
</noscript>
{scripts}
</body></html>"""


def inline_deals(payload):
    """`window.__DEALS` 에 박을 JSON 문자열.

    🔴 **이전용 어댑터다. 영구 코드가 아니다.**

    v1 봉투는 `{schema, generated, origins, deals}` 인데 현행 인라인은 `{updated, origins, deals}` 다.

    🔴 **2026-09-22 부터 `discover.js` 가 `updated` 를 읽는다**(C-15 — 피드 헤드의 `· 07:23 기준`).
    예전 주석은 「`updated` 는 안 본다(실측 0회)」였는데 **더 이상 사실이 아니다.** 그래서 이 어댑터는
    이전용이 아니라 **화면이 쓰는 값을 만드는 자리**가 됐다 — 없애려면 `discover.js` 가 `generated` 를
    직접 읽도록 같이 고쳐야 한다(`updated` 는 오프셋을 버린 KST 벽시계라 모양이 다르다).

    그런데도 현행 바이트를 재현하는 이유는 **M2 T5 의 증명을 흐리지 않기 위해서다.**
    봉투만 바꿔도 `index.html` 은 크게 diff 가 나고, 그러면 「화면은 같다」를
    사람이 눈으로 판정해야 한다. 바이트가 같으면 판정할 게 없다.

    직렬화 인자는 현행과 같아야 한다(`discover_data.py:290`) —
    `ensure_ascii=False, separators=(",", ":")`. 다르면 같은 데이터라도 바이트가 달라진다.

    **없앨 조건**: `discover.js` 가 `generated` 를 직접 읽게 되면 이 함수를 지우고 v1 봉투를 그대로 박는다.
    그때 **C-15 의 날짜 계산도 같이 옮겨야 한다**(오프셋이 붙은 `generated` 를 KST 로 읽는 코드로).
    """
    legacy = {"updated": payload["generated"][:16].replace("T", " "),
              "origins": payload["origins"],
              "deals": payload["deals"]}
    return json.dumps(legacy, ensure_ascii=False, separators=(",", ":"))
