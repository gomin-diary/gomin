import path from "node:path";
import { fileURLToPath } from "node:url";
import { lstat, readFile, mkdir, writeFile } from "node:fs/promises";
import { analyzeMarkdown, documentUrl, resolveDocumentLink } from "../src/lib/docs-markdown.mjs";

async function readDocument(root, source) {
  let location = root;
  for (const part of source.split("/")) {
    location = path.join(location, part);
    try {
      if ((await lstat(location)).isSymbolicLink()) throw new Error(`Symlink document path: ${source}`);
    } catch (error) {
      if (error.code === "ENOENT") throw new Error(`Missing document: ${source}`);
      throw error;
    }
  }
  return readFile(location, "utf8");
}

export async function buildDocumentation(root) {
  const documents = [];
  const navigation = [];
  const queue = ["docs/README.md"];
  const queued = new Set(queue);
  const urls = new Set();
  for (let index = 0; index < queue.length; index++) {
    const source = queue[index];
    const url = documentUrl(source);
    if (urls.has(url)) throw new Error(`Duplicate document URL: ${url}`);
    urls.add(url);
    const markdown = await readDocument(root, source);
    const { headings, links } = analyzeMarkdown(markdown);
    documents.push({ source, slug: url.slice(6), url, title: headings[0]?.text ?? path.basename(source, ".md"), markdown, headings });
    for (const link of links) {
      const target = resolveDocumentLink(source, link.href);
      if (!target) continue;
      if (!queued.has(target.source)) { queue.push(target.source); queued.add(target.source); }
      if (index === 0) {
        const section = target.source === "README.md" ? "프로젝트" : link.section;
        let group = navigation.find(group => group.title === section);
        if (!group) { group = { title: section, items: [] }; navigation.push(group); }
        const targetUrl = documentUrl(target.source);
        if (!group.items.some(item => item.url === targetUrl)) group.items.push({ title: link.title, url: targetUrl });
      }
    }
  }
  return { documents, navigation };
}

async function main() {
  const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
  const manifest = await buildDocumentation(path.resolve(frontend, ".."));
  const output = path.join(frontend, "src/generated/docs.json");
  await mkdir(path.dirname(output), { recursive: true });
  await writeFile(output, JSON.stringify(manifest));
  process.stdout.write(`Generated ${manifest.documents.length} public documents.\n`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });
}
