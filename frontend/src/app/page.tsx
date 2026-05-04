import { CursorGlow } from "@/components/CursorGlow";
import { EvalPanel } from "@/components/EvalPanel";
import { Footer } from "@/components/Footer";
import { Hero } from "@/components/Hero";
import { SearchPanel } from "@/components/SearchPanel";
import { StatsBar } from "@/components/StatsBar";
import { StickyHeader } from "@/components/StickyHeader";
import { WelcomeModal } from "@/components/WelcomeModal";

export default function Page() {
  return (
    <main className="min-h-screen relative">
      <CursorGlow />
      <StickyHeader />
      <Hero />
      <div id="search" className="relative z-10 pt-24 sm:pt-28 pb-16 scroll-mt-16">
        <SearchPanel />
        <StatsBar />
        <EvalPanel />
      </div>
      <Footer />
      <WelcomeModal />
    </main>
  );
}
