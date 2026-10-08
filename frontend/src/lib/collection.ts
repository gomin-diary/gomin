/** Collection display model. IDs identify saved entries, not generation results. */
export const collectionCategories = ["전체", "기쁨", "슬픔", "불안", "관계", "일상"] as const;
export type CollectionCategory = typeof collectionCategories[number];
export type CollectionImage = { src: string; width: number; left: number; top: number; accessPath?: string };
export type CollectionItem = {
  id: string;
  date: string;
  title: string;
  image: CollectionImage;
  categories: Exclude<CollectionCategory, "전체">[];
};
export type CollectionDetail = CollectionItem & {
  caption: string;
  mind: string;
  concerns: string[];
  emotions: string[];
};
export type CollectionRepository = {
  list: (memberId: string, signal?: AbortSignal) => Promise<CollectionItem[]>;
  detail: (memberId: string, id: string, signal?: AbortSignal) => Promise<CollectionDetail>;
  page?: (cursor: string | null, category: CollectionCategory, signal?: AbortSignal) => Promise<CollectionPage>;
};
export type CollectionPage = { items: CollectionItem[]; nextCursor: string | null };
export type CollectionApi = <T>(path: string, init?: RequestInit) => Promise<T>;

type ApiItem = { id: string; source_result_id: string; diary_date: string; title: string; emotion_tags: string[] };
type ApiDetail = ApiItem & { encouragement_text: string; current_feeling: string; main_concerns: string[] };
const entryPath = (id: string) => {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)) throw new CollectionNotFoundError();
  return `/api/v1/collection/${id}`;
};
function mapItem(row: ApiItem): CollectionItem {
  if (!row || typeof row.title !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(row.diary_date)
      || !Array.isArray(row.emotion_tags) || !row.emotion_tags.every(tag => typeof tag === "string")) throw new Error("Invalid collection data");
  return { id: row.id, date: row.diary_date, title: row.title,
    image: { src: "", width: 1, left: 0, top: 0, accessPath: `${entryPath(row.id)}/image-url` },
    categories: collectionCategories.filter((category): category is Exclude<CollectionCategory, "전체"> =>
      category !== "전체" && row.emotion_tags.includes(category)) };
}

/** Inject the shared apiFetch; account IDs never become authorization parameters. */
export function createApiCollectionRepository(request: CollectionApi): CollectionRepository {
  const page = async (cursor: string | null, category: CollectionCategory, signal?: AbortSignal): Promise<CollectionPage> => {
    const params = new URLSearchParams({ limit: "24" });
    if (cursor) params.set("cursor", cursor);
    if (category !== "전체") params.set("emotion", category);
    const data = await request<{ items: ApiItem[]; next_cursor: string | null }>(`/api/v1/collection?${params}`, { signal });
    if (!Array.isArray(data.items) || (data.next_cursor !== null && typeof data.next_cursor !== "string")) throw new Error("Invalid collection page");
    return { items: data.items.map(mapItem), nextCursor: data.next_cursor };
  };
  return {
    page,
    async list(_memberId, signal) {
      const items: CollectionItem[] = [], seen = new Set<string>();
      let cursor: string | null = null;
      do {
        signal?.throwIfAborted();
        const data = await page(cursor, "전체", signal);
        items.push(...data.items);
        cursor = data.nextCursor;
        if (cursor && seen.has(cursor)) throw new Error("Repeated collection cursor");
        if (cursor) seen.add(cursor);
      } while (cursor);
      return items;
    },
    async detail(_memberId, id, signal) {
      try {
        const row = await request<ApiDetail>(entryPath(id), { signal });
        if (typeof row.encouragement_text !== "string" || typeof row.current_feeling !== "string"
            || !Array.isArray(row.main_concerns) || !row.main_concerns.every(text => typeof text === "string")) throw new Error("Invalid collection detail");
        return { ...mapItem(row), caption: row.encouragement_text, mind: row.current_feeling,
                 concerns: row.main_concerns, emotions: row.emotion_tags };
      } catch (error) {
        if (error && typeof error === "object" && "status" in error && error.status === 404) throw new CollectionNotFoundError();
        throw error;
      }
    },
  };
}
export class CollectionNotFoundError extends Error {
  constructor() { super("기록을 찾을 수 없어요."); this.name = "CollectionNotFoundError"; }
}
export type CollectionScenario = "normal" | "empty" | "error" | "detail-error" | "slow";

/** Shared demo records for every signed-in member; future real records require server ownership checks. */
export function createMockCollectionRepository(
  records: readonly CollectionDetail[],
  { scenario = "normal", delay = 250 }: { scenario?: CollectionScenario; delay?: number } = {},
): CollectionRepository {
  let failedList = false;
  let failedDetail = false;
  async function wait(signal?: AbortSignal) {
    signal?.throwIfAborted();
    await new Promise<void>((resolve, reject) => {
      const abort = () => { clearTimeout(timer); reject(signal?.reason); };
      const timer = setTimeout(() => { signal?.removeEventListener("abort", abort); resolve(); }, delay);
      signal?.addEventListener("abort", abort, { once: true });
    });
    signal?.throwIfAborted();
  }
  return {
    async list(memberId, signal) {
      await wait(signal);
      if (scenario === "error" && !failedList) { failedList = true; throw new Error("Mock list failure"); }
      if (!memberId || scenario === "empty") return [];
      return records.map(({ id, date, title, image, categories }) =>
        structuredClone({ id, date, title, image, categories }));
    },
    async detail(memberId, id, signal) {
      await wait(signal);
      const record = memberId && records.find((record) => record.id === id);
      if (!record || scenario === "empty") throw new CollectionNotFoundError();
      if (scenario === "detail-error" && !failedDetail) { failedDetail = true; throw new Error("Mock detail failure"); }
      return structuredClone(record);
    },
  };
}

type LoadState = "loading" | "ready" | "error";
export type CollectionSnapshot = {
  status: LoadState;
  items: CollectionItem[];
  category: CollectionCategory;
  page: number;
  selectedId: string | null;
  detailStatus: LoadState;
  detail: CollectionDetail | null;
  detailNotFound: boolean;
};
export const COLLECTION_PAGE_SIZE = 6;
export function visibleCollectionItems(state: CollectionSnapshot) {
  return state.items.filter((item) => state.category === "전체" || item.categories.includes(state.category));
}

/** Request generations protect retries, rapid selection and disposal from late responses. */
export function createCollectionController(memberId: string, repository: CollectionRepository) {
  let state: CollectionSnapshot = {
    status: "loading", items: [], category: "전체", page: 0,
    selectedId: null, detailStatus: "loading", detail: null, detailNotFound: false,
  };
  const initial = state;
  const listeners = new Set<() => void>();
  let listVersion = 0, detailVersion = 0;
  let listAbort: AbortController | undefined, detailAbort: AbortController | undefined;
  const update = (patch: Partial<CollectionSnapshot>) => {
    state = { ...state, ...patch };
    listeners.forEach((listener) => listener());
  };
  const close = () => {
    detailVersion++; detailAbort?.abort();
    update({ selectedId: null, detail: null, detailNotFound: false });
  };
  const load = async () => {
    const version = ++listVersion;
    listAbort?.abort(); listAbort = new AbortController();
    update({ status: "loading" });
    try {
      const items = await repository.list(memberId, listAbort.signal);
      if (version !== listVersion) return;
      update({ status: "ready", items, page: 0 });
    } catch {
      if (version === listVersion) update({ status: "error", items: [] });
    }
  };
  const select = async (id: string) => {
    const version = ++detailVersion;
    detailAbort?.abort(); detailAbort = new AbortController();
    update({ selectedId: id, detail: null, detailStatus: "loading", detailNotFound: false });
    try {
      const detail = await repository.detail(memberId, id, detailAbort.signal);
      if (version === detailVersion) update({ detail, detailStatus: "ready" });
    } catch (error) {
      if (version === detailVersion) update({ detailStatus: "error", detailNotFound: error instanceof CollectionNotFoundError });
    }
  };
  return {
    getSnapshot: () => state,
    getServerSnapshot: () => initial,
    subscribe: (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; },
    load, select, close,
    filter: (category: CollectionCategory) => { close(); update({ category, page: 0 }); },
    move: (direction: -1 | 1) => {
      const maxPage = Math.max(0, Math.ceil(visibleCollectionItems(state).length / COLLECTION_PAGE_SIZE) - 1);
      update({ page: Math.max(0, Math.min(maxPage, state.page + direction)) });
    },
    dispose: () => { listVersion++; detailVersion++; listAbort?.abort(); detailAbort?.abort(); },
  };
}
