// Page shell: safe area, background, centered 720px column on wide screens,
// optional minimal header (back + title). This replaces any nav chrome.
// `dotted` swaps the flat background for the dotted canvas (sign-in only).

import { router } from "expo-router";
import React from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Branches } from "@/components/Branches";
import { DottedBackground } from "@/components/DottedBackground";
import { font, space, useTheme } from "@/lib/theme";

export function Screen({
  title,
  back,
  children,
  scroll = true,
  dotted = false,
  branches = false,
}: {
  title?: string;
  back?: boolean;
  children: React.ReactNode;
  scroll?: boolean;
  dotted?: boolean;
  branches?: boolean;
}) {
  const t = useTheme();
  const insets = useSafeAreaInsets();

  const inner = (
    <View style={{ flex: 1, width: "100%", maxWidth: 720, padding: space.m }}>
      {(title || back) && (
        <View style={{ flexDirection: "row", alignItems: "center", marginBottom: space.l }}>
          {back && (
            <Pressable
              onPress={() => (router.canGoBack() ? router.back() : router.replace("/"))}
              hitSlop={12}
              style={{ marginRight: space.m }}
            >
              <Text style={[font.bodyLg, { color: t.muted }]}>←</Text>
            </Pressable>
          )}
          {title && <Text style={[font.title, { color: t.fg }]}>{title}</Text>}
        </View>
      )}
      {children}
    </View>
  );

  const art = branches && (
    <View
      pointerEvents="none"
      style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }}
    >
      <Branches />
    </View>
  );

  const body = scroll ? (
    <ScrollView contentContainerStyle={{ flexGrow: 1, alignItems: "center" }}>
      {inner}
    </ScrollView>
  ) : (
    <View style={{ flex: 1, alignItems: "center" }}>{inner}</View>
  );

  if (dotted) {
    return (
      <DottedBackground style={{ paddingTop: insets.top }}>
        {art}
        {body}
      </DottedBackground>
    );
  }
  return (
    <View style={{ flex: 1, backgroundColor: t.bg, paddingTop: insets.top }}>
      {art}
      {body}
    </View>
  );
}
