export type Member = { id: string; email: string; name: string };
type Snapshot = { member: Member | null | undefined; error: string };
export const AUTH_RECHECK_MS = 5 * 60 * 1000;
const initialSnapshot: Snapshot = { member: undefined, error: "" };

/** In-memory UI state only. Server APIs still authorize every request. */
export function createAuthSession(
  load: () => Promise<Member>,
  isUnauthorized: (error: unknown) => boolean,
  now: () => number = Date.now,
) {
  let snapshot = initialSnapshot;
  let version = 0;
  let lastAttempt: number | undefined;
  let pending: Promise<void> | undefined;
  const listeners = new Set<() => void>();
  const update = (value: Snapshot) => {
    snapshot = value;
    listeners.forEach((listener) => listener());
  };
  const accept = (member: Snapshot["member"]) => {
    version++;
    pending = undefined;
    lastAttempt = now();
    update({ member, error: "" });
  };
  const refresh = (): Promise<void> => {
    if (pending) return pending;
    const current = version;
    lastAttempt = now();
    const request = (async () => {
      try {
        const member = await load();
        if (version === current) update({ member, error: "" });
      } catch (error) {
        if (version !== current) return;
        if (isUnauthorized(error)) accept(null);
        else update({ ...snapshot, error: "로그인 상태를 확인할 수 없어요. 연결을 확인하고 다시 시도해 주세요." });
      }
    })();
    pending = request;
    void request.finally(() => { if (pending === request) pending = undefined; });
    return request;
  };
  return {
    getSnapshot: () => snapshot,
    getServerSnapshot: () => initialSnapshot,
    subscribe: (listener: () => void) => {
      listeners.add(listener);
      return () => { listeners.delete(listener); };
    },
    refresh,
    recheck: () => pending ?? (lastAttempt === undefined || now() - lastAttempt >= AUTH_RECHECK_MS ? refresh() : Promise.resolve()),
    accept,
    // Capture when a protected API starts, not when its response arrives.
    captureUnauthorized: () => {
      const current = version;
      return () => { if (version === current) accept(null); };
    },
    invalidate: () => { version++; pending = undefined; },
  };
}
