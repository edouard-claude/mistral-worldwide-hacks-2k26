import { createContext, useContext } from "react";
import type { Lang } from "./translations";

const LanguageContext = createContext<Lang>("fr");

export const LanguageProvider = LanguageContext.Provider;

export function useLang(): Lang {
  return useContext(LanguageContext);
}
