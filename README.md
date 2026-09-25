- ComfyUI는 노드 기반으로 이미지 생성 파이프라인을 구성하는 도구다.
- 최소 workflow는 Checkpoint 로드 → Prompt 인코딩 → Sampling → Decode → Save 흐름으로 이해할 수 있다.
- 같은 장면 조건을 유지한 채 seed를 변경하면 reference image variation을 만들 수 있다.

## DAY2 — Prompt Control & Shot Design

### Goal
동일한 Scene에서 Prompt와 Seed가 이미지 Composition과 Consistency에 어떤 영향을 주는지 실험하고, 이후 Image-to-Video에 사용할 Reference Image를 선정했다.

### Prompt Structure
Prompt를 다음 5개 요소로 분리했다.

- Character
- Environment
- Composition
- Lighting
- Mood

Scene, Character, Lighting, Mood는 유지하고 Composition만 변경하여 서로 다른 Shot을 생성했다.

### Shot Design

- Shot A: symmetrical establishing shot / centered / deep perspective
- Shot B: side profile walking shot / rule of thirds
- Shot C: follow shot / rear view / leading lines

동일한 Seed에서 Composition Prompt만 변경했을 때 Shot A와 B는 의도가 비교적 잘 반영되었고, Shot C는 rear follow shot 지시가 부분적으로만 반영되었다.

### Seed Test
동일한 Prompt에서 Seed만 변경하여 3장을 생성했다.

유지된 요소:
- centered composition
- deep perspective
- overall mood

변화한 요소:
- platform layout
- train placement
- character styling
- exact symmetry

Prompt는 Shot의 큰 방향을 제어하지만, 명시되지 않은 세부 요소는 Seed의 영향을 크게 받는 것을 확인했다.

### Img2Img
Reference Image를 활용하기 위해 기본 Img2Img Workflow를 구성했다.

Load Image → VAE Encode → KSampler → VAE Decode → Save Image

Denoise 비교:

- 0.35: Composition과 Scene 구조를 강하게 유지하며 세부 디테일만 일부 변경
- 0.55: 전체 Shot 구조는 유지하지만 Character와 Environment의 재해석이 증가

### Key Learning

AI Shot 생성은 단순 Prompt 입력보다 다음 반복 구조가 중요하다.

Shot Specification  
→ Prompt Construction  
→ Generation  
→ Evaluation  
→ Iteration

Text-to-Image는 새로운 Shot 탐색에 적합하고, Img2Img는 선택한 Reference를 기반으로 Controlled Variation과 Refinement를 수행하는 데 유용했다.