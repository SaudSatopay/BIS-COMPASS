export function Footer() {
  return (
    <footer className="mt-24 border-t border-border">
      <div className="max-w-5xl mx-auto px-6 py-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-xs text-muted-foreground">
        <div>
          <span className="font-medium text-foreground">BIS Compass</span> · built for the Sigma
          Squad × Bureau of Indian Standards Hackathon · April 2026
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono">
          <span>bge-m3 + bge-reranker-v2-m3</span>
          <span>·</span>
          <span>FAISS + BM25 + RRF</span>
          <span>·</span>
          <span>Gemini 2.5 Flash</span>
        </div>
      </div>
    </footer>
  );
}
