// User-approved development drafts. Update text and version together before release.
export const legalDocuments = {
  terms_of_service: {
    title: "이용약관", version: "dev-2026-10-02", href: "/terms",
    paragraphs: [
      "고민일기는 이용자가 자신의 마음과 경험을 기록할 수 있는 서비스를 제공합니다. 이용자는 이메일 소유 인증과 필수 동의를 거쳐 계정을 만들며, 자신의 계정 정보를 관리합니다.",
      "타인의 계정 도용, 타인의 권리 침해 및 서비스 운영을 방해하는 행위는 허용되지 않습니다. 이용자가 작성하는 내용은 타인의 개인정보나 권리를 침해하지 않아야 합니다.",
    ],
  },
  privacy_collection: {
    title: "개인정보 수집·이용 동의", version: "dev-2026-10-02", href: "/privacy",
    paragraphs: [
      "회원가입과 계정 관리를 위해 이름, 이메일, 비밀번호의 단방향 해시, 약관 종류·버전·동의 시각을 저장합니다. 이메일 소유 확인과 로그인 유지를 위해 인증 코드의 해시, 인증 상태·만료 시각 및 세션 토큰의 해시를 처리합니다.",
      "수집 목적은 이메일 소유 인증, 계정 생성, 본인 인증, 로그인 유지 및 필수 동의 내역 관리입니다. 인증 메일은 설정된 발송 제공자를 통해 전달합니다.",
      "필수 정보 수집·이용에 동의하지 않을 수 있으며, 이 경우 회원가입을 완료할 수 없습니다.",
    ],
  },
} as const;
