from supabase import AsyncClient

from app.core.errors import AppError


class AuthRepository:
    def __init__(self, database: AsyncClient):
        self.database = database

    async def _execute(self, query):
        try:
            return (await query.execute()).data
        except Exception:
            raise AppError(503, "SERVICE_UNAVAILABLE", "인증 서비스를 일시적으로 이용할 수 없습니다.") from None

    async def find_member(self, email: str):
        rows = await self._execute(self.database.table("members")
                                  .select("id,email,name,password_hash").eq("email", email).limit(1))
        return rows[0] if rows else None

    async def create_session(self, member_id: str, digest: str):
        await self._execute(self.database.rpc("create_auth_session", {
            "p_member_id": member_id, "p_digest": digest,
        }))

    async def renew_session(self, digest: str):
        rows = await self._execute(self.database.rpc("renew_auth_session", {"p_digest": digest}))
        return rows[0] if rows else None

    async def delete_session(self, digest: str):
        await self._execute(self.database.table("auth_sessions").delete().eq("token_digest", digest))
