# 고민일기 배경 자산

웹에서 사용하는 장식용 배경을 AVIF와 WebP로 함께 제공한다. 원본에 문구를 합성하지 않으며 제목·안내는 별도 UI 텍스트로 배치한다.

| 자산 | 규격 | 원본 |
| --- | --- | --- |
| `home-mobile` | 1440×3120 | 기존 로컬 `figma/home-mobile.png` |
| `login-mobile` | 1440×3120 | Figma `Background / Login / Mobile` (`23:2`) PNG 1× 내보내기 |
| `home-desktop` | 2560×1440 | Figma `39:48` PNG 1× 내보내기 |
| `login-desktop` | 2560×1440 | Figma `25:2` PNG 1× 내보내기 |
| `collection-desktop` | 2560×1440 | Figma `65:114` PNG 1× 내보내기 |
| `talk-desktop` | 2560×1440 | Figma `85:1433` PNG 1× 내보내기 |
| `talk-mobile` | 1440×3120 | Figma `85:1434` PNG 1× 내보내기 |

로그인 PC 자산은 가이드·회원가입에서도 공유한다. 로그인 모바일 자산은 회원가입에서도 공유하며, 인증 화면 구현에서 현재 Figma의 실내 벽·사진·책상 배경을 다시 내보내 반영했다. 기존 로컬 PNG와 `figma/assets/backgrounds/mobile-assets.json`의 로그인 변환 기록은 이 새 자산의 기준이 아니다.

`PageShell`은 `picture`의 media 조건으로 기기에 맞는 AVIF/WebP를 선택한다. `object-fit: cover`로 비율을 유지하므로 화면 비율에 따라 가장자리 일부가 잘릴 수 있다. 배경은 접근성 트리와 포인터 이벤트에서 제외한다.

[페이지별 매핑과 표시 방식](../../../../docs/frontend/shared-ui.md)을 참고한다.
