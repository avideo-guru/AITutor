// The antfu-style dotted canvas. Web-only effect: react-native-web can't
// express `background-image: radial-gradient(...)`, so we inject one global
// stylesheet and tag the view with a data attribute. Native gets a plain
// themed background.

import React, { useEffect } from "react";
import { Platform, View, type ViewStyle } from "react-native";

import { useTheme } from "@/lib/theme";

const STYLE_ID = "dotted-bg-style";

export function DottedBackground({
  children,
  style,
}: {
  children: React.ReactNode;
  style?: ViewStyle;
}) {
  const t = useTheme();

  useEffect(() => {
    if (Platform.OS !== "web") return;
    let el = document.getElementById(STYLE_ID) as HTMLStyleElement | null;
    if (!el) {
      el = document.createElement("style");
      el.id = STYLE_ID;
      document.head.appendChild(el);
    }
    el.textContent = `[data-dotted="true"]{background-image:radial-gradient(${t.dot} 1px, transparent 1px);background-size:24px 24px;}`;
  }, [t.dot]);

  return (
    <View
      style={[{ flex: 1, backgroundColor: t.bg }, style]}
      // @ts-expect-error dataSet is a react-native-web prop (renders data-* attrs)
      dataSet={{ dotted: "true" }}
    >
      {children}
    </View>
  );
}
