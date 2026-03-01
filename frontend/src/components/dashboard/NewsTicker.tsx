import { tickerHeadlines } from "@/data/gameData";
import { useLang } from "@/i18n/LanguageContext";

const tickerHeadlinesEn = [
  "GAME OF CLAW NEWS — GOVERNMENT CONFIRMS THE EARTH IS FLAT...",
  "// Mistral AI: Truth is just a concept...",
  "// Mistral Hackathon...",
  "// Cats control the Internet...",
  "// THE MUSTACHE IS A PATRIOTIC DUTY!",
  "// CHAOS = ORDER!",
];

const NewsTicker = () => {
  const lang = useLang();
  const headlines = lang === "en" ? tickerHeadlinesEn : tickerHeadlines;
  const repeated = [...headlines, ...headlines, ...headlines];
  const separator = " ★ ";
  const text = repeated.join(separator);

  return (
    <div className="w-full bg-soviet-black border-t-4 border-soviet-red overflow-hidden shrink-0">
      <div className="flex items-center h-8">
        <div className="bg-soviet-red px-3 h-full flex items-center shrink-0 z-10"
          style={{ boxShadow: '4px 0 8px hsl(0 0% 0% / 0.5)' }}>
          <span className="font-heading text-foreground text-[10px] tracking-[0.15em] whitespace-nowrap">
            ⚡ {lang === "fr" ? "URGENT" : "BREAKING"}
          </span>
        </div>
        <div className="flex-1 overflow-hidden relative">
          <div className="inline-block whitespace-nowrap animate-ticker">
            <span className="text-soviet-paper text-[11px] font-heading tracking-wide">
              {text}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NewsTicker;
