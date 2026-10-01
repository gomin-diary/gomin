# 고민일기 배경 자산

로그인·홈 배경을 각각 **1440 × 3120px (6:13)**로 제공한다. `figma/`의 최신 `login-mobile.png`, `home-mobile.png`가 기준 원본이다. 문구가 없는 배경 이미지이므로 제목과 안내 문구는 UI 텍스트로 별도 배치한다.

| 화면 | AVIF | WebP |
|---|---|---|
| 로그인 | `login-mobile.avif` | `login-mobile.webp` |
| 홈 | `home-mobile.avif` | `home-mobile.webp` |

프레임워크의 정적 파일 디렉터리에 이 파일을 넣고 다음처럼 AVIF와 WebP 폴백을 함께 사용할 수 있다.

```html
<picture>
  <source srcset="/images/backgrounds/login-mobile.avif" type="image/avif" />
  <img
    src="/images/backgrounds/login-mobile.webp"
    width="1440"
    height="3120"
    alt=""
    decoding="async"
    fetchpriority="high"
    class="mobile-background"
  />
</picture>
```

```css
.mobile-background {
  display: block;
  width: 100%;
  height: auto;
  aspect-ratio: 6 / 13;
}
```

홈 화면에서는 파일 이름을 `home-mobile`로 바꾼다. 이 방식은 이미지 전체를 유지하며, 가로 390px에서는 세로 845px로 표시된다. 서로 다른 화면 비율에서 `object-fit: cover` 또는 `background-size: cover`를 사용하면 다시 일부 영역이 잘릴 수 있다.

원본 PNG와 변환 도구는 Git에서 제외한 `figma/` 안에 로컬로 유지한다. 출력 크기·원본 체크섬·파일 정보는 `figma/assets/backgrounds/mobile-assets.json`에 기록되어 있으며, 기록 안의 경로는 `figma/` 기준이다.

제공받은 852 × 1846px 원본을 1440 × 3120px로 확대하고 비율 차이를 최소한으로 정규화했다. 네 파일 모두 디코딩 후 크기와 포맷을 확인했다. 재변환: `python figma/scripts/export-mobile-backgrounds.py` (Pillow의 WebP/AVIF 지원 필요).

변환 결과는 `figma/public/images/backgrounds/`에 생성된다. 웹에 반영할 때는 필요한 AVIF/WebP 파일을 `frontend/public/images/backgrounds/`에 복사한다.

## 공용 화면 추가 자산

PC `home-desktop`, `login-desktop`, `collection-desktop`, `talk-desktop`과 모바일 `talk-mobile`을 AVIF/WebP로 제공한다. PC는 2560×1440, 모바일은 1440×3120이며 Figma의 해당 배경 컴포넌트를 1×로 내보낸 PNG에서 변환했다. 로그인 PC 자산은 가이드·회원가입에서도 공유한다.

[페이지별 매핑과 표시 방식](../../../../docs/frontend/shared-ui.md)을 참고한다.
