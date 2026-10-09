const sentenceSegmenter = new Intl.Segmenter("ko", { granularity: "sentence" });

export function formatEncouragement(text: string): string {
  return Array.from(sentenceSegmenter.segment(text), ({ segment }) => segment.trim())
    .filter(Boolean)
    .join("\n");
}
