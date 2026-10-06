import type { Metadata } from "next";
import { CollectionGallery } from "@/components/collection-gallery";
import { AuthGuard } from "@/components/auth-guard";
import { sharedPages } from "@/lib/shared-pages";

export const metadata: Metadata = { title: `${sharedPages.collection.title} | 고민일기` };

export default function Page() {
  return <AuthGuard><CollectionGallery /></AuthGuard>;
}
