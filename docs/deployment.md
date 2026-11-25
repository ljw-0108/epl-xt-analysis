# 배포 설계 — Streamlit Community Cloud

## 원칙
데이터(`data/`)와 생성 manifest는 Git에 넣지 않는다. 배포된 앱은 **처음 시작할 때 로컬 실행과 같은 검증 파이프라인**(`src/epl_xt/pipeline.py`)을 실행해 데이터를 만든다.

1. OpenPlay `checksums.json` → 이벤트 Parquet 다운로드 → 배포처 SHA-256 대조
2. Karun Singh xT 그리드 다운로드 → 고정 SHA-256 대조
3. 25/26·EPL 외 데이터 거부, 패스 변환·스키마 검증
4. `passes.csv`·`xt_grid.csv`·`matches.csv` 저장 → **마지막에** manifest 저장
5. 앱은 manifest 해시로 가공 파일을 다시 검증한 뒤에만 수치를 표시

실패하면(네트워크, 체크섬 불일치, 시즌 불일치) 오류만 표시하고 대체 데이터를 만들지 않는다. 시작 전에 기존 manifest를 지우므로 실패한 실행이 예전 manifest로 검증된 것처럼 보이지 않는다. 자동 준비는 세션당 한 번만 시도한다(실패 시 무한 재시도 없음). 동시에 여러 방문자가 와도 잠금으로 한 번만 실행된다.

## 실행 모드
| 상황 | 동작 |
|---|---|
| 로컬, 데이터 없음 | "원본 내려받기 및 검증" 버튼 + CLI 안내 |
| `EPL_AUTO_PREPARE=1` (환경변수 또는 Streamlit Secrets 최상위 키) | 데이터가 없으면 자동 실행 |
| 데이터 있음 | 바로 로딩 (manifest 해시 검증) |

## 배포 절차 (사용자 계정에서 수행)
1. https://share.streamlit.io 에 GitHub 계정으로 로그인한다. 저장소가 비공개이면 Streamlit에 비공개 저장소 접근 권한을 준다.
2. **Create app** → Repository `ljw-0108/epl-xt-analysis`, Branch `main`(PR 병합 후; 병합 전 시연은 `claude/affectionate-goodall-6ohzho`), Main file `app.py`.
3. **Advanced settings** → Python 3.12, Secrets에 다음 한 줄:
   ```toml
   EPL_AUTO_PREPARE = "1"
   ```
4. Deploy. 첫 방문 시 데이터 준비 단계가 상태 상자로 표시된 뒤 대시보드가 열린다.
5. 배포 URL을 README와 `docs/claude_harness_plan.md`에 기록한다.

## 리허설 결과 (2026-11-25, 이 컨테이너)
- 데이터·manifest가 없는 코드 사본에서 `EPL_AUTO_PREPARE=1 streamlit run app.py` → 약 **12초** 후 대시보드 표시 (Playwright 확인).
- 생성된 결과: 패스 362,739건, 380경기, 제외 0건. `passes.csv` SHA-256이 로컬 실행 결과와 동일 (변환이 결정적).
- 메모리: 파이프라인 최대 RSS 약 **425MB**, 데이터 로딩 최대 RSS 약 256MB(DataFrame 85MB). Community Cloud 메모리 한도 안에 들어갈 것으로 예상하지만 실제 배포에서 확인이 필요하다.

## 위험과 대응
- **외부 호스트 접근:** Streamlit Cloud에서 `github.com`(릴리스)과 `karun.in` 접근이 필요하다. 막히면 준비가 실패하고 오류가 표시된다(대체 없음).
- **저장소 휘발성:** 앱이 잠들었다 깨어나면 파일이 사라질 수 있어 첫 방문 때 다시 준비한다(약 12초 + 다운로드 시간).
- **그리드 파일 변경:** 배포처가 그리드를 바꾸면 고정 해시와 달라 중단된다. 새 파일을 검토한 뒤에만 `GRID_SHA256`을 갱신한다.
- **라이선스:** 이벤트 데이터 CC BY 4.0 — 앱 상단·하단과 CSV 안내에 출처 표기가 있다.
