import { apiFetch } from "./api";
import {
  collectionCategories, CollectionNotFoundError,
  type CollectionItem, type CollectionRepository,
} from "./collection";

export type CollectionRow = {
  id: string; source_result_id: string; title: string; diary_date: string;
  emotion_tags: string[]; image_url: string;
};

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
    async detail() {
      throw new CollectionNotFoundError();
    },
  };
}
