# galmal-frontend — 프론트 세션

@../galmal-plan/SESSIONS.md

> 위 한 줄이 **세 세션 공통 규칙**을 가져온다(형제 폴더 `../galmal-plan/`). 가져오기가 안 되면 그 파일을 **먼저 직접 읽는다.**
> 이 파일에는 **이 저장소만의 규칙**을 둔다. 작업 방식·챕터 로드맵은 `FRONTEND.md`, 곁가지는 `BACKLOG.md`.

## 이 저장소

v1 API를 받아 **화면을 굽는다** — 발견 지도·카드·필터·노선 페이지·SEO. 배포는 **`https://galmal.kr`**.
데이터 로직(수집·판정)은 없다. 받는 쪽이다.

| 경로 | 무엇 |
|---|---|
| `site/` | 화면 빌드 — 진입점 **`site/build.py`** |
| `public/` | 정적 자산(`assets/` JS·CSS·벤더 `d3-*` · `data/world.geojson`). 빌드가 그대로 복사한다 |
| `fixtures/v1/` | 라이브에서 받아 적은 v1 사본(한 발행분, 40개) — **손으로 고치지 않는다** |
| `tests/` | 단위 테스트 |

## 빌드
```bash
python site/build.py --api https://api.galmal.kr/v1 --out dist          # 라이브 API로
python site/build.py --api fixtures/v1 --out dist                        # 네트워크 없이 픽스처로
python -m http.server 8000 --directory dist                              # 확인
```
- 빌드는 받은 v1 응답 전부의 `generated`가 한 스냅숏인지 검사하고(`galmal-plan/CONTRACT.md` §공통 규칙), 어긋나면 **한 파일도 쓰기 전에** 실패한다(T6d).
- 검사를 끄는 옵션은 **없다.** 픽스처도 한 발행분으로 받아 적으므로(`python fixtures/capture.py https://api.galmal.kr/v1`) 같은 검사를 받는다.
- 테스트: `python -m unittest discover -s tests -v` — **출력에서 `^OK`를 확인**하고 커밋한다.

## 배포 (`.github/workflows/deploy.yml`)
- 트리거: `main` push(`.md`만 바뀐 커밋은 제외) · 백엔드의 `repository_dispatch`(`api-updated`, `client_payload.generated`와 대조) · 수동.
- 커스텀 도메인 `galmal.kr`은 Pages 설정에 저장된다 — Actions 배포라 `CNAME` 파일은 필요 없다(재배포 후 유지 실측).
- 사이트에 `build.json`(`api_generated`)을 함께 낸다 — 백엔드 크론이 그걸로 「사이트가 뒤처졌나」를 본다. **지우지 않는다.**

## 계약 소비
- 계약 정본은 `galmal-backend/contract/v1/`. **임계(보여줘도 되나)는 프론트가 정하고, 창(어느 기간을 보나)은 백엔드가 정한다.**
- **어휘는 `/v1/vocab.json`에서 받는다**(CONTRACT §5). 손 사본은 없다 — 분위기 칩·날짜 어휘 칩은 `site/home.py`가 vocab으로 그리고,
  `discover.js`의 `TAG_TOP`·`WHEN_CHIPS`는 **그 칩에서 읽는다**(날짜 칩은 `data-when` 표식이 있는 것만). 지역 표시명은 `vocab.region_name`.
- 빌드가 막는 것 둘 — ① 그려진 칩 ≠ 계약(순서까지) `home.chip_problems` ② 어휘 키 매핑 `TAG_GRAD`·`HAUL2STAGE`가 어휘를 못 덮음 `site/coverage.py`.
  새 태그·새 haul이 생기면 **빌드가 멈춘다** — 그때 매핑에 색·단계를 정해 넣는다(색은 `DESIGN.md` 소관).

## git
- `main`에 크론 커밋이 없다. 작게 자주 커밋하면 push마다 배포된다 — **배포되는 것**이라는 걸 기억한다.
