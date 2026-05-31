# 루나 진단 과제 #L3 — 국밥집 브리프 (Flux 문장 문법 및 구도 통제)

> 목적: 쉼표(,)를 사용한 토큰 나열(키워드 스택)을 완벽히 배제하고, 오직 완결된 자연어 문장만으로 피사체와 구도(여백, 초점, 카메라 앵글)를 완벽하게 통제하여 플럭스(Flux) 엔진을 다룬다.
> 작성일: 2026-05-31
> 작성자: 루나 (Luna)

## 📌 브리프 (Brief)
- **피사체:** 국밥집 (김이 나는 뚝배기와 테이블).
- **매체/스타일:** 블로그 썸네일용 미니멀 플랫 2D 일러스트. 

---

## 1. Flux 전용 프롬프트 (자연어 문장 문법)

**Prompt:**
> This is a minimal flat 2D editorial illustration of a traditional Korean soup restaurant, designed specifically for a blog thumbnail. The composition is centered from a slight top-down angle, establishing a steaming black stone bowl as the primary focal point on a simple round table. A generous amount of solid warm pastel negative space surrounds the central bowl, providing ample room for future text overlays. Thick clean outlines and bold geometric shapes define all objects, while flat solid colors entirely replace any gradients or realistic shading. In the upper left area of the negative space, a flat wooden menu board hangs on a clean background, clearly displaying the Korean text "원조 할매 국밥" in bold typography. The entire image maintains a strict flat graphic design aesthetic without any photorealism or 3D rendering effects.

**루나의 기획 의도 (Flux):**
1. **자연어 문법 완전 전환:** 쉼표로 키워드를 나열하던 기존의 악습(MJ식 토큰 스택)을 단 하나도 남기지 않고 완벽하게 버렸습니다. 모든 지시 사항을 `The composition is centered...`, `A generous amount of negative space...`와 같이 주어와 동사가 있는 완결된 영어 문장 구조로 풀어내어, 플럭스의 뛰어난 자연어 이해력을 100% 가동했습니다.
2. **구도의 명확한 통제 (썸네일 최적화):** 엔진이 알아서 구도를 잡게 방치하지 않았습니다. 썸네일로서의 실용성을 위해 `primary focal point`(뚝배기를 주인공으로 설정), `slight top-down angle`(앵글 통제), `generous amount of negative space`(블로그 글씨가 들어갈 넉넉한 여백 확보), `upper left area`(메뉴판의 정확한 좌표 지정)를 문장 안에 단단하게 엮어내어 캔버스의 모든 공간(Negative Space 포함)을 완벽하게 통제했습니다.
