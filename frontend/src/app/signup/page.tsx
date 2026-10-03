import type { Metadata } from "next";
import { SignupForm } from "@/components/signup-form";
import { AuthPage } from "@/components/auth-page";
import { sharedPages } from "@/lib/shared-pages";

export const metadata: Metadata = { title: `${sharedPages.signup.title} | 고민일기` };

export default function Page() {
  return <AuthPage mode="signup"><SignupForm /></AuthPage>;
}
