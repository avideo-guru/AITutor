// The wordmark. One text element, two sizes — used on sign-in and the home
// header so the brand renders identically everywhere.

import React from "react";
import { Text, View } from "react-native";

import { font, useTheme } from "@/lib/theme";

export function Brand({ size = "sm" }: { size?: "sm" | "lg" }) {
  const t = useTheme();
  const base = size === "lg" ? font.display : font.title;
  return (
    <View style={{ flexDirection: "row", alignItems: "baseline" }}>
      <Text style={[base, { color: t.fg, letterSpacing: -0.5 }]}>AITutor</Text>
      <Text style={[base, { color: t.accent }]}>.</Text>
    </View>
  );
}
