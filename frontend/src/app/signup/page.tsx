import { googleOAuthNotice } from "@/lib/google-oauth";
import type { Metadata } from "next";
import { SignupForm } from "@/components/signup-form";
import { AuthPage } from "@/components/auth-page";
import { sharedPages } from "@/lib/shared-pages";

export const metadata: Metadata = { title: `${sharedPages.signup.title} | 고민일기` };

export default async function Page({ searchParams }: { searchParams: Promise<{ oauth_error?: string }> }) {
  const { oauth_error } = await searchParams;
  return <AuthPage mode="signup"><SignupForm initialNotice={googleOAuthNotice(oauth_error)} /></AuthPage>;
}
