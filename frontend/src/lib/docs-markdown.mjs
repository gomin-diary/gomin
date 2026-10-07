import path from "node:path";
import { unified } from "unified";
import remarkParse from "remark-parse";
import remarkGfm from "remark-gfm";
import { visit } from "unist-util-visit";
import { toString } from "mdast-util-to-string";
import GithubSlugger from "github-slugger";

const parser = unified().use(remarkParse).use(remarkGfm);

export function validateDocumentSource(source) {
  if (source.includes("\\")) throw new Error(`Backslash document path: ${source}`);
  const segments = source.split("/");
  if (source !== "README.md" && !source.startsWith("docs/")) {
    throw new Error(`Outside document root: ${source}`);
  }
  if (segments.some(segment => segment.startsWith(".") || segment === "superpowers")) {
    throw new Error(`Excluded document: ${source}`);
  }
  if (!source.endsWith(".md")) throw new Error(`Unsupported document: ${source}`);
  return source;
}

export function documentUrl(source) {
  validateDocumentSource(source);
  if (source === "README.md") return "/docs/project-readme";
  const relative = source.slice(5).replace(/(?:^|\/)README\.md$/, "").replace(/\.md$/, "");
  return relative ? `/docs/${relative}` : "/docs";
}

function resolveRelativeLink(source, href) {
  if (/^(?:[a-z][a-z\d+.-]*:|\/|#)/i.test(href)) return null;
  const hashIndex = href.indexOf("#");
  const fragment = hashIndex < 0 ? "" : href.slice(hashIndex);
  const withoutFragment = hashIndex < 0 ? href : href.slice(0, hashIndex);
  const queryIndex = withoutFragment.indexOf("?");
  const query = queryIndex < 0 ? "" : withoutFragment.slice(queryIndex);
  const encodedPath = queryIndex < 0 ? withoutFragment : withoutFragment.slice(0, queryIndex);
  const decoded = decodeURIComponent(encodedPath);
  if (decoded.includes("\\")) throw new Error(`Backslash link path: ${href}`);
  const target = path.posix.normalize(path.posix.join(path.posix.dirname(source), decoded));
  return { source: target, query, fragment };
}

export function resolveDocumentLink(source, href) {
  const target = resolveRelativeLink(source, href);
  if (!target?.source.endsWith(".md")) return null;
  return { ...target, source: validateDocumentSource(target.source) };
}

export function repositorySourceUrl(source, href) {
  const target = resolveRelativeLink(source, href);
  if (!target) return href;
  const segments = target.source.split("/");
  if (!/^(?:backend|frontend|supabase|scripts|\.github)\//.test(target.source)
    || segments.some((segment, index) => (segment.startsWith(".") && !(index === 0 && segment === ".github")) || segment === "superpowers")) return "";
  const encoded = segments.map(encodeURIComponent).join("/");
  return `https://github.com/gomin-diary/gomin/blob/main/${encoded}${target.query}${target.fragment}`;
}

export function analyzeMarkdown(markdown) {
  const tree = parser.parse(markdown);
  const slugger = new GithubSlugger();
  const headings = [];
  const links = [];
  const definitions = new Map();
  visit(tree, "definition", node => definitions.set(node.identifier, node.url));
  let section = "문서";
  for (const block of tree.children) {
    if (block.type === "heading" && block.depth === 2) section = toString(block);
    visit(block, node => {
      if (node.type === "heading") {
        const text = toString(node);
        headings.push({ depth: node.depth, text, id: slugger.slug(text) });
      }
      const href = node.type === "link" ? node.url : node.type === "linkReference" ? definitions.get(node.identifier) : null;
      if (href) links.push({ href, title: toString(node), section });
    });
  }
  return { links, headings };
}
