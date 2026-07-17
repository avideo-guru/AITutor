// Claude-style composer: one rounded card holding a growing prompt input, a
// ＋ attach menu (camera / photo library), the attached-photo chip, and a
// circular send button. Picking lives here; the photo itself is parent state
// so submit logic stays on the screen.

import * as ImagePicker from "expo-image-picker";
import React, { useState } from "react";
import {
  Image,
  Platform,
  Pressable,
  Text,
  TextInput,
  View,
} from "react-native";

import { font, space, useTheme } from "@/lib/theme";

export type ComposerPhoto = { base64: string; mime: string; uri: string };

const pickerOptions = {
  mediaTypes: "images" as const,
  quality: 0.8,
  base64: true,
};

function toPhoto(res: ImagePicker.ImagePickerResult): ComposerPhoto | null {
  const asset = res.assets?.[0];
  if (res.canceled || !asset?.base64) return null;
  return { base64: asset.base64, mime: asset.mimeType ?? "image/jpeg", uri: asset.uri };
}

export function Composer({
  value,
  onChangeText,
  photo,
  onPhoto,
  onSubmit,
  busy,
  placeholder,
}: {
  value: string;
  onChangeText: (v: string) => void;
  photo: ComposerPhoto | null;
  onPhoto: (p: ComposerPhoto | null) => void;
  onSubmit: () => void;
  busy?: boolean;
  placeholder?: string;
}) {
  const t = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);
  const [inputHeight, setInputHeight] = useState(24);
  const canSend = !busy && (!!value.trim() || !!photo);

  async function pick(kind: "camera" | "library") {
    setMenuOpen(false);
    const res =
      kind === "camera"
        ? await ImagePicker.launchCameraAsync(pickerOptions)
        : await ImagePicker.launchImageLibraryAsync(pickerOptions);
    const picked = toPhoto(res);
    if (picked) onPhoto(picked);
  }

  const menuItem = (label: string, onPress?: () => void, hint?: string) => (
    <Pressable
      key={label}
      onPress={onPress}
      disabled={!onPress}
      style={({ pressed }) => ({
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        paddingVertical: 10,
        paddingHorizontal: space.m,
        backgroundColor: pressed ? t.bg : "transparent",
      })}
    >
      <Text style={[font.body, { color: onPress ? t.fg : t.muted }]}>{label}</Text>
      {hint && <Text style={[font.small, { color: t.muted, marginLeft: space.m }]}>{hint}</Text>}
    </Pressable>
  );

  return (
    <View
      style={{
        backgroundColor: t.inputBg,
        borderWidth: 1,
        borderColor: t.border,
        borderRadius: 16,
        padding: space.m,
        gap: space.s,
      }}
    >
      {photo && (
        <View style={{ flexDirection: "row" }}>
          <View>
            <Image
              source={{ uri: photo.uri }}
              style={{
                width: 56,
                height: 56,
                borderRadius: 8,
                borderWidth: 1,
                borderColor: t.border,
                backgroundColor: t.card,
              }}
            />
            <Pressable
              onPress={() => onPhoto(null)}
              hitSlop={8}
              style={{
                position: "absolute",
                top: -6,
                right: -6,
                width: 20,
                height: 20,
                borderRadius: 10,
                backgroundColor: t.fg,
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Text style={{ color: t.bg, fontSize: 12, lineHeight: 14, fontWeight: "700" }}>
                ×
              </Text>
            </Pressable>
          </View>
        </View>
      )}

      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder ?? "Ask anything…"}
        placeholderTextColor={t.muted}
        multiline
        onContentSizeChange={(e) =>
          setInputHeight(Math.min(144, Math.max(24, e.nativeEvent.contentSize.height)))
        }
        onKeyPress={(e) => {
          // Enter sends on web; Shift+Enter inserts a newline.
          const ne = e.nativeEvent as { key?: string; shiftKey?: boolean };
          if (Platform.OS === "web" && ne.key === "Enter" && !ne.shiftKey && canSend) {
            e.preventDefault();
            onSubmit();
          }
        }}
        style={[
          font.body,
          { color: t.fg, height: inputHeight, padding: 0 },
          Platform.OS === "web" && ({ outlineStyle: "none" } as object),
        ]}
      />

      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <View>
          <Pressable
            onPress={() => setMenuOpen((v) => !v)}
            hitSlop={8}
            style={({ pressed }) => ({
              width: 32,
              height: 32,
              borderRadius: 16,
              borderWidth: 1,
              borderColor: t.border,
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: menuOpen || pressed ? t.bg : "transparent",
            })}
          >
            <Text style={{ color: t.muted, fontSize: 18, lineHeight: 20 }}>＋</Text>
          </Pressable>

          {menuOpen && (
            <View
              style={{
                position: "absolute",
                bottom: 40,
                left: 0,
                minWidth: 200,
                backgroundColor: t.card,
                borderWidth: 1,
                borderColor: t.border,
                borderRadius: 12,
                paddingVertical: space.xs,
                zIndex: 10,
                ...(Platform.OS === "web"
                  ? ({ boxShadow: "0 4px 16px rgba(0,0,0,0.12)" } as object)
                  : {}),
              }}
            >
              {menuItem("Take photo", () => pick("camera"))}
              {menuItem("Choose photo", () => pick("library"))}
              {menuItem("Upload file", undefined, "soon")}
            </View>
          )}
        </View>

        <Pressable
          onPress={onSubmit}
          disabled={!canSend}
          style={({ pressed }) => ({
            width: 32,
            height: 32,
            borderRadius: 16,
            backgroundColor: t.accent,
            alignItems: "center",
            justifyContent: "center",
            opacity: !canSend ? 0.35 : pressed ? 0.85 : 1,
          })}
        >
          <Text style={{ color: t.accentFg, fontSize: 16, lineHeight: 18, fontWeight: "700" }}>
            ↑
          </Text>
        </Pressable>
      </View>
    </View>
  );
}
