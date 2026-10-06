/** Temporary view model for GOMIN-31; this is not a database schema. */
export const collectionCategories = ["전체", "기쁨", "슬픔", "불안", "관계", "일상"] as const;
export type CollectionCategory = typeof collectionCategories[number];
export type CollectionImage = { src: string; width: number; left: number; top: number };
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
export type CollectionRecord = CollectionDetail & { memberId: string };
export type CollectionRepository = {
  list: (memberId: string, signal?: AbortSignal) => Promise<CollectionItem[]>;
  detail: (memberId: string, id: string, signal?: AbortSignal) => Promise<CollectionDetail>;
};
export class CollectionNotFoundError extends Error {
  constructor() { super("기록을 찾을 수 없어요."); this.name = "CollectionNotFoundError"; }
}
export type CollectionScenario = "normal" | "empty" | "error" | "detail-error" | "slow";

/** A mock transport only. Production ownership must be enforced by the future server API. */
export function createMockCollectionRepository(
  records: readonly CollectionRecord[],
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
      return records.filter((record) => record.memberId === memberId).map(({ id, date, title, image, categories }) =>
        structuredClone({ id, date, title, image, categories }));
    },
    async detail(memberId, id, signal) {
      await wait(signal);
      const record = memberId && records.find((record) => record.id === id && record.memberId === memberId);
      if (!record || scenario === "empty") throw new CollectionNotFoundError();
      if (scenario === "detail-error" && !failedDetail) { failedDetail = true; throw new Error("Mock detail failure"); }
      const { memberId: _owner, ...detail } = record;
      void _owner;
      return structuredClone(detail);
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
