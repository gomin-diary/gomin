"use client";

import Link from "next/link";
import { useEffect, useRef, useState, useSyncExternalStore, type CSSProperties } from "react";
import { PageShell } from "@/components/page-shell";
import { useAuth } from "@/providers/auth-provider";
import { useUiStore } from "@/providers/ui-store-provider";
import {
  collectionCategories, COLLECTION_PAGE_SIZE, createCollectionController,
  visibleCollectionItems, type CollectionDetail, type CollectionImage,
} from "@/lib/collection";
import { createApiCollectionRepository } from "@/lib/collection-api";
import { formatEncouragement } from "@/lib/diary-text";
import { filmPerforations } from "@/lib/collection-film";
import styles from "./collection-gallery.module.css";

const mobileQuery = "(max-width: 767px)";
const subscribeViewport = (listener: () => void) => {
  const query = window.matchMedia(mobileQuery);
  query.addEventListener("change", listener);
  return () => query.removeEventListener("change", listener);
};
const mobileSnapshot = () => window.matchMedia(mobileQuery).matches;
const serverViewport = () => false;
const cardPositions = [
  { x: 80, y: 103, angle: 8 }, { x: 440, y: 142, angle: 5 },
  { x: 800, y: 162, angle: 1.6 }, { x: 1160, y: 162, angle: -1.6 },
  { x: 1520, y: 142, angle: -5 }, { x: 1880, y: 103, angle: -8 },
];
const formatDate = (date: string, weekday = false) => {
  const [year, month, day] = date.split("-");
  const label = `${year}. ${month}. ${day}`;
  const week = ["일", "월", "화", "수", "목", "금", "토"][new Date(`${date}T00:00:00Z`).getUTCDay()];
  return weekday ? `${label} (${week})` : label;
};

function RecordImage({ image, hero = false }: { image: CollectionImage; hero?: boolean }) {
  const style = {
    "--image-width": `${image.width * 100}%`,
    "--image-left": `${image.left * 100}%`,
    "--image-top": `${image.top * 100}%`,
  } as CSSProperties;
  return <div className={`${styles.photo} ${hero ? styles.heroPhoto : ""}`} style={style}>
    {/* eslint-disable-next-line @next/next/no-img-element */}
    <img src={image.src} alt="" width={1672} height={941} />
  </div>;
}

function AssetIcon({ name }: { name: string }) {
  // Preserve Figma SVG root geometry and scale its wrapper, never the SVG dimensions.
  return <span className={styles.iconSlot} aria-hidden="true">
    {/* eslint-disable-next-line @next/next/no-img-element */}
    <img src={`/images/collection/${name}.svg`} alt="" />
  </span>;
}

function DetailContent({ detail }: { detail: CollectionDetail }) {
  const showToast = useUiStore((state) => state.showToast);
  return <>
    <header className={styles.detailHeading}>
      <time dateTime={detail.date}>{formatDate(detail.date, true)}</time>
      <div className={styles.titleRow}><h2 id="collection-detail-title">{detail.title}</h2><AssetIcon name="title-leaf" /></div>
      <p>{formatEncouragement(detail.caption)}</p>
    </header>
    <div className={styles.summaryCards}>
      <section className={`${styles.summaryCard} ${styles.mind}`}>
        <AssetIcon name="heart" /><div><h3>지금의 마음</h3><p>{detail.mind}</p></div>
      </section>
      <section className={`${styles.summaryCard} ${styles.concern}`}>
        <AssetIcon name="sprout" /><div><h3>주요 고민</h3><ul>{detail.concerns.map((text) => <li key={text}>{text}</li>)}</ul></div>
      </section>
      <section className={`${styles.summaryCard} ${styles.emotions}`}>
        <AssetIcon name="cloud" /><div><h3>자주 느끼는 감정</h3><ul className={styles.emotionTags}>{detail.emotions.map((text) => <li key={text}>{text}</li>)}</ul></div>
      </section>
    </div>
    <button className={styles.continueButton} type="button" onClick={() => showToast("이전 이야기 이어 보기는 아직 준비 중이에요.")}>
      <span className={styles.editIcon}><AssetIcon name="edit" /></span>이 이야기 이어서 보기
    </button>
  </>;
}

export function CollectionGallery() {
  const { member } = useAuth();
  return member ? <MemberCollection key={member.id} memberId={member.id} /> : null;
}

function MemberCollection({ memberId }: { memberId: string }) {
  const [controller] = useState(() => createCollectionController(memberId, createApiCollectionRepository()));
  const state = useSyncExternalStore(controller.subscribe, controller.getSnapshot, controller.getServerSnapshot);
  const isMobile = useSyncExternalStore(subscribeViewport, mobileSnapshot, serverViewport);
  const dialog = useRef<HTMLDialogElement>(null);
  const canvasWrapper = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement | null>(null);
  const [scale, setScale] = useState(1);
  const items = visibleCollectionItems(state);
  const start = state.page * COLLECTION_PAGE_SIZE;
  const pageItems = items.slice(start, start + COLLECTION_PAGE_SIZE);
  const selected = state.selectedId !== null;

  useEffect(() => {
    void controller.load();
    const restore = () => {
      const hash = new URLSearchParams(window.location.hash.slice(1));
      const id = hash.get("entry");
      if (id) void controller.select(id);
      else { controller.close(); requestAnimationFrame(() => trigger.current?.focus({ preventScroll: true })); }
    };
    restore();
    window.addEventListener("popstate", restore);
    return () => { window.removeEventListener("popstate", restore); controller.dispose(); };
  }, [controller]);

  useEffect(() => {
    const wrapper = canvasWrapper.current;
    if (!wrapper) return;
    const observer = new ResizeObserver(([entry]) => setScale(entry.contentRect.width / 2280));
    observer.observe(wrapper);
    return () => observer.disconnect();
  }, [state.status]);

  useEffect(() => {
    if (selected && !isMobile && dialog.current && !dialog.current.open) dialog.current.showModal();
  }, [selected, isMobile]);

  const close = () => {
    if (window.history.state?.collectionEntry === state.selectedId) window.history.back();
    else {
      const url = new URL(window.location.href); url.hash = "";
      window.history.replaceState(window.history.state, "", url);
      controller.close(); requestAnimationFrame(() => trigger.current?.focus({ preventScroll: true }));
    }
  };
  const open = (id: string, button: HTMLButtonElement) => {
    trigger.current = button;
    const url = new URL(window.location.href); url.hash = new URLSearchParams({ entry: id }).toString();
    window.history.pushState({ ...window.history.state, collectionEntry: id }, "", url);
    void controller.select(id);
  };
  const detailBody = state.detailStatus === "loading"
    ? <div className={styles.detailState} role="status">이야기를 불러오는 중이에요…</div>
    : state.detailStatus === "error"
      ? <div className={styles.detailState} role="alert">
        <h2 id="collection-detail-title">{state.detailNotFound ? "기록을 찾을 수 없어요." : "이야기를 불러오지 못했어요."}</h2>
        <p>{state.detailNotFound ? "컬렉션으로 돌아가 다른 이야기를 골라 주세요." : "연결을 확인하고 다시 시도해 주세요."}</p>
        {!state.detailNotFound && <button type="button" onClick={() => void controller.select(state.selectedId!)}>다시 시도</button>}
      </div>
      : state.detail && <DetailContent detail={state.detail} />;

  return <PageShell page="collection" contentClassName={styles.content}>
    <div className={styles.gallery} inert={isMobile && selected} aria-hidden={isMobile && selected ? true : undefined}>
      <header className={styles.intro}>
        <h1>지금까지의 모든 이야기가,<br />하나의 컬렉션으로 모여요.</h1>
        <p>작은 고민도, 소중한 하루도.<br />여기, 나만의 필름 속에.</p>
      </header>
      <nav className={styles.filters} aria-label="감정별 컬렉션">
        {collectionCategories.map((category) => <button type="button" key={category} aria-pressed={state.category === category} onClick={() => controller.filter(category)}>{category}</button>)}
      </nav>
      {state.status === "loading" ? <div className={styles.feedback} role="status">컬렉션을 불러오는 중이에요…</div>
        : state.status === "error" ? <div className={styles.feedback} role="alert">
          <h2>컬렉션을 불러오지 못했어요.</h2><p>연결을 확인하고 다시 시도해 주세요.</p>
          <button type="button" onClick={() => void controller.load()}>다시 시도</button>
        </div>
          : !items.length ? <div className={styles.feedback}>
            <h2>{state.items.length ? "이 감정의 이야기는 아직 없어요." : "아직 모아둔 이야기가 없어요."}</h2>
            <p>{state.items.length ? "다른 감정을 골라 이야기를 만나보세요." : "오늘의 마음을 털어놓고, 첫 번째 이야기를 남겨보세요."}</p>
            {state.items.length ? <button type="button" onClick={() => controller.filter("전체")}>전체 이야기 보기</button> : <Link href="/talk">털어놓기 시작하기</Link>}
          </div>
            : <>
              <section className={styles.desktopFilm} aria-label="고민일기 필름" hidden={isMobile}>
                <button className={`${styles.arrow} ${styles.previous}`} type="button" aria-label="이전 기록" disabled={state.page === 0} onClick={() => controller.move(-1)}>‹</button>
                <div className={styles.filmWrapper} ref={canvasWrapper}>
                  <div className={styles.filmCanvas} style={{ transform: `scale(${scale})` }}>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img className={styles.ribbon} src="/images/collection/film.svg" alt="" />
                    {filmPerforations.map((hole, index) => <span key={index} aria-hidden="true" className={styles.perforation}
                      style={{ left: hole.x, top: hole.y, width: hole.w, height: hole.h }}><i style={{ transform: `rotate(${hole.angle}deg)` }} /></span>)}
                    {pageItems.map((item, index) => <button type="button" key={item.id} className={styles.filmCard}
                      style={{ left: cardPositions[index].x, top: cardPositions[index].y, transform: `rotate(${cardPositions[index].angle}deg)` }}
                      aria-label={`${formatDate(item.date)} ${item.title} 상세 보기`} onClick={(event) => open(item.id, event.currentTarget)}>
                      <RecordImage image={item.image} /><time dateTime={item.date}>{formatDate(item.date)}</time><span>{item.title}</span>
                    </button>)}
                  </div>
                </div>
                <button className={`${styles.arrow} ${styles.next}`} type="button" aria-label="다음 기록" disabled={start + COLLECTION_PAGE_SIZE >= items.length} onClick={() => controller.move(1)}>›</button>
                <span className={styles.srOnly} role="status">{items.length}개 중 {start + 1}부터 {start + pageItems.length}번째 이야기</span>
              </section>
              <section className={styles.mobileFilm} aria-label="고민일기 목록" hidden={!isMobile}>
                <div className={styles.mobileCards}>{items.map((item) => <button type="button" key={item.id} className={styles.mobileCard}
                  aria-label={`${formatDate(item.date)} ${item.title} 상세 보기`} onClick={(event) => open(item.id, event.currentTarget)}>
                  <RecordImage image={item.image} /><time dateTime={item.date}>{formatDate(item.date)}</time><span>{item.title}</span>
                </button>)}</div>
                <p className={styles.mobileClosing}>모든 날들이<br />특별한 장면이 되는 곳. — 고민일기 ♡</p>
              </section>
            </>}
      <footer className={styles.closing}><p>오늘도<br />좋은 하루가 되기를.</p><p>모든 감정이 특별한 장면이 되는 곳.<br />— 고민일기 ♡</p></footer>
    </div>
    {selected && (isMobile
      ? <article className={styles.mobileDetail} aria-label="고민일기 상세">
        <div className={styles.mobileHero}>{state.detail && <RecordImage image={state.detail.image} hero />}
          <button className={styles.backButton} type="button" aria-label="컬렉션으로 돌아가기" onClick={close} autoFocus>←</button>
        </div>
        <div className={styles.mobileDetailBody}>{detailBody}</div>
      </article>
      : <dialog ref={dialog} className={styles.dialog} aria-label="고민일기 상세" onCancel={(event) => { event.preventDefault(); close(); }}
        onClick={(event) => { if (event.target === event.currentTarget) { const box = event.currentTarget.getBoundingClientRect(); if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) close(); } }}>
        <button className={styles.closeButton} type="button" aria-label="상세 닫기" onClick={close} autoFocus><AssetIcon name="close" /></button>
        {detailBody}
      </dialog>)}
  </PageShell>;
}
