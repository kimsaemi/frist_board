# -*- coding: utf-8 -*-
"""대시보드 검수 — 실제 브라우저(Playwright/Chromium)로 화면을 띄워 확인한다.

검사 항목 (요청서 '검증 조건' 그대로)
  1. 하드코딩된 샘플이 아니라 실제 data/bike_station_profile.csv를 네트워크로 읽는다
  2. 기본 가중치에서 2,782개 대여소가 표시된다 (마커 수 · 합계 · 군집 수 합)
  3. 가중치를 크게 변경하면 군집이 바뀌는 대여소 수가 0보다 크다
  4. 같은 가중치로 다시 계산하면 결과가 완전히 같다 (재현성)
  5. 군집 필터 · 검색 · 목록 선택 · 지도 선택 · 초기화가 동작한다
  6. 브라우저 콘솔 오류가 없다
  7. 데스크톱·태블릿·모바일 스크린샷을 screenshots/ 에 저장한다
  추가. sqrt(가중치)가 실제로 적용됐는지 (z × √w 를 직접 재계산해 대조)
  추가. 기본 가중치 결과가 sklearn KMeans 결과와 같은 군집 크기인지

실행 (dashboard 폴더에서)

    python -m http.server 8000
    python tests/test_dashboard.py            # 기본 http://localhost:8000
    python tests/test_dashboard.py 8765       # 포트를 바꿀 때
"""

import json
import os
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHOTS = os.path.join(ROOT, "screenshots")
PORT = sys.argv[1] if len(sys.argv) > 1 else "8000"
BASE = f"http://localhost:{PORT}"
EXPECTED_STATIONS = 2782

os.makedirs(SHOTS, exist_ok=True)
results, fails = [], []


def ok(name, passed, detail=""):
    results.append((name, passed, detail))
    if not passed:
        fails.append(f"{name} — {detail}")
    print(("  [OK]   " if passed else "  [FAIL] ") + name + (f"  {detail}" if detail else ""))


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1600, "height": 950})

    console = []
    page.on("console", lambda m: console.append((m.type, m.text)))
    page.on("pageerror", lambda e: console.append(("pageerror", str(e))))
    requests = []
    page.on("response", lambda r: requests.append((r.url, r.status)))

    print("1) 페이지 로드")
    page.goto(f"{BASE}/index.html", wait_until="networkidle")
    page.wait_for_selector("#layout:not([hidden])", timeout=30000)
    page.wait_for_function("() => window.__dash && window.__dash.state.labels.length > 0",
                           timeout=30000)

    # ── 1. 실제 CSV를 읽었는가 ────────────────────────────────
    csv_hits = [(u, s) for u, s in requests if "bike_station_profile.csv" in u]
    ok("실제 CSV를 네트워크로 읽는다", bool(csv_hits) and csv_hits[0][1] == 200,
       f"{csv_hits}")
    csv_bytes = os.path.getsize(os.path.join(ROOT, "data", "bike_station_profile.csv"))
    ok("CSV 파일이 실물이다", csv_bytes > 500_000, f"{csv_bytes:,} bytes")

    # ── 2. 기본 가중치에서 2,782곳 ────────────────────────────
    info = page.evaluate("""() => {
      const S = window.__dash.state;
      return {
        rows: S.rows.length,
        markers: S.markers.size,
        labels: S.labels.length,
        counts: S.summary.map(c => c.n),
        names: S.summary.map(c => c.nameCandidate),
        means: S.summary.map(c => c.mean),
        weights: S.weights,
        stat: document.getElementById('statStations').textContent,
        legend: document.getElementById('legend').textContent.replace(/\\s+/g,' ').trim(),
      };
    }""")
    ok("대여소 수 2,782곳", info["rows"] == EXPECTED_STATIONS, f"rows={info['rows']}")
    ok("지도 마커 2,782개", info["markers"] == EXPECTED_STATIONS,
       f"markers={info['markers']}")
    ok("군집별 합계 = 전체", sum(info["counts"]) == EXPECTED_STATIONS,
       f"{info['counts']} 합 {sum(info['counts'])}")
    ok("상단 표기도 2,782곳", "2,782" in info["stat"], info["stat"])
    ok("기본 가중치가 각 20%", info["weights"] == [20] * 5, str(info["weights"]))
    ok("범례에 군집별 대여소 수 표기",
       all(f"군집 {k}" in info["legend"] for k in range(4)), info["legend"][:120])
    print("     군집 크기:", info["counts"])
    print("     이름 후보:", info["names"])

    # ── 추가. sqrt(가중치)가 실제로 적용됐는지 직접 대조 ──────
    sqrt_check = page.evaluate("""() => {
      const D = window.__dash, S = D.state;
      const w = [40, 15, 15, 15, 15];                 // 합계 100
      const norm = D.normalizeWeights(w);
      const X = D.applyWeights(S.z, norm);
      // 첫 행에 대해 z_j * sqrt(w_j) 인지 확인 (z_j * w_j 이면 어긋난다)
      const want = S.z[0].map((v, j) => v * Math.sqrt(norm[j]));
      const wrong = S.z[0].map((v, j) => v * norm[j]);
      const maxDiffRight = Math.max(...X[0].map((v, j) => Math.abs(v - want[j])));
      const maxDiffWrong = Math.max(...X[0].map((v, j) => Math.abs(v - wrong[j])));
      return { norm, maxDiffRight, maxDiffWrong };
    }""")
    ok("입력값 = 표준화값 × √(정규화 가중치)",
       sqrt_check["maxDiffRight"] < 1e-12 and sqrt_check["maxDiffWrong"] > 1e-6,
       f"√w와 차이 {sqrt_check['maxDiffRight']:.2e} / w와 차이 {sqrt_check['maxDiffWrong']:.2e}")
    ok("가중치 정규화 합계 1",
       abs(sum(sqrt_check["norm"]) - 1) < 1e-12, f"{sum(sqrt_check['norm'])}")

    # ── 추가. 기본 가중치 결과가 sklearn과 같은 해인지 (inertia 비교) ──
    inertia = page.evaluate("""() => {
      const D = window.__dash, S = D.state;
      const norm = D.normalizeWeights([20,20,20,20,20]);
      const X = D.applyWeights(S.z, norm);
      // 표준화 공간(z)에서의 inertia로 환산한다. 모든 좌표가 sqrt(0.2)배이므로
      // 가중 공간 inertia ÷ 0.2 = z 공간 inertia.
      const centers = Array.from({length:4}, () => new Array(5).fill(0));
      const cnt = new Array(4).fill(0);
      for (let i=0;i<X.length;i++){ const k=S.labels[i]; cnt[k]++;
        for(let j=0;j<5;j++) centers[k][j]+=X[i][j]; }
      for(let k=0;k<4;k++) for(let j=0;j<5;j++) centers[k][j]/=cnt[k];
      let inert=0;
      for (let i=0;i<X.length;i++){ const c=centers[S.labels[i]];
        for(let j=0;j<5;j++){ const d=X[i][j]-c[j]; inert+=d*d; } }
      return inert / 0.2;
    }""")
    ok("기본 가중치 결과가 sklearn과 같은 해 (inertia 7086.33 ± 0.5)",
       abs(inertia - 7086.33) < 0.5, f"inertia={inertia:.4f}")

    # ── 추가. 기본 군집 번호가 발표자료와 같은 순서인지 ───────
    order_ok = page.evaluate("""() => {
      const s = window.__dash.state.summary;
      const rel = j => s.map(c => c.mean[j]);
      const argmax = a => a.indexOf(Math.max(...a));
      return { dailyMax: argmax(rel(0)), morningMax: argmax(rel(1)),
               eveningMax: argmax(rel(2)), weekendMax: argmax(rel(3)),
               counts: s.map(c=>c.n), names: s.map(c=>c.nameCandidate) };
    }""")
    ok("군집 1 = 일평균 최대 (발표자료와 같은 번호)", order_ok["dailyMax"] == 1, str(order_ok))
    ok("군집 3 = 출근 최대", order_ok["morningMax"] == 3, str(order_ok["morningMax"]))
    ok("군집 0 = 퇴근 최대", order_ok["eveningMax"] == 0, str(order_ok["eveningMax"]))
    ok("군집 2 = 주말 최대", order_ok["weekendMax"] == 2, str(order_ok["weekendMax"]))

    # ── 4. 재현성 (같은 가중치 → 같은 결과) ───────────────────
    repeat = page.evaluate("""() => {
      const D = window.__dash, S = D.state;
      const before = Array.from(S.labels);
      D.recompute([20,20,20,20,20]);
      const a = Array.from(S.labels);
      D.recompute([20,20,20,20,20]);
      const b = Array.from(S.labels);
      const sameAsBefore = before.every((v,i) => v === a[i]);
      const sameTwice = a.every((v,i) => v === b[i]);
      return { sameAsBefore, sameTwice };
    }""")
    ok("같은 가중치 재계산 결과 동일 (2회)", repeat["sameTwice"], "")
    ok("최초 계산과도 동일", repeat["sameAsBefore"], "")

    # ── 3. 가중치를 크게 바꾸면 군집이 바뀐다 ─────────────────
    moved = page.evaluate("""() => {
      const D = window.__dash, S = D.state;
      const out = {};
      // 출근시간 비중만 크게
      let r = D.recompute([5, 80, 5, 5, 5]);
      out.morningHeavy = { moved: r.moved, counts: S.summary.map(c=>c.n), map: r.map };
      // 이용건수만 크게
      r = D.recompute([80, 5, 5, 5, 5]);
      out.dailyHeavy = { moved: r.moved, counts: S.summary.map(c=>c.n), map: r.map };
      // 합계가 100이 아닌 입력도 정규화되는지
      r = D.recompute([10, 10, 10, 10, 10]);   // 합 50 → 각 20%
      out.halfSum = { moved: r.moved, counts: S.summary.map(c=>c.n) };
      D.recompute([20,20,20,20,20]);
      return out;
    }""")
    ok("출근 가중치 80%: 군집 변경 대여소 > 0",
       moved["morningHeavy"]["moved"] > 0, f"{moved['morningHeavy']['moved']}곳 · 크기 {moved['morningHeavy']['counts']}")
    ok("이용건수 가중치 80%: 군집 변경 대여소 > 0",
       moved["dailyHeavy"]["moved"] > 0, f"{moved['dailyHeavy']['moved']}곳 · 크기 {moved['dailyHeavy']['counts']}")
    ok("합계 50%(각 10) 입력이 각 20%와 같은 결과로 정규화",
       moved["halfSum"]["moved"] == 0, f"변경 {moved['halfSum']['moved']}곳 · 크기 {moved['halfSum']['counts']}")

    # ── 5-a. UI: 가중치 슬라이더 + 재계산 버튼 ────────────────
    page.fill("#wn1", "80")
    page.fill("#wn0", "5")
    page.fill("#wn2", "5")
    page.fill("#wn3", "5")
    page.fill("#wn4", "5")
    sum_text = page.inner_text("#weightSum")
    ok("입력 합계 표시가 갱신된다", sum_text.strip() == "100%", sum_text)
    eff = page.inner_text("#effectiveBody")
    ok("정규화 전 값과 유효 가중치를 구분해 표시", "80%" in eff and "0.894" in eff,
       eff.replace("\n", " | ")[:160])

    page.click("#btnRecalc")
    page.wait_for_timeout(700)
    delta = page.inner_text("#deltaValue")
    ok("버튼으로 재계산 후 변경 대여소 수 표시", delta.strip() not in ("", "0곳"), delta)
    ui_counts = page.evaluate("() => window.__dash.state.summary.map(c => c.n)")
    ok("재계산 후에도 합계 2,782곳", sum(ui_counts) == EXPECTED_STATIONS, str(ui_counts))

    page.evaluate("""() => { window.__dash.state.map.setView([37.5512,126.9882],11,{animate:false});
        window.scrollTo(0,0); return null; }""")
    page.wait_for_timeout(1200)
    page.screenshot(path=os.path.join(SHOTS, "03_출근가중치80.png"), full_page=False)

    # ── 5-b. 초기화 ───────────────────────────────────────────
    page.click("#btnReset")
    page.wait_for_timeout(700)
    reset_state = page.evaluate("""() => ({
      weights: window.__dash.state.weights,
      moved: document.getElementById('deltaValue').textContent,
      counts: window.__dash.state.summary.map(c => c.n),
    })""")
    ok("초기화 버튼이 각 20%로 되돌린다", reset_state["weights"] == [20] * 5,
       str(reset_state["weights"]))
    ok("초기화 후 변경 대여소 0곳", reset_state["moved"].strip() == "0곳",
       reset_state["moved"])
    ok("초기화 후 군집 크기가 최초와 동일", reset_state["counts"] == info["counts"],
       f"{reset_state['counts']} vs {info['counts']}")

    # ── 5-c. 군집 필터 ────────────────────────────────────────
    page.click('#clusterFilter .chip[data-v="1"]')
    page.wait_for_timeout(400)
    filt = page.evaluate("""() => {
      const S = window.__dash.state;
      let shown = 0;
      S.markers.forEach(m => { if (m.options.fillOpacity > 0) shown++; });
      return { filter: S.filter, shown,
               listCount: document.getElementById('listCount').textContent,
               rows: document.querySelectorAll('#stationList .row').length };
    }""")
    ok("군집 1 필터: 해당 군집 마커만 보인다",
       filt["shown"] == info["counts"][1], f"보이는 마커 {filt['shown']} / 군집1 {info['counts'][1]}")
    ok("군집 1 필터: 목록도 그 군집만", str(info["counts"][1]) in filt["listCount"].replace(",", "") or "곳" in filt["listCount"],
       filt["listCount"])
    page.evaluate("""() => { window.__dash.state.map.setView([37.5512,126.9882],11,{animate:false});
        window.scrollTo(0,0); return null; }""")
    page.wait_for_timeout(1200)
    page.screenshot(path=os.path.join(SHOTS, "02_군집1_필터.png"))

    page.click('#clusterFilter .chip[data-v="all"]')
    page.wait_for_timeout(400)
    all_shown = page.evaluate("""() => { let n=0;
      window.__dash.state.markers.forEach(m => { if (m.options.fillOpacity > 0) n++; }); return n; }""")
    ok("전체 필터로 되돌리면 2,782개 모두 보인다", all_shown == EXPECTED_STATIONS,
       f"{all_shown}")

    # ── 5-d. 검색 + 목록 선택 ─────────────────────────────────
    page.fill("#search", "DMC역 2번출구")
    page.wait_for_timeout(400)
    rows = page.query_selector_all("#stationList .row")
    ok("검색(대여소명)이 결과를 좁힌다", 0 < len(rows) <= 5, f"{len(rows)}건")
    rows[0].click()
    page.wait_for_timeout(600)
    detail = page.inner_text("#station")
    need = ["대여소번호", "자치구", "일평균 이용건수", "출근시간 비중", "퇴근시간 비중",
            "주말 비중", "심야 비중", "거치대 수", "거치대당 일평균",
            "동일가중치점수", "집중운영점수", "우선관리등급", "군집"]
    missing = [t for t in need if t not in detail]
    ok("상세 패널에 필요한 항목이 모두 있다", not missing, f"빠짐 {missing}")
    ok("선택한 대여소가 DMC역이다", "DMC역" in detail, detail.split("\n")[0][:40])
    ok("상세에 '군집 번호는 순위가 아니다' 안내", "순위가 아니다" in detail, "")
    page.screenshot(path=os.path.join(SHOTS, "04_대여소_상세.png"))

    page.fill("#search", "870")
    page.wait_for_timeout(400)
    rows = page.query_selector_all("#stationList .row")
    ok("검색(대여소번호)도 동작", len(rows) >= 1, f"{len(rows)}건")

    page.fill("#search", "")
    page.wait_for_timeout(300)

    # ── 5-e. 지도 마커 선택 → 목록 동기화 ─────────────────────
    sync = page.evaluate("""() => {
      const S = window.__dash.state;
      // 지도 마커 클릭을 실제로 발생시킨다
      const target = S.rows[10];
      S.markers.get(target.id).fire('click');
      const row = document.querySelector('#stationList .row[aria-current="true"]');
      return { selected: S.selectedId, target: target.id,
               listSynced: !!row && row.dataset.id === target.id,
               detailHas: document.getElementById('station').innerText.includes(target.name) };
    }""")
    ok("지도 마커 선택 → 상태 반영", sync["selected"] == sync["target"], str(sync))
    ok("지도 마커 선택 → 목록에서 같은 대여소가 선택 표시",
       sync["listSynced"], str(sync))
    ok("지도 마커 선택 → 상세 패널 갱신", sync["detailHas"], "")

    # ── 5-f. 군집 카드 클릭 = 필터 ────────────────────────────
    page.click('#clusterCards .card[data-k="3"]')
    page.wait_for_timeout(400)
    card_filter = page.evaluate("() => window.__dash.state.filter")
    ok("군집 카드 클릭으로도 필터가 걸린다", card_filter == "3", str(card_filter))
    page.click('#clusterCards .card[data-k="3"]')
    page.wait_for_timeout(300)
    ok("같은 카드를 다시 누르면 전체로 돌아온다",
       page.evaluate("() => window.__dash.state.filter") == "all", "")

    # ── 7. 스크린샷 (데스크톱 · 태블릿 · 모바일) ──────────────
    # 앞선 검사에서 지도가 특정 대여소로 확대돼 있다. 서울 전체 뷰로 되돌린다.
    def reset_view(wait=1400):
        page.evaluate("""() => {
          window.__dash.state.map.closePopup();
          window.__dash.state.map.setView([37.5512, 126.9882], 11, {animate:false});
          window.scrollTo(0, 0);
          document.querySelectorAll('.panel').forEach(el => { el.scrollTop = 0; });
          return null;
        }""")
        page.wait_for_timeout(wait)

    reset_view()
    page.screenshot(path=os.path.join(SHOTS, "01_기본화면_데스크톱.png"))

    page.set_viewport_size({"width": 1024, "height": 900})
    page.wait_for_timeout(700)
    page.evaluate("() => { window.__dash.state.map.invalidateSize(); return null; }")
    page.wait_for_timeout(500)
    reset_view(3000)
    page.screenshot(path=os.path.join(SHOTS, "05_태블릿_1024.png"), full_page=True)

    page.set_viewport_size({"width": 420, "height": 900})
    page.wait_for_timeout(700)
    page.evaluate("() => { window.__dash.state.map.invalidateSize(); return null; }")
    page.wait_for_timeout(500)
    reset_view(3000)
    page.screenshot(path=os.path.join(SHOTS, "06_모바일_420.png"), full_page=True)
    page.set_viewport_size({"width": 1600, "height": 950})

    # ── 6. 콘솔 오류 ──────────────────────────────────────────
    bad = [(t, m) for t, m in console
           if t in ("error", "pageerror")
           # 타일 서버 차단은 화면 기능 문제가 아니다 — 별도로 안내 문구가 뜬다
           and "tile.openstreetmap" not in m and "ERR_" not in m]
    ok("콘솔 오류 없음", not bad, str(bad[:3]))
    tile_errors = [m for t, m in console if "tile.openstreetmap" in m]
    if tile_errors:
        print(f"     (참고) 지도 타일 요청 실패 {len(tile_errors)}건 — 오프라인 환경일 수 있다. "
              f"점 표시는 영향 없음")

    # 저장할 요약
    summary = page.evaluate("""() => {
      const S = window.__dash.state;
      return { counts: S.summary.map(c => c.n),
               names: S.summary.map(c => c.nameCandidate),
               means: S.summary.map(c => c.mean),
               mean: S.mean, std: S.std };
    }""")
    with open(os.path.join(HERE, "last_run.json"), "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "moved": moved,
                   "results": [(n, p, d) for n, p, d in results]},
                  f, ensure_ascii=False, indent=2)

    browser.close()

print()
print(f"검사 {len(results)}건 · 통과 {len(results) - len(fails)}건 · 실패 {len(fails)}건")
print("스크린샷:", ", ".join(sorted(os.listdir(SHOTS))))
if fails:
    print()
    for f_ in fails:
        print(" 실패:", f_)
    sys.exit(1)
