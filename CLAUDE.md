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
| `fixtures/v1/` | 기준선에서 받아 적은 v1 사본 — **손으로 고치지 않는다** |
| `tests/` | 단위 테스트 |

## 빌드
```bash
python site/build.py --api https://api.galmal.kr/v1 --out dist          # 라이브 API로
python site/build.py --api fixtures/v1 --out dist --no-snapshot-check    # 네트워크 없이 픽스처로
python -m http.server 8000 --directory dist                              # 확인
```
- 빌드는 받은 v1 응답 전부의 `generated`가 한 스냅숏인지 검사하고(`galmal-plan/CONTRACT.md` §공통 규칙), 어긋나면 **한 파일도 쓰기 전에** 실패한다(T6d).
- ⚠️ `--no-snapshot-check`는 **픽스처 빌드에만** 쓴다 — 기준선 픽스처는 그 규칙이 생기기 전 것이라 위반한다. 다른 경로에 번지면 검사가 무력해진다. 픽스처를 새로 받아 적는 날 지운다.
- 테스트: `python -m unittest discover -s tests -v` — **출력에서 `^OK`를 확인**하고 커밋한다.

## 배포 (`.github/workflows/deploy.yml`)
- 트리거: `main` push(`.md`만 바뀐 커밋은 제외) · 백엔드의 `repository_dispatch`(`api-updated`, `client_payload.generated`와 대조) · 수동.
- 커스텀 도메인 `galmal.kr`은 Pages 설정에 저장된다 — Actions 배포라 `CNAME` 파일은 필요 없다(재배포 후 유지 실측).
- 사이트에 `build.json`(`api_generated`)을 함께 낸다 — 백엔드 크론이 그걸로 「사이트가 뒤처졌나」를 본다. **지우지 않는다.**

## 계약 소비
- 계약 정본은 `galmal-backend/contract/v1/`. **임계(보여줘도 되나)는 프론트가 정하고, 창(어느 기간을 보나)은 백엔드가 정한다.**
- ⚠️ **알려진 손 사본**(참조 데이터 v1 발행 과제에서 없앤다): `TAG_TOP` · 분위기 칩 · `WHEN_CHIPS` · 날짜 칩 · `site/route.py` `REGION_NAME`.
  어휘 키 매핑 `TAG_GRAD` · `HAUL2STAGE`는 남기되 빌드 타임 포괄 검사로 잠근다. 그 전까진 어휘가 바뀌면 이 목록부터 본다.

## git
- `main`에 크론 커밋이 없다. 작게 자주 커밋하면 push마다 배포된다 — **배포되는 것**이라는 걸 기억한다.
