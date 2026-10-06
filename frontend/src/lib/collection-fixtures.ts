import type { CollectionRecord, CollectionImage } from "./collection";

// Public local seed member IDs only. Unknown members have an empty mock collection.
export const collectionFixtureMembers = [
  "00000000-0000-4000-8000-000000000001",
  "00000000-0000-4000-8000-000000000002",
  "00000000-0000-4000-8000-000000000003",
] as const;
// Exact reference-photo crops supplied by Figma 84:893–918, normalized to a 320×300 slot.
const crops: CollectionImage[] = [
  { src: "/images/collection/reference.png", width: 2907.826 / 320, left: -252.17 / 320, top: -679.57 / 300 },
  { src: "/images/collection/reference.png", width: 2850 / 320, left: -647.95 / 320, top: -698.86 / 300 },
  { src: "/images/collection/reference.png", width: 3040 / 320, left: -1132.73 / 320, top: -782.73 / 300 },
  { src: "/images/collection/reference.png", width: 3021.687 / 320, left: -1546.02 / 320, top: -784.34 / 300 },
  { src: "/images/collection/reference.png", width: 2972.444 / 320, left: -1955.56 / 320, top: -770.89 / 300 },
  { src: "/images/collection/reference.png", width: 2866.286 / 320, left: -2318.86 / 320, top: -725.14 / 300 },
];
const stories: Omit<CollectionRecord, "id" | "memberId" | "image">[] = [
  { date: "2025-08-28", title: "조금 더, 나답게", caption: "오늘도 조금씩, 나에게 가까워지는 중이에요.",
    mind: "새로운 환경이 아직은 낯설고 긴장되지만,\n잘 해내고 싶은 마음이 커요.\n조금 더 나답게, 천천히 적응하고 싶어요.",
    concerns: ["새로운 환경에 대한 긴장감", "잘 해낼 수 있을지에 대한 걱정", "나다운 모습을 잃지 않을까 하는 불안"],
    emotions: ["긴장", "불안함", "걱정", "설렘", "기대"], categories: ["불안", "관계"] },
  { date: "2025-08-31", title: "괜찮아, 잘하고 있어", caption: "작은 걸음도 나를 앞으로 데려가요.",
    mind: "다른 사람과 비교하다 보니 나만 뒤처진 것 같았어요. 오늘은 내가 해낸 작은 일부터 돌아보려고 해요.",
    concerns: ["친구들과 비교하게 되는 마음", "내 속도를 믿고 싶은 마음", "작은 성취를 알아주기"],
    emotions: ["걱정", "안도", "기대"], categories: ["기쁨", "일상"] },
  { date: "2025-09-03", title: "비가 와도, 나는", caption: "마음에 비가 내리는 날도 괜찮아요.",
    mind: "괜히 마음이 가라앉는 하루였어요. 억지로 밝아지려 하기보다 지금의 감정을 천천히 만나보고 싶어요.",
    concerns: ["이유 없이 무거워지는 마음", "쉬어도 괜찮을지에 대한 고민", "나를 돌보는 시간"],
    emotions: ["슬픔", "외로움", "차분함"], categories: ["슬픔", "일상"] },
  { date: "2025-09-05", title: "오늘도, 좋은 하루", caption: "지금도 충분히 잘하고 있어요.",
    mind: "시험이 다가오면서 괜히 더 불안해졌어.\n준비는 하고 있는데, 잘 하고 있는 건지\n자꾸만 걱정이 되네.",
    concerns: ["시험 준비에 대한 불안감", "계획대로 하고 있는지에 대한 걱정", "결과가 좋지 않을까 봐 두려운 마음"],
    emotions: ["불안함", "자신감 부족", "초조함", "걱정", "예민함"], categories: ["불안", "일상"] },
  { date: "2025-09-07", title: "다시, 피어나는 마음", caption: "나의 마음도 다시 피어날 거예요.",
    mind: "친구와 솔직하게 이야기하고 나니 마음이 조금 가벼워졌어요. 서로의 마음을 들을 수 있어 고마웠어요.",
    concerns: ["오해를 풀기 위한 대화", "내 마음을 표현하는 방법", "관계를 소중히 지키기"],
    emotions: ["안도", "기쁨", "고마움"], categories: ["기쁨", "관계"] },
  { date: "2025-09-12", title: "앞으로도, 천천히", caption: "서두르지 않아도 괜찮아요.",
    mind: "앞으로의 일이 아직 선명하지 않지만, 오늘의 나를 믿어보고 싶어요. 내 속도로 천천히 걸어갈 거예요.",
    concerns: ["미래에 대한 고민", "나에게 맞는 속도 찾기", "오늘을 소중히 보내기"],
    emotions: ["기대", "걱정", "평온"], categories: ["불안", "일상"] },
];
export const collectionFixtures: CollectionRecord[] = [
  ...stories.map((story, index) => ({ ...story, image: crops[index], id: `local-1-${index + 1}`, memberId: collectionFixtureMembers[0] })),
  ...stories.slice(0, 2).map((story, index) => ({
    ...story, title: index ? "내 속도로 걷기" : "작은 용기를 내본 날", date: `2025-09-${15 + index}`,
    mind: "오늘은 작은 용기를 내어 내 마음을 전했어요. 서두르지 않고 나만의 속도로 걸어가고 싶어요.",
    image: crops[index], id: `local-1-${index + 7}`, memberId: collectionFixtureMembers[0],
  })),
  { ...stories[4], title: "함께여서 고마운 하루", image: crops[4], id: "local-2-1", memberId: collectionFixtureMembers[1] },
  { ...stories[2], title: "잠시 쉬어가도 괜찮아", image: crops[2], id: "local-2-2", memberId: collectionFixtureMembers[1] },
];
