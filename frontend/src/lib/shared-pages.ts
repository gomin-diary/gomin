export const navigationItems = [
  { href: "/", label: "홈", icon: "home" },
  { href: "/guide", label: "가이드", icon: "guide" },
  { href: "/collection", label: "컬렉션", icon: "collection" },
] as const;

export type PageId = "home" | "guide" | "collection" | "login" | "signup" | "talk";
type Background = { asset: string; width: number; height: number };
const desktop = (asset: string): Background => ({ asset, width: 2560, height: 1440 });
const mobile = (asset: string): Background => ({ asset, width: 1440, height: 3120 });
const authBackgrounds = { desktop: desktop("login-desktop"), mobile: mobile("login-mobile") };

export const sharedPages: Record<PageId, {
  title: string;
  desktop: Background;
  mobile: Background | null;
  mobileColor?: string;
  navigation: "both" | "desktop" | "none";
}> = {
  home: { title: "홈", desktop: desktop("home-desktop"), mobile: mobile("home-mobile"), navigation: "both" },
  guide: { title: "가이드", desktop: desktop("login-desktop"), mobile: null, mobileColor: "#fcfaf4", navigation: "both" },
  collection: { title: "컬렉션", desktop: desktop("collection-desktop"), mobile: null, mobileColor: "#0b0e0d", navigation: "both" },
  login: { title: "로그인", ...authBackgrounds, navigation: "desktop" },
  signup: { title: "회원가입", ...authBackgrounds, navigation: "desktop" },
  talk: { title: "대화", desktop: desktop("talk-desktop"), mobile: mobile("talk-mobile"), navigation: "none" },
};
