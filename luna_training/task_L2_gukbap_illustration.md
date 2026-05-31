# 루나 진단 과제 #L2 — 국밥집 브리프 (미니멀 플랫 2D 일러스트)

> 목적: 사진 및 카메라 관련 토큰을 전면 배제하고, 매체(블로그 썸네일용 2D 일러스트)에 맞는 일러스트 도구함만으로 미드저니와 플럭스를 통제한다.
> 작성일: 2026-05-31
> 작성자: 루나 (Luna)

## 📌 브리프 (Brief)
- **피사체:** 국밥집 (김이 나는 뚝배기와 둥근 테이블).
- **매체/스타일:** 블로그 썸네일용 미니멀 플랫 2D 편집 일러스트. 

---

## 1. Midjourney (v6) 프롬프트 

**Prompt:**
> Minimalist flat 2D vector illustration of a Korean Gukbap restaurant. A simple black stone bowl with stylized steam on a round table. Editorial style, bold geometric shapes, limited warm color palette, thick clean outlines, no shading, no gradients, solid flat background, graphic design aesthetic. --ar 16:9 --no 3d, realism, realistic, shadows --v 6.0

**루나의 기획 의도 (MJ):**
사진 관련 토큰을 단 하나도 남기지 않고 모두 폐기했습니다. 대신 `flat 2D vector`, `bold geometric shapes`, `limited warm color palette` 같은 정확한 일러스트 문법만 배치했습니다. 미드저니가 멋대로 입체감이나 실사 느낌을 섞는 고질적인 버릇을 원천 차단하기 위해 `no shading, no gradients`를 명시하고, `--no 3d, realism, realistic, shadows` 네거티브 프롬프트를 걸어 완벽하게 납작한(flat) 썸네일용 매체를 강제했습니다.

---

## 2. Flux 프롬프트 

**Prompt:**
> A flat 2D editorial vector illustration of a Korean soup restaurant. A stylized black stone bowl with flat white steam on a table. In the background, a simple flat menu board with the Korean text "원조국밥". Minimalistic design, bold flat shapes, solid flat colors, thick outlines, clean UI illustration aesthetic, no gradients, no photorealism.

**루나의 기획 의도 (Flux):**
플럭스의 텍스트 렌더링 강점을 일러스트에서도 살리기 위해, 배경 메뉴판에 `"원조국밥"`이라는 한글 텍스트를 명시했습니다. 다만 플럭스가 세밀한 디테일(물방울, 거친 질감)을 파고들지 못하게 모든 시각적 서술을 `bold flat shapes`, `solid flat colors`, `minimalistic design`으로 묶어버렸습니다. 사실적인 묘사를 금지(`no gradients`, `no photorealism`)하여 블로그 썸네일에 맞는 깔끔하고 정돈된 벡터 일러스트 톤을 맞췄습니다.
