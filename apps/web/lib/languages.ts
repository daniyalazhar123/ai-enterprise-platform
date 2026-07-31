export const LANGUAGES = [
  { code: "en", name: "English", native_name: "English" },
  { code: "zh", name: "Chinese", native_name: "中文" },
  { code: "es", name: "Spanish", native_name: "Español" },
  { code: "fr", name: "French", native_name: "Français" },
  { code: "de", name: "German", native_name: "Deutsch" },
  { code: "ja", name: "Japanese", native_name: "日本語" },
  { code: "ko", name: "Korean", native_name: "한국어" },
  { code: "pt", name: "Portuguese", native_name: "Português" },
  { code: "ru", name: "Russian", native_name: "Русский" },
  { code: "ar", name: "Arabic", native_name: "العربية" },
];

export function getLanguageName(code: string): string {
  return LANGUAGES.find((l) => l.code === code)?.name || code;
}

export function getNativeName(code: string): string {
  return LANGUAGES.find((l) => l.code === code)?.native_name || code;
}