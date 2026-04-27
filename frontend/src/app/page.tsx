import { CursorGlow } from "@/components/CursorGlow";
import { Footer } from "@/components/Footer";
import { Hero } from "@/components/Hero";
import { SearchPanel } from "@/components/SearchPanel";
import { StatsBar } from "@/components/StatsBar";
import { StickyHeader } from "@/components/StickyHeader";

export default function Page() {
  return (
    <main className="min-h-screen relative">
      <CursorGlow />
      <StickyHeader />
      <Hero />
      <div className="relative z-10 pb-16">
        <SearchPanel />
        <StatsBar />
      </div>
      <Footer />
    </main>
  );
}
