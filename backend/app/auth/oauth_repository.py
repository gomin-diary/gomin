"""Server-only OAuth RPC boundary."""
from app.core.errors import AppError

ERRORS = {
    'OAUTH_REQUEST_INVALID': (400, 'Google 로그인을 다시 시작해 주세요.'),
    'OAUTH_PROOF_INVALID': (400, '가입 인증이 만료됐어요. Google 로그인을 다시 시작해 주세요.'),
    'OAUTH_LINK_CONFLICT': (409, '연결된 Google 계정을 확인한 뒤 다시 로그인해 주세요.'),
    'EMAIL_EXISTS': (409, '이미 가입된 이메일이에요. Google 로그인을 다시 시작해 주세요.'),
    'CONSENT_VERSION_CHANGED': (409, '약관이 변경됐어요. 새로고침한 뒤 다시 동의해 주세요.'),
    'INVALID_NAME': (422, '이름은 공백을 제외하고 1~30자로 입력해 주세요.'),
}

class OAuthRepository:
    def __init__(self, db):
        self.db = db

    async def call(self, name: str, params: dict):
        try:
            result = (await self.db.rpc(f'gomin_auth_oauth_{name}', params).execute()).data
        except Exception:
            raise AppError(503, 'SERVICE_UNAVAILABLE', '인증 서비스를 일시적으로 이용할 수 없습니다.') from None
        if not isinstance(result, dict):
            raise AppError(503, 'SERVICE_UNAVAILABLE', '인증 서비스를 일시적으로 이용할 수 없습니다.')
        if code := result.get('error'):
            status, message = ERRORS.get(code, (400, 'Google 로그인을 다시 시작해 주세요.'))
            raise AppError(status, code, message)
        return result
