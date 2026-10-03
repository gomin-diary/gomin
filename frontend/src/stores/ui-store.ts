import { createStore } from "zustand/vanilla";

type Toast = {
  id: number;
  message: string;
  action?: { label: string; onClick: () => void };
};

export type UiState = {
  isMenuOpen: boolean;
  toggleMenu: () => void;
  closeMenu: () => void;
  toast: Toast | null;
  toastSequence: number;
  showToast: (message: string, action?: Toast["action"]) => number;
  dismissToast: (id: number) => void;
};

export const createUiStore = () =>
  createStore<UiState>()((set) => ({
    isMenuOpen: false,
    toggleMenu: () => set((state) => ({ isMenuOpen: !state.isMenuOpen })),
    closeMenu: () => set({ isMenuOpen: false }),
    toast: null,
    toastSequence: 0,
    showToast: (message, action) => {
      let id = 0;
      set((state) => {
        if (state.toast?.message === message) {
          id = state.toast.id;
          return state;
        }
        id = state.toastSequence + 1;
        return { toastSequence: id, toast: { id, message, action } };
      });
      return id;
    },
    dismissToast: (id) => set((state) => state.toast?.id === id ? { toast: null } : state),
  }));
