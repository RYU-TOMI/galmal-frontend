# -*- coding: utf-8 -*-
"""고지 문구의 하한 — 제휴 `(광고)` 표식과 설명줄이 **읽히는가** (DESIGN.md §접근성, 2026-09-20 확정).

「고지이지 강조가 아니다」를 따르다 보니 글자가 9px · `opacity .85` 까지 내려가 있었다. 대비가
3.48:1 (`(광고)` 표식은 2.91:1) — WCAG AA 는 4.5:1 이다. 법적 고지는 「명확히 인식할 수 있게」가
조건이라 **약하게 하되 안 보이게 하면 안 된다.**

이 상태는 예외로 드러나지 않는다 — CSS 는 멀쩡히 적용되고 화면도 멀쩡해 보인다. 누가 「조금만 더
연하게」 하며 `opacity` 를 다시 넣어도 아무것도 안 깨진다. 그래서 여기서 잠근다:

  | | 하한 |
  |---|---|
  | 크기 | 12px 이상 (`.75rem`) |
  | 색 | `--sub` 그대로 · **`opacity` 없음** → `--card` 위 대비 4.5:1 이상 |
  | 강조 | 없음 — 코랄 · 굵게(700+) · 배경칠 금지 (중립성 결정 2026-08-06) |

탐침은 실제 `discover.css` 를 읽는다 — 가짜 CSS 로 검사하면 진짜 파일이 바뀌었을 때를 못 잡는다.

⚠️ **여기서 못 보는 것**: 부모 요소의 `opacity` 가 물려 내려오는 경우(정적 분석으론 DOM 을 모른다).
그건 화면에서 잰다 — `FRONTEND.md` §3 QA, 계산된 대비를 CDP 로.
"""
import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = io.open(os.path.join(ROOT, "public", "assets", "discover.css"), encoding="utf-8").read()

DISCLOSURE = [".cmp-ad", ".hc-ad"]      # (광고) 표식 · 설명줄(가격 신선도 고지도 이 줄)
MIN_PX = 12
MIN_CONTRAST = 4.5
ROOT_PX = 16                            # rem 기준 — discover.css 는 html font-size 를 안 바꾼다


def _rules(css):
    """[(선택자 목록, {속성: 값})]. `@media` 안의 규칙도 펼쳐서 같이 본다 — 모바일에서만 흐려져도 걸려야 한다."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = []
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        sel = sel.strip()
        if not sel or sel.startswith("@") or re.match(r"^(\d+%|from|to)\b", sel):
            continue
        props = {}
        for decl in body.split(";"):
            if ":" in decl:
                k, v = decl.split(":", 1)
                props[k.strip().lower()] = v.strip().lower()
        out.append(([s.strip() for s in sel.split(",")], props))
    return out


def _root_vars(css):
    m = re.search(r":root\s*\{([^}]*)\}", css)
    return dict((k.strip(), v.strip()) for k, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+)", m.group(1))) if m else {}


def _lum(hex_color):
    h = hex_color.lstrip("#")
    ch = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(fg, bg):
    a, b = _lum(fg), _lum(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def _px(value):
    m = re.match(r"^([\d.]+)(rem|px)$", value)
    if not m:
        return None
    return float(m.group(1)) * (ROOT_PX if m.group(2) == "rem" else 1)


def problems(css):
    """하한을 어긴 것의 문장 목록. 맞으면 빈 목록."""
    out = []
    rules = _rules(css)
    vars_ = _root_vars(css)

    for cls in DISCLOSURE:
        # 그 클래스를 **가리키는** 모든 규칙 — `.hovercard .hc-ad` · `@media` 안의 재정의까지.
        mine = [(sels, p) for sels, p in rules
                if any(re.search(r"%s(?![\w-])" % re.escape(cls), s) for s in sels)]
        if not mine:
            # 못 찾으면 통과가 아니라 실패다 — 이름이 바뀌면 「어긴 게 없다」로 읽히면 안 된다.
            out.append("%s 규칙을 discover.css 에서 못 찾았다 — 검사를 할 수 없으면 통과가 아니라 실패다" % cls)
            continue

        sizes = [p["font-size"] for _, p in mine if "font-size" in p]
        if not sizes:
            out.append("%s 에 font-size 가 없다 — 물려받은 크기는 여기서 보장할 수 없다" % cls)
        for v in sizes:
            px = _px(v)
            if px is None or px < MIN_PX:
                out.append("%s font-size %s — %dpx 미만이다" % (cls, v, MIN_PX))

        for _, p in mine:
            if "opacity" in p and p["opacity"] not in ("1", "1.0"):
                out.append("%s 에 opacity %s — 흐리게 하는 것도 「--sub 보다 옅은 회색」이다" % (cls, p["opacity"]))
            if "filter" in p and "opacity" in p["filter"]:
                out.append("%s 에 filter %s — opacity 의 우회다" % (cls, p["filter"]))
            if any(k in p for k in ("background", "background-color")):
                out.append("%s 에 배경칠 — 강조 금지" % cls)
            w = p.get("font-weight", "")
            if w == "bold" or (w.isdigit() and int(w) >= 700):
                out.append("%s font-weight %s — 굵게 금지" % (cls, w))

        colors = [p["color"] for _, p in mine if "color" in p]
        if not colors:
            out.append("%s 에 color 가 없다 — 물려받은 색은 여기서 보장할 수 없다" % cls)
        for v in colors:
            if v != "var(--sub)":
                out.append("%s color %s — `--sub` 그대로여야 한다(코랄·더 옅은 회색 금지)" % (cls, v))

    sub, card = vars_.get("--sub"), vars_.get("--card")
    if not sub or not card:
        out.append(":root 에서 --sub / --card 를 못 읽었다")
    else:
        cr = contrast(sub, card)
        if cr < MIN_CONTRAST:
            out.append("--sub(%s) on --card(%s) 대비 %.2f:1 — %.1f 미만이다" % (sub, card, cr, MIN_CONTRAST))
    return out


class DisclosureTest(unittest.TestCase):

    def test_real_css_meets_the_floor(self):
        self.assertEqual(problems(CSS), [])

    def test_contrast_formula_is_the_wcag_one(self):
        """자가 검증 — 검정/흰색은 21:1, 기획이 잰 `--sub` on 흰색은 4.61:1."""
        self.assertAlmostEqual(contrast("#000000", "#FFFFFF"), 21.0, places=1)
        self.assertAlmostEqual(contrast("#5E7A7C", "#FFFFFF"), 4.61, places=2)

    def test_opacity_creeping_back_is_caught(self):
        """탐침 — 예전 값 그대로 되돌리면 잡힌다. 이게 실제로 있었던 상태다."""
        old = CSS.replace(".cmp-ad{font-weight:600;font-size:.75rem;color:var(--sub);",
                          ".cmp-ad{font-weight:600;font-size:.64rem;color:var(--sub);opacity:.75;")
        self.assertNotEqual(old, CSS, "탐침이 아무것도 안 바꿨다 — CSS 모양이 달라졌으면 탐침을 고친다")
        bad = problems(old)
        self.assertTrue(any("opacity" in b and ".cmp-ad" in b for b in bad))
        self.assertTrue(any("12px 미만" in b and ".cmp-ad" in b for b in bad))

    def test_override_elsewhere_is_caught(self):
        """탐침 — 본 규칙은 멀쩡한데 **다른 규칙이** 흐리게 해도 잡는다(모바일 `@media` 안 포함)."""
        self.assertTrue(any("opacity" in b for b in problems(CSS + "\n.hovercard .hc-ad{opacity:.8}")))
        self.assertTrue(any("12px 미만" in b for b in
                            problems(CSS + "\n@media(max-width:860px){.hc-ad{font-size:.6rem}}")))

    def test_emphasis_is_caught(self):
        """반대 방향 — 읽히게 한다고 강조하면 중립성 결정을 깬다."""
        self.assertTrue(any("굵게" in b for b in problems(CSS + "\n.cmp-ad{font-weight:800}")))
        self.assertTrue(any("--sub" in b for b in problems(CSS + "\n.cmp-ad{color:var(--accent)}")))
        self.assertTrue(any("배경칠" in b for b in problems(CSS + "\n.hc-ad{background:#FFF3EF}")))

    def test_lighter_sub_token_is_caught(self):
        """탐침 — 클래스는 그대로 두고 `--sub` 토큰 자체를 옅게 바꿔도 잡는다."""
        lighter = CSS.replace("--sub:#5E7A7C", "--sub:#8FA6A8")
        self.assertNotEqual(lighter, CSS)
        self.assertTrue(any("대비" in b for b in problems(lighter)))

    def test_missing_rule_is_failure_not_pass(self):
        """이름이 바뀌어 규칙을 못 찾으면 「어긴 게 없다」로 읽히면 안 된다."""
        renamed = CSS.replace(".hc-ad{", ".hc-notice{")
        self.assertTrue(any(".hc-ad" in b and "못 찾았다" in b for b in problems(renamed)))


if __name__ == "__main__":
    unittest.main()
