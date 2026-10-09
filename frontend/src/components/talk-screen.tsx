"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState, useSyncExternalStore, type KeyboardEvent } from "react";
import { PageShell } from "@/components/page-shell";
import { useAuth } from "@/providers/auth-provider";
import { talkApi } from "@/lib/talk-api";
import { canFinish, canSend, createTalkController, enterSends, messageLength, type TalkApi, type TalkSummary, type SummaryHandoff } from "@/lib/talk";
import styles from "./talk-screen.module.css";

export function TalkScreen({ conversationId, summaryId }: { conversationId?: string; summaryId?: string }) {
  const { member } = useAuth();
  return member ? <TalkSession key={`${member.id}:${conversationId ?? "new"}:${summaryId ?? ""}`} conversationId={conversationId} summaryId={summaryId} /> : null;
}

function SummarySections({ summary }: { summary: TalkSummary }) {
  return <div className={styles.sections}>
    <section className={styles.card}><h2>지금의 마음</h2><p>{summary.current_feeling}</p></section>
    <section className={styles.card}><h2>주요 고민</h2><ul>{summary.main_concerns.map((concern, index) => <li key={index}>{concern}</li>)}</ul></section>
    <section className={styles.card}><h2>자주 느끼는 감정</h2><ul className={styles.tags}>{summary.emotion_tags.map((emotion, index) => <li key={index}>{emotion}</li>)}</ul></section>
  </div>;
}

// Forward the confirmed identifier to the existing image owner, without starting
// image generation or claiming collection success at confirmation time.
export function ConfirmedSummaryBoundary({ handoff }: { handoff: SummaryHandoff }) {
  return <section className={styles.handoff} aria-label="확정 요약 전달">
    <p role="status">요약을 확정했어요. 이 내용으로 그림일기를 만들 수 있어요.</p>
    <p>이미지 생성과 컬렉션 저장은 아직 시작되지 않았어요.</p>
    <Link className={styles.primary} href={`/talk?summary=${encodeURIComponent(handoff.summary_id)}`}>그림일기 만들기로 이동</Link>
    <Link href={`/talk/${handoff.conversation_id}/handoff/${handoff.summary_id}`}>확정 요약 보기</Link>
  </section>;
}

export function TalkSession({ conversationId, summaryId, api = talkApi, onConfirmed }: {
  conversationId?: string; summaryId?: string; api?: TalkApi; onConfirmed?: (handoff: SummaryHandoff) => void;
}) {
  const [controller] = useState(() => {
    const showConversation = (id: string) => window.history.replaceState(null, "", `/talk/${id}`);
    return createTalkController(api, { onCreated: showConversation, onResumed: showConversation });
  });
  const state = useSyncExternalStore(controller.subscribe, controller.getSnapshot, controller.getSnapshot);
  const transcript = useRef<HTMLDivElement>(null);
  const composing = useRef(false);
  const delivered = useRef<string | null>(null);
  useEffect(() => {
    controller.activate();
    if (conversationId) void controller.load(conversationId, summaryId);
    return () => controller.dispose();
  }, [controller, conversationId, summaryId]);
  useEffect(() => {
    const element = transcript.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [state.conversation?.messages.length, state.replyPending]);
  useEffect(() => {
    if (state.handoff && delivered.current !== state.handoff.summary_id) {
      delivered.current = state.handoff.summary_id;
      onConfirmed?.(state.handoff);
    }
  }, [state.handoff, onConfirmed]);
  const busySummary = state.summaryStatus === "waiting" || state.summaryStatus === "loading";
  const summary = state.handoff?.summary ?? state.conversation?.summaries.at(-1);
  const count = messageLength(state.draft);
  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    const mobile = window.matchMedia("(max-width: 767px), (pointer: coarse)").matches;
    if (event.key === "Enter" && enterSends({ mobile, shift: event.shiftKey, composing: composing.current || event.nativeEvent.isComposing, keyCode: event.keyCode })) {
      event.preventDefault(); void controller.send();
    }
  }
  return <PageShell page="talk" contentClassName={styles.content}>
    <div className={styles.surface}>
      <div className={styles.topbar}>
        {state.view === "conversation" ? <Link className={styles.back} href="/" aria-label="홈으로 돌아가기"><Image src="/images/navigation/back.svg" width={24} height={24} alt="" /></Link>
          : <button className={styles.back} type="button" aria-label="같은 대화로 돌아가기" disabled={busySummary || state.confirming} onClick={() => void controller.resume()}><Image src="/images/navigation/back.svg" width={24} height={24} alt="" /></button>}
        <span>{state.view === "handoff" ? "확정 요약" : "털어놓기"}</span>
      </div>
      {state.status === "loading" ? <p className={styles.notice} role="status">저장된 대화를 불러오고 있어요.</p>
        : state.status === "error" ? <p className={styles.error} role="alert">{state.error}</p>
        : state.view === "summary" || state.view === "handoff" ? <div className={styles.summary}>
          <div className={styles.heading}><Image src="/images/navigation/profile-character.png" width={96} height={80} alt="모리" /><h1>지금까지의 고민 요약</h1><p>네 이야기를 차곡차곡 정리했어요.</p></div>
          {summary ? <><p className={styles.version}>요약 {summary.version} · 저장 원문 {summary.source_until_seq_no}번째 메시지까지</p><SummarySections summary={summary} /></> : null}
          {state.confirmError ? <p className={styles.error} role="alert">{state.confirmError}</p> : null}
          {state.error ? <p className={styles.error} role="alert">{state.error}</p> : null}
          {state.handoff ? <ConfirmedSummaryBoundary handoff={state.handoff} /> : <div className={styles.actions}>
            <button className={styles.primary} disabled={state.confirming} onClick={() => void controller.confirm()}>{state.confirming ? "요약을 확정하고 있어요…" : "이 내용으로 정리하기"}</button>
            <button className={styles.secondary} disabled={state.confirming} onClick={() => void controller.resume()}>다시 이야기하기</button>
          </div>}
        </div> : <>
          <div className={styles.transcript} ref={transcript} aria-label="저장된 대화">
            <div className={styles.heading}><Image src="/images/navigation/profile-character.png" width={96} height={80} alt="모리" /><h1>무엇이든 이야기해줘,<br />지금 네 마음을 들을게.</h1></div>
            <ol className={styles.messages}>{state.conversation?.messages.map((message) => <li key={message.id} className={message.role === "user" ? styles.user : styles.assistant}>
              {message.role === "assistant" ? <Image src="/images/navigation/profile-character.png" width={48} height={40} alt="" /> : null}
              <div><span className={styles.speaker}>{message.role === "user" ? "나" : "모리"}</span><p className={styles.bubble}>{message.content}</p><time dateTime={message.created_at}>{new Intl.DateTimeFormat("ko-KR", { dateStyle: "short", timeStyle: "short" }).format(new Date(message.created_at))}</time></div>
            </li>)}</ol>
            {state.replyPending ? <p className={styles.notice} role="status">모리가 네 이야기를 듣고 있어요… 입력은 계속할 수 있어요.</p> : null}
            {state.replyError ? <p className={styles.error} role="alert">{state.replyError}</p> : null}
          </div>
          <div className={styles.wrapup}>
            {state.view === "conversation" ? <button className={styles.finish} disabled={!canFinish(state)} onClick={() => void controller.finish()}>대화 마무리하기 <small>지금까지의 이야기를 정리해 볼게요</small></button>
              : <><h2>지금까지의 이야기를 정리하고 있어요.</h2>
                {state.summaryStatus === "waiting" ? <p role="status">진행 중인 모리 응답을 기다린 뒤, 저장된 대화를 요약할게요.</p> : null}
                {state.summaryStatus === "loading" ? <p role="status">저장된 원문으로 요약을 만들고 있어요…</p> : null}
                {state.summaryError ? <p className={styles.error} role="alert">{state.summaryError}</p> : null}
                {state.summaryStatus === "error" ? <button className={styles.secondary} onClick={() => void controller.resume()}>다시 이야기하기</button> : null}
              </>}
          </div>
          {state.error ? <p className={styles.error} role="alert">{state.error}</p> : null}
          <form className={styles.composer} onSubmit={(event) => { event.preventDefault(); void controller.send(); }}>
            <label className={styles.inputLabel} htmlFor="talk-message">메시지</label>
            <textarea id="talk-message" aria-describedby="talk-count talk-input-hint" aria-invalid={count > 100} value={state.draft} placeholder="메시지를 입력하세요…" rows={2} onChange={(event) => controller.setDraft(event.target.value)} onCompositionStart={() => { composing.current = true; }} onCompositionEnd={() => { composing.current = false; }} onKeyDown={onKeyDown} />
            <div className={styles.composerFooter}><span id="talk-count" className={count > 100 ? styles.error : ""}>{count}/100</span><button className={styles.send} type="submit" disabled={!canSend(state)} aria-label="메시지 전송">↑</button></div>
            <p id="talk-input-hint" className={styles.hint}>{busySummary ? "작성 중인 내용은 요약에 포함되지 않아요." : <><span className={styles.desktopHint}>Enter 전송 · Shift+Enter 줄바꿈</span><span className={styles.mobileHint}>Enter 줄바꿈 · 버튼으로 전송</span></>}</p>
          </form>
        </>}
    </div>
  </PageShell>;
}
