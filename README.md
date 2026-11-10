# EPL 2025/26 — OpenPlay 패스 및 xT 분석 

## 데이터 선택 결과
- 2026/27 EPL: 1~10R의 경기 결과 데이터는 확보했지만 **공개된 선수별 패스 좌표 이벤트 데이터는 확인되지 않음**.
- 사용자가 사전에 승인한 대안에 따라 **25/26 시즌**을 선택.
- 25/26 실제 패스 데이터 출처: openplay (Noah Bair), `events_eng_2526.parquet`, https://github.com/nlbair/openplay/releases/tag/data-v0.1.0 (CC BY 4.0).
- 데이터는 ZIP에 **포함하지 않음**. 아래 스크립트가 GitHub 공식 파일을 다운받아 SHA-256 확인 후 변환한다. 이 환경에서는 외부 원본 다운로드를 실행할 수 없었으므로, 현 시점에 실제 25/26 이벤트 CSV가 완성됐다고 주장하지 않는다.
- 원본 **수신자 정보 없음** → 선수 간 정확한 패스 네트워크 비활성화. 실제 패스 위치 지도와 선수별 xT 계산 가능.
- xT 그리드: https://karun.in/blog/data/open_xt_12x8_v1.json (Karun Singh, 2017/18 EPL 기반 공개 그리드). **25/26로 학습한 모델이 아님**.

## Windows PowerShell — 실행 순서
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/download_openplay_2526.py
streamlit run app.py
```

`download_openplay_2526.py`만 인터넷 연결이 필요하며, 원본 패스 파일은 약 11.5MB이다. 첫 실행 시 다운로드 시간을 고려하고 SHA-256 오류가 뜨면 데이터 사용을 중단하라.

## 파일 안내
- `scripts/download_openplay_2526.py`: 원본 파일·xT 그리드 다운로드, SHA-256 검증, canonical pass CSV 및 manifest 생성
- `src/epl_xt/openplay_adapter.py`: 엄격한 25/26 컬럼 변환 (원본 수신자 미제공을 그대로 보존)
- `src/epl_xt/provenance_2526.py`: import 데이터 무결성 검사
- `app.py`: 25/26 실제 패스 좌표, xT, 선수 비교 (다운로드 전에는 실행 방법만 표시)
- `pages/99_26_27_결과_보관.py`: **별도** 26/27 1~10R 경기 결과, 혼합 금지
- `docs/codex_prompts.md`: AI 개발을 위한 다음 작업 프롬프트
- `tests/test_openplay_adapter.py`: 소스 필드 변환 및 시즌 변경 방지 자동 테스트

## 사용 시 저작자 표기
Event data: **openplay (Noah Bair)**, CC BY 4.0.
 xT grid: **Karun Singh**, https://karun.in/blog/expected-threat.html
