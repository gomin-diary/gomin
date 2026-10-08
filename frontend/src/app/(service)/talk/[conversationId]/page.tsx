import { AuthGuard } from "@/components/auth-guard";
import { TalkScreen } from "@/components/talk-screen";

export default async function Page({ params }: { params: Promise<{ conversationId: string }> }) {
  const { conversationId } = await params;
  return <AuthGuard><TalkScreen conversationId={conversationId} /></AuthGuard>;
}
