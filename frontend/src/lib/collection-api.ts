import { apiFetch, ApiRequestError } from "./api";
import {
  collectionCategories, CollectionNotFoundError,
  type CollectionItem, type CollectionRepository,
} from "./collection";

export type CollectionRow = {
  id: string; source_result_id: string; title: string; diary_date: string;
  emotion_tags: string[]; image_url: string;
};
type DetailRow = CollectionRow & { encouragement_text: string; current_feeling: string; main_concerns: string[] };

export function collectionItem(row: CollectionRow): CollectionItem {
  return {
    id: row.id, title: row.title, date: row.diary_date,
    image: { src: row.image_url, width: 1, left: 0, top: 0 },
    categories: collectionCategories.filter((tag) => tag !== "전체" && row.emotion_tags.includes(tag)) as CollectionItem["categories"],
  };
}

export function createApiCollectionRepository(request: typeof apiFetch = apiFetch): CollectionRepository {
  return {
    async list(_memberId, signal) {
      const rows = await request<CollectionRow[]>("/api/v1/collection", { signal });
      return rows.map(collectionItem);
    },
    async detail(_memberId, id, signal) {
      try {
        const row = await request<DetailRow>(`/api/v1/collection/${encodeURIComponent(id)}`, { signal });
        return { ...collectionItem(row), caption: row.encouragement_text,
          mind: row.current_feeling, concerns: row.main_concerns, emotions: row.emotion_tags };
      } catch (error) {
        if (error instanceof ApiRequestError && error.status === 404) throw new CollectionNotFoundError();
        throw error;
      }
    },
  };
}
