import { DocDocument } from "@/components/docs/document";
import { getDocument } from "@/lib/docs";

export default function DocsPage() {
  const document = getDocument("");
  if (!document) throw new Error("Documentation index is missing");
  return <DocDocument document={document} />;
}
