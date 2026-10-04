import { AuthPage } from "@/components/auth-page";
import { GoogleOAuthResult } from "@/components/google-oauth-result";
export default async function Page({ searchParams }: { searchParams: Promise<{ result?: string; error?: string }> }) {
  const params = await searchParams;
  return <AuthPage mode="login"><GoogleOAuthResult result={params.result ?? "error"} errorCode={params.error} /></AuthPage>;
}
