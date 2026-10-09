import assert from "node:assert/strict";
import { test } from "node:test";
import { formatEncouragement } from "../src/lib/diary-text.ts";

test("two sentences in an existing paragraph render on separate lines", () => {
  assert.equal(formatEncouragement("마음이 흔들려도 괜찮아요. 당신의 속도로 걸어가요."),
    "마음이 흔들려도 괜찮아요.\n당신의 속도로 걸어가요.");
});

test("existing line breaks are preserved without adding empty lines", () => {
  assert.equal(formatEncouragement("마음이 흔들려도 괜찮아요.\n\n당신의 속도로 걸어가요."),
    "마음이 흔들려도 괜찮아요.\n당신의 속도로 걸어가요.");
});

test("single sentences and decimal numbers are not split at every period", () => {
  assert.equal(formatEncouragement("한 걸음씩 준비해도 괜찮아요"), "한 걸음씩 준비해도 괜찮아요");
  assert.equal(formatEncouragement("0.5만큼만 나아가도 괜찮아요. 잠시 쉬어 가요."),
    "0.5만큼만 나아가도 괜찮아요.\n잠시 쉬어 가요.");
  assert.equal(formatEncouragement("  "), "");
});
