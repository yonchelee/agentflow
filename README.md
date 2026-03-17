# 🤖 AI Agent 제작 완전 가이드

Dataset에서 Agent까지 — 한 페이지로 끝내는 RAG & Agent 핵심 개념 정리

🔗 **[라이브 페이지 보기](https://[your-github-id].github.io/[repo-name]/)**

---

## 📌 다루는 내용

| 섹션 | 내용 |
|------|------|
| 전체 파이프라인 | Dataset → Chunk → Embedding → Knowledge → Agent 흐름 |
| 집합 관계 | Knowledge ⊃ Chunk ⊃ Embedding 포함 관계 시각화 |
| Embedding | 텍스트를 벡터로 변환하는 원리 |
| Chunk & Chunk Size | 문서 분할 전략, 크기별 트레이드오프 |
| Top-K | 유사도 검색 결과 선택 방식 |
| Agent 역할 설정 | Persona, Constraint, Format, Tool, Memory, Fallback |
| 프롬프트 강화 | System Prompt 구조, Few-shot, CoT, Temperature 등 |
| 전체 코드 | LangChain 기반 완전 구현 예시 |

---

## 🚀 로컬에서 실행

별도 설치 없이 `index.html`을 브라우저로 열면 바로 실행됩니다.

```bash
# 파일 다운로드 후
open index.html   # macOS
start index.html  # Windows
```

---

## 🛠 기술 스택

- **Pure HTML / CSS / JavaScript** — 외부 라이브러리 없음
- **Google Fonts** — Noto Sans KR, JetBrains Mono
- **GitHub Pages** 로 호스팅

---

## 📖 주요 개념 요약

```
Dataset   →   Chunking   →   Embedding   →   Vector DB   →   Agent
  📂            ✂️              🔢              🗄️              🤖
원본 문서    검색 단위 분할    벡터로 변환     Knowledge 저장   질문 → 답변
```

**Chunk Size 선택 기준**
- `128~256` tokens → 정밀한 검색, 문맥 부족 (FAQ에 적합)
- `512~1024` tokens → 균형 잡힌 선택 ★ (일반 문서에 추천)
- `2048+` tokens → 풍부한 문맥, 검색 정밀도 낮음 (논문/법률에 적합)

**Top-K 선택 기준**
- `k=1` → 빠름, 정보 부족
- `k=3` → 균형 (기본값 ★)
- `k=5~10` → 풍부한 문맥, 노이즈 증가

---

## 📄 License

MIT — 자유롭게 사용, 수정, 배포 가능합니다.
