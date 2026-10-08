export type TalkMessage = { id: string; conversation_id: string; seq_no: number; role: "user" | "assistant"; content: string; created_at: string };
export type TalkSummary = { id: string; conversation_id: string; version: number; source_until_seq_no: number; current_feeling: string; main_concerns: string[]; emotion_tags: string[]; confirmed_at: string | null; created_at: string };
export type TalkJob = { id: string; kind: "reply" | "summary"; status: "running" | "succeeded" | "failed"; source_until_seq_no: number; error_code: string | null };
export type TalkConversation = { id: string; phase: string; messages: TalkMessage[]; summaries: TalkSummary[]; jobs: TalkJob[] };
export type SummaryHandoff = { conversation_id: string; summary_id: string; version: number; confirmed: true; summary: TalkSummary; next_stage: "image_generation"; next_stage_status: "not_started" };
export type TalkApi = {
  create(): Promise<TalkConversation>;
  read(id: string): Promise<TalkConversation>;
  send(id: string, content: string, requestId: string): Promise<{ message: TalkMessage; job: TalkJob }>;
  summarize(id: string, requestId: string): Promise<TalkJob>;
  resume(id: string): Promise<TalkConversation>;
  confirm(id: string, summaryId: string): Promise<SummaryHandoff>;
  handoff(id: string, summaryId: string): Promise<SummaryHandoff>;
};
export type TalkState = {
  status: "loading" | "ready" | "error";
  view: "conversation" | "wrapup" | "summary" | "handoff";
  conversation: TalkConversation | null;
  draft: string;
  sending: boolean;
  replyPending: boolean;
  summaryStatus: "idle" | "waiting" | "loading" | "ready" | "error";
  confirming: boolean;
  error: string | null;
  replyError: string | null;
  summaryError: string | null;
  confirmError: string | null;
  handoff: SummaryHandoff | null;
};

// Unicode code points: same counting as Python len and PostgreSQL char_length.
export const messageLength = (content: string) => Array.from(content).length;
export const validMessage = (content: string) => content.trim().length > 0 && messageLength(content) <= 100;
export const canFinish = (state: TalkState) => !!state.conversation?.messages.some((message) => message.role === "user");
export const canSend = (state: TalkState) => state.status === "ready" && state.view === "conversation" && !state.sending && !state.replyPending && validMessage(state.draft);
export function enterSends({ mobile, shift, composing, keyCode }: { mobile: boolean; shift: boolean; composing: boolean; keyCode?: number }) {
  return !mobile && !shift && !composing && keyCode !== 229;
}

function failureText(kind: "reply" | "summary", code?: string | null) {
  const label = kind === "reply" ? "모리 응답" : "요약";
  return code === "AI_NOT_CONFIGURED" ? `${label} 서비스를 아직 연결하지 못했어요. 현재 단계는 보류 중이에요.`
    : `${label}을 완료하지 못했어요. 현재 단계는 보류 중이에요.`;
}

export function createTalkController(api: TalkApi, { onCreated = (_id: string) => { void _id; }, onResumed = (_id: string) => { void _id; }, pollMs = 800 } = {}) {
  let state: TalkState = { status: "ready", view: "conversation", conversation: null, draft: "", sending: false, replyPending: false,
    summaryStatus: "idle", confirming: false, error: null, replyError: null, summaryError: null, confirmError: null, handoff: null };
  let disposed = false;
  let loadGeneration = 0;
  let replyTask: Promise<void> | null = null;
  let acceptanceTask: Promise<void> | null = null;
  const listeners = new Set<() => void>();
  function patch(values: Partial<TalkState>) {
    if (disposed) return;
    state = { ...state, ...values };
    listeners.forEach((listener) => listener());
  }
  async function watch(job: TalkJob) {
    try {
      while (!disposed) {
        await new Promise((resolve) => setTimeout(resolve, pollMs));
        if (disposed) return;
        const conversation = await api.read(state.conversation!.id);
        patch({ conversation });
        const current = conversation.jobs.find((item) => item.id === job.id);
        if (!current) throw new Error("Missing job");
        if (current.status === "running") continue;
        if (current.kind === "reply") patch({ replyPending: false, replyError: current.status === "failed" ? failureText("reply", current.error_code) : null });
        else if (current.status === "failed") patch({ summaryStatus: "error", summaryError: failureText("summary", current.error_code) });
        else patch({ summaryStatus: "ready", view: "summary" });
        return;
      }
    } catch {
      // Stop on transport failure; polling is observation, never retrying execution.
      if (job.kind === "reply") patch({ replyPending: false, replyError: "모리 응답 상태를 확인하지 못했어요. 응답은 보류 중이에요." });
      else patch({ summaryStatus: "error", summaryError: "요약 상태를 확인하지 못했어요. 요약은 보류 중이에요." });
    }
  }
  const controller = {
    getSnapshot: () => state,
    subscribe(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener); }; },
    setDraft(draft: string) { patch({ draft }); },
    activate() { disposed = false; },
    async load(id: string, summaryId?: string) {
      const generation = ++loadGeneration;
      patch({ status: "loading" });
      try {
        const conversation = await api.read(id);
        if (disposed || generation !== loadGeneration) return;
        patch({ conversation, status: "ready" });
        if (summaryId) {
          const handoff = await api.handoff(id, summaryId);
          if (disposed || generation !== loadGeneration) return;
          patch({ view: "handoff", handoff });
          return;
        }
        const reply = conversation.jobs.filter((job) => job.kind === "reply").at(-1);
        const summary = conversation.jobs.filter((job) => job.kind === "summary").at(-1);
        if (reply?.status === "running") { patch({ replyPending: true }); replyTask = watch(reply); }
        else if (reply?.status === "failed") patch({ replyError: failureText("reply", reply.error_code) });
        if (conversation.phase === "summarizing") {
          patch({ view: "wrapup", summaryStatus: summary?.status === "running" ? "loading" : "error",
            summaryError: summary?.status === "failed" ? failureText("summary", summary.error_code) : null });
          if (summary?.status === "running") void watch(summary);
        } else if (conversation.phase === "reviewing" && conversation.summaries.length) patch({ view: "summary", summaryStatus: "ready" });
      } catch { if (generation === loadGeneration) patch({ status: "error", error: "저장된 대화나 확정 요약을 불러오지 못했어요." }); }
    },
    async send() {
      if (!canSend(state)) return;
      const content = state.draft;
      let acceptedDone = () => {};
      acceptanceTask = new Promise<void>((resolve) => { acceptedDone = resolve; });
      let thisReply: Promise<void> | null = null;
      // Clear only the submitted draft; later edits survive the normal waiting period.
      patch({ draft: "", sending: true, replyError: null, error: null });
      try {
        let conversation = state.conversation;
        if (!conversation) {
          conversation = await api.create();
          if (disposed) return;
          patch({ conversation }); onCreated(conversation.id);
        }
        const accepted = await api.send(conversation.id, content, crypto.randomUUID());
        if (disposed) return;
        patch({ sending: false, replyPending: accepted.job.status === "running", conversation: {
          ...conversation, messages: [...conversation.messages, accepted.message], jobs: [...conversation.jobs, accepted.job],
        } });
        if (accepted.job.status === "running") { replyTask = watch(accepted.job); thisReply = replyTask; }
      } catch { patch({ sending: false, replyPending: false, error: "메시지를 보내지 못했어요. 저장 여부를 확인할 수 없어요." }); }
      finally { acceptedDone(); }
      if (thisReply) await thisReply;
    },
    async finish() {
      if (!canFinish(state) || state.summaryStatus === "waiting" || state.summaryStatus === "loading") return;
      const accepting = state.sending;
      patch({ view: "wrapup", summaryStatus: accepting || state.replyPending ? "waiting" : "loading", summaryError: null, confirmError: null, handoff: null });
      // Selection is enabled from persistence, even when the reply is still running.
      // Settle that one reply before freezing the stored-source boundary in the RPC.
      if (accepting && acceptanceTask) await acceptanceTask;
      if (disposed) return;
      if (accepting && state.error) {
        patch({ summaryStatus: "error", summaryError: "메시지 저장 여부를 확인하지 못해 요약을 시작하지 못했어요." }); return;
      }
      if (state.replyPending && replyTask) await replyTask;
      if (disposed) return;
      if (state.replyError?.includes("상태를 확인")) {
        patch({ summaryStatus: "error", summaryError: "진행 중인 응답 상태를 확인하지 못해 요약을 시작하지 못했어요." }); return;
      }
      patch({ summaryStatus: "loading" });
      try {
        const job = await api.summarize(state.conversation!.id, crypto.randomUUID());
        patch({ conversation: { ...state.conversation!, phase: "summarizing", jobs: [...state.conversation!.jobs, job] } });
        await watch(job);
      } catch { patch({ summaryStatus: "error", summaryError: "요약을 시작하지 못했어요. 현재 단계는 보류 중이에요." }); }
    },
    async resume() {
      if (!state.conversation || state.summaryStatus === "waiting" || state.summaryStatus === "loading" || state.confirming) return;
      try {
        const conversation = await api.resume(state.conversation.id);
        patch({ conversation, view: "conversation", summaryStatus: "idle", summaryError: null, confirmError: null, handoff: null });
        if (!disposed) onResumed(conversation.id);
      } catch { patch({ error: "같은 대화로 돌아가지 못했어요. 현재 단계는 보류 중이에요." }); }
    },
    async confirm() {
      const summary = state.conversation?.summaries.at(-1);
      if (!summary || state.view !== "summary" || state.summaryStatus !== "ready" || state.confirming) return;
      patch({ confirming: true, confirmError: null });
      try {
        const handoff = await api.confirm(state.conversation!.id, summary.id);
        patch({ confirming: false, handoff, view: "handoff" });
      } catch { patch({ confirming: false, confirmError: "요약을 확정하지 못했어요. 대화가 추가되었다면 다시 이야기하기로 돌아가 새 요약을 확인해 주세요." }); }
    },
    dispose() { disposed = true; loadGeneration++; listeners.clear(); },
  };
  return controller;
}
