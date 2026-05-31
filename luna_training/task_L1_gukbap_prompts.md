# 루나 진단 과제 #L1 — 국밥집 브리프 (MJ vs Flux 프롬프트)

> 목적: 동일한 '국밥집' 씬을 두고, 미드저니(MJ)와 플럭스(Flux) 각 엔진의 특성에 맞춰 사족 토큰을 배제하고 극사실주의 프롬프트를 기획한다.
> 작성일: 2026-05-31
> 작성자: 루나 (Luna)

## 📌 브리프 (Brief)
- **피사체:** 세월의 흔적이 묻어나는 한국의 노포 국밥집 내부. 김이 모락모락 나는 뚝배기, 낡은 둥근 스테인리스 테이블.
- **무드:** 거칠지만 따뜻한, 인위적으로 꾸며지지 않은 리얼리티(Realism).

---

## 1. Midjourney (v6) 프롬프트 버전
미드저니는 자체적인 미적(Aesthetic) 개입이 매우 강하므로, 주관적 형용사를 철저히 배제하고 빛과 질감을 물리적으로 강제해야 사실적인 결과를 얻을 수 있습니다.

**Prompt:**
> Documentary photography of an old traditional Korean Gukbap restaurant interior. A heavily scratched stainless steel round table. In the center, a worn black earthen pot(ttukbaegi) filled with boiling pork soup, thick steam rising dynamically. Greasy tiled walls in the background, a warm tungsten light bulb hanging from the ceiling casting harsh, dramatic shadows. Shot on Sony A7R IV, 35mm lens, f/2.8. Kodachrome film stock, heavy film grain, unretouched, hyper-realistic, volumetric steam. --ar 16:9 --style raw --v 6.0

**루나의 기획 의도 (MJ):**
`beautiful`이나 `delicious` 같은 주관적 감상 토큰(사족)을 완전히 제거했습니다. 대신 `heavily scratched(심하게 긁힌)`, `greasy tiled walls(기름때 낀 타일 벽)` 같은 '결점 텍스처'를 부여했습니다. 또한 `--style raw` 파라미터와 `Kodachrome` 필름 스펙, `heavy film grain`을 명시하여 미드저니 특유의 '매끈한 디지털 느낌'을 거친 다큐멘터리 톤으로 억눌렀습니다.

---

## 2. Flux 프롬프트 버전
플럭스는 프롬프트의 서술을 직관적으로 이해하고 특히 '텍스트(글자) 렌더링'과 공간 배치에 강하므로, 요소를 명확한 서술형으로 배치합니다.

**Prompt:**
> A photorealistic, unretouched image of a rustic Korean soup restaurant(Gukbap) at night. A close-up of a steaming black stone bowl containing milky pork broth on a scratched metal table. Next to the bowl, there are small side dishes with vibrant red kimchi and green chili peppers. In the blurred background, a weathered wooden menu board hangs on the wall with Korean text clearly written as "원조 할매 국밥". Soft ambient fluorescent lighting overhead, highly detailed textures, realistic condensation on stainless water cups, depth of field, photorealism.

**루나의 기획 의도 (Flux):**
플럭스의 최대 강점인 '명확한 공간 이해도'와 '텍스트 렌더링' 능력을 살리기 위해, 배경에 `"원조 할매 국밥"`이라는 한글 메뉴판 텍스트가 정확히 출력되도록 명시했습니다. 또한 `realistic condensation on stainless water cups`(스테인리스 물컵에 맺힌 리얼한 물방울)처럼 구체적인 디테일을 서술식으로 나열하여, 플럭스 엔진이 화면을 물리적으로 완벽하게 채울 수 있도록 유도했습니다.
