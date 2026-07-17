// Design tokens — AITutor.md §4.1. Monochrome + one indigo accent, system
// fonts, one type scale. This file IS the design system.

import { Platform, useColorScheme } from "react-native";

export const palette = {
  light: {
    bg: "#FAFAF8",
    card: "#FFFFFF",
    inputBg: "#FFFFFF",
    fg: "#1A1A1A",
    muted: "#6B6B66",
    border: "#E6E6E0",
    dot: "#DBDBD2",
    accent: "#4F46E5",
    accentFg: "#FFFFFF",
    danger: "#B91C1C",
  },
  dark: {
    bg: "#0A0A0B",
    card: "#161618",
    inputBg: "#131315",
    fg: "#EDEDEA",
    muted: "#9A9A94",
    border: "#26262A",
    dot: "#222226",
    accent: "#818CF8",
    accentFg: "#101012",
    danger: "#F87171",
  },
};

export type Theme = typeof palette.light;

// Display serif — the one warm note in an otherwise utilitarian system
// (greetings and headlines only, never UI chrome or body text).
export const serif = Platform.select({
  web: "Georgia, 'Iowan Old Style', 'Palatino Linotype', 'Times New Roman', serif",
  default: "serif",
});

// The one type scale: 15 / 17 / 22 / 28, line-height 1.6 for reading.
export const font = {
  small: { fontSize: 13, lineHeight: 20 },
  body: { fontSize: 15, lineHeight: 24 },
  bodyLg: { fontSize: 17, lineHeight: 27 },
  title: { fontSize: 22, lineHeight: 30, fontWeight: "600" as const },
  display: { fontSize: 28, lineHeight: 36, fontWeight: "700" as const },
  displaySerif: {
    fontSize: 36,
    lineHeight: 44,
    fontWeight: "400" as const,
    fontFamily: serif,
  },
};

export const space = { xs: 4, s: 8, m: 16, l: 24, xl: 40 };

export function useTheme(): Theme {
  return palette[useColorScheme() === "dark" ? "dark" : "light"];
}
