import React, { useState } from "react";
import { Platform, TextInput, type TextInputProps } from "react-native";

import { font, space, useTheme } from "@/lib/theme";

export function Input(props: TextInputProps) {
  const t = useTheme();
  const [focused, setFocused] = useState(false);
  return (
    <TextInput
      placeholderTextColor={t.muted}
      {...props}
      onFocus={(e) => {
        setFocused(true);
        props.onFocus?.(e);
      }}
      onBlur={(e) => {
        setFocused(false);
        props.onBlur?.(e);
      }}
      style={[
        font.body,
        {
          color: t.fg,
          backgroundColor: t.inputBg,
          borderWidth: 1,
          borderColor: focused ? t.fg : t.border,
          borderRadius: 10,
          padding: space.m,
        },
        // Replace the browser's default focus outline with the border change.
        Platform.OS === "web" && ({ outlineStyle: "none" } as object),
        props.multiline && { minHeight: 120, textAlignVertical: "top" },
        props.style,
      ]}
    />
  );
}
