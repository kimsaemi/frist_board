# 🚲 서울시 따릉이 & 3040 맞벌이 주거지 대시보드 웹호스팅 실습

본 저장소는 **서울시 따릉이 대여소 모빌리티 데이터 분석** 및 **3040 실수요자 주거 후보지역 종합 분석 대시보드**를 위한 웹호스팅 실습 저장소입니다.

---

## 📌 주요 실습 및 대시보드 구성

### 1. 🚲 서울시 따릉이 요약 대시보드 (`simple_dashboard/index.html`) [NEW]
* **총 이용건수(`21,280,450건`)** 및 **운영 대여소 수(`2,794개`)** 핵심 KPI 카드
* 0시~23시 시간대별 이용량 추이 그래프 & TOP 5 최다 대여소 시각화
* 평일/주말 필터링 및 대여소 검색 기능 지원

### 2. 🗺️ 서울시 따릉이 지도 대시보드 (`index.html` / `따릉이_지도_대시보드.html`)
* **Leaflet.js** 기반 동적 지도 시각화
* 대여소별 이용량, 출근시간대 비중, 9호선/지하철 라스트마일 연계 분석
* 군집 분석(Cluster) 필터링 및 대여소 검색 기능 제공

### 3. 🏠 3040 실수요자 주거후보지역 종합분석 리포트 (`서울시_3040_실수요자_주거후보지역_종합분석리포트.html`)
* 부동산 실거래가, 3040 실측 통근 이동량, 금리 사이클별 자산 방어력 융합 분석
* 예산대별 추천 주거지(당산동, 사당동, 염창동, 봉천동, 공덕동 등) 데이터 시각화

---

## 🌐 대시보드 웹호스팅 실습 (Web Hosting Practice)

본 실습은 GitHub Pages를 활용하여 데이터 시각화 대시보드를 실제 웹사이트로 무료 호스팅(배포)해보는 실습 과정입니다.

### 🌐 배포 완료 후 웹사이트 접속 주소
* 📊 **따릉이 요약 대시보드**: [https://kimsaemi.github.io/frist_board/simple_dashboard/index.html](https://kimsaemi.github.io/frist_board/simple_dashboard/index.html)
* 🚲 **따릉이 지도 대시보드**: [https://kimsaemi.github.io/frist_board/](https://kimsaemi.github.io/frist_board/)
* 🏠 **3040 주거후보지역 리포트**: [https://kimsaemi.github.io/frist_board/서울시_3040_실수요자_주거후보지역_종합분석리포트.html](https://kimsaemi.github.io/frist_board/서울시_3040_실수요자_주거후보지역_종합분석리포트.html)

---

## 📂 저장소 구조 (Directory Structure)

```
.
├── simple_dashboard/                                 # [NEW] 따릉이 요약 대시보드 (총 이용건수 & 운영 대여소 수)
│   ├── index.html
│   ├── style.css
│   └── app.js
├── index.html                                        # 메인 지도 대시보드 웹 페이지
├── 따릉이_지도_대시보드.html                          # 따릉이 지도 대시보드
├── 서울시_3040_실수요자_주거후보지역_종합분석리포트.html # 3040 실수요자 주거 분석 리포트
├── 서울시_3040_실수요자_주거후보지역_종합분석리포트.pdf  # PDF 리포트 파일
├── 데이터_분석_명세서_및_통계요약.md                   # 데이터 명세서 및 분석 요약
├── stations_data.js                                  # 따릉이 대여소 시각화 데이터 JS
├── bike_station_aggregated.csv                       # 대여소 집계 데이터
├── 05주차_데이터셋/                                   # 원본 및 파생 분석 데이터셋
├── 13일차_따릉이_우선관리/                           # 13일차 프롬프트 및 분석자료
└── 14일차_따릉이_군집과지도/                         # 14일차 군집분석 및 대시보드 앱
```

---

© 2026 3040 Housing & Mobility Data Lab

