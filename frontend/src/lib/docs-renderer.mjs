import { createElement } from "react";
import Markdown, { defaultUrlTransform } from "react-markdown";
import remarkGfm from "remark-gfm";
import { SKIP, visit } from "unist-util-visit";
import { analyzeMarkdown, repositorySourceUrl, resolveDocumentLink } from "./docs-markdown.mjs";

function assignHeadingIds(options) {
  return tree => {
    let index = 0;
    visit(tree, "element", node => {
      if (node.properties.dataFootnotes) return SKIP;
      if (/^h[1-6]$/.test(node.tagName)) {
        node.properties.id = options.headings[index++]?.id;
      }
    });
  };
}

export function MarkdownContent({ markdown, source, documents, Diagram }) {
  const { headings } = analyzeMarkdown(markdown);
  return createElement(Markdown, {
    skipHtml: true,
    remarkPlugins: [remarkGfm],
    remarkRehypeOptions: { footnoteLabel: "각주", footnoteBackLabel: "본문으로 돌아가기" },
    rehypePlugins: [[assignHeadingIds, { headings }]],
    urlTransform: (href, key) => {
      const safe = defaultUrlTransform(href);
      if (!safe) return "";
      const target = resolveDocumentLink(source, safe);
      if (!target) return key === "href" ? repositorySourceUrl(source, safe) : safe;
      const document = documents.find(document => document.source === target.source);
      return document ? document.url + target.query + target.fragment : "";
    },
    components: {
      pre: ({ node, children }) => {
        const code = node?.children.find(child => child.type === "element" && child.tagName === "code");
        if (code?.properties?.className?.includes("language-mermaid")) {
          const value = code.children.filter(child => child.type === "text").map(child => child.value).join("").trimEnd();
          return createElement(Diagram, { code: value, key: value });
        }
        return createElement("pre", null, children);
      },
    },
  }, markdown);
}
