export type Heading = { depth: number; text: string; id: string };
export function validateDocumentSource(source: string): string;
export function documentUrl(source: string): string;
export function resolveDocumentLink(source: string, href: string): { source: string; query: string; fragment: string } | null;
export function repositorySourceUrl(source: string, href: string): string;
export function analyzeMarkdown(markdown: string): { headings: Heading[]; links: { href: string; title: string; section: string }[] };
