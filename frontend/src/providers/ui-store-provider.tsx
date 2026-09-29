"use client";

import { createContext, useContext, useState, type ReactNode } from "react";
import { useStore } from "zustand";
import { createUiStore, type UiState } from "@/stores/ui-store";

const UiStoreContext = createContext<ReturnType<typeof createUiStore> | null>(null);

export function UiStoreProvider({ children }: { children: ReactNode }) {
  const [store] = useState(createUiStore);

  return <UiStoreContext.Provider value={store}>{children}</UiStoreContext.Provider>;
}

export function useUiStore<T>(selector: (state: UiState) => T): T {
  const store = useContext(UiStoreContext);
  if (!store) throw new Error("useUiStore requires UiStoreProvider");
  return useStore(store, selector);
}
