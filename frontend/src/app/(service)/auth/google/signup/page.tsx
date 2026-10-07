import { AuthPage } from "@/components/auth-page";
import { GoogleSignupForm } from "@/components/google-signup-form";
export default function Page() {
  return <AuthPage mode="signup"><GoogleSignupForm /></AuthPage>;
}
