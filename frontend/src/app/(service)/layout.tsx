import { UiStoreProvider } from "@/providers/ui-store-provider";
import { AuthProvider } from "@/providers/auth-provider";
import { Toast } from "@/components/toast";
import "./service.css";

export default function ServiceLayout({ children }: { children: React.ReactNode }) {
  return <div className="service-root">
    <UiStoreProvider><AuthProvider>{children}<Toast /></AuthProvider></UiStoreProvider>
  </div>;
}
