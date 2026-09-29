import { createStore } from "zustand/vanilla";

export type UiState = {
  isMenuOpen: boolean;
  toggleMenu: () => void;
  closeMenu: () => void;
};

export const createUiStore = () =>
  createStore<UiState>()((set) => ({
    isMenuOpen: false,
    toggleMenu: () => set((state) => ({ isMenuOpen: !state.isMenuOpen })),
    closeMenu: () => set({ isMenuOpen: false }),
  }));
