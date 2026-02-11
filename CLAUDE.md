# NK-Russia TNR Tracker

## 프로젝트 컨텍스트
북한-러시아 초국가적 억압(TNR) 추적 시스템. OSINT 기반 인권 침해 데이터 수집/분석/보고.

## 연결 스킬
- strategic-osint: 지정학적 분석, 국제정치 컨텍스트
- security-osint: 네트워크 스캔(nmap-unleashed), 보안 인텔(secintel-ai)
- web-osint: 웹 크롤링(Crawl4AI/WebExtractor), 계정 추적(Sherlock)
- financial-osint: 제재 대상 금융 추적(Dexter)
- files: 문서 변환(Docling), 크롤링
- agent-orchestration: CrewAI 멀티에이전트 분석, strix, allama
- dev-tools: 빌드도구, 글로벌 Python 라이브러리

## 연결 MCP 프로필
- osint-full: OSINT 전체 (dexter, osint-tools, geospatial, signals)
- data: 한국 공공데이터 API (data-go-mcp-servers)
- docs: 문서 처리 (docling, zotero)
- security: 보안 도구 (mcp-security-hub)

## 주요 명령
```bash
uv venv && uv pip install -e ".[all]"    # 전체 설치
python -m packages.etl.pipeline --nightly  # ETL 파이프라인
uvicorn packages.api.main:app --reload     # API 서버
pytest                                      # 테스트
ruff check . && ruff format .              # 린트/포맷
```

## D:\repo 연동 도구
| 도구 | 용도 | 경로 |
|------|------|------|
| data-go-mcp-servers | 한국 공공데이터 ETL | D:\repo\data-go-mcp-servers |
| WebExtractor | 웹 데이터 추출 | D:\repo\WebExtractor |
| Doctra | AI 문서 분석 | D:\repo\Doctra |
| nmap-unleashed | 인프라 스캐닝 | D:\repo\nmap-unleashed |
| secintel-ai | 보안 인텔리전스 | D:\repo\secintel-ai |
| marker-pdf | PDF→MD 변환 | pip: marker-pdf |
| NetAlertX | 네트워크 모니터링 | D:\repo\NetAlertX |
| AI-Scientist | AI 연구 자동화 | D:\repo\AI-Scientist |
