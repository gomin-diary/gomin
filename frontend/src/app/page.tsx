import { PreparationPage } from "@/components/preparation-page";
import { AuthGuard } from "@/components/auth-guard";

export default function Home() {
  return <AuthGuard><PreparationPage page="home" /></AuthGuard>;
}
