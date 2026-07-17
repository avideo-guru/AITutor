// One Q&A exchange: the question (with optional photo) as a quiet card on
// the right — like a sent message — and the answer as plain full-width prose.
// Used by both the live thread and history threads.

import React from "react";
import { Image, Text, View } from "react-native";

import { Badge } from "@/components/Badge";
import { MathText } from "@/lib/math";
import { font, space, useTheme } from "@/lib/theme";

export function Bubble({
  question,
  imageUrl,
  answer,
  streaming,
  sources,
}: {
  question: string;
  imageUrl?: string | null;
  answer: string;
  streaming?: boolean;
  sources?: string[];
}) {
  const t = useTheme();
  return (
    <View style={{ gap: space.l }}>
      <View
        style={{
          alignSelf: "flex-end",
          maxWidth: "85%",
          backgroundColor: t.card,
          borderWidth: 1,
          borderColor: t.border,
          borderRadius: 16,
          borderBottomRightRadius: 4,
          padding: space.m,
        }}
      >
        <Text style={[font.body, { color: t.fg }]}>{question}</Text>
        {imageUrl ? (
          <Image
            source={{ uri: imageUrl }}
            style={{
              width: 220,
              height: 160,
              borderRadius: 10,
              marginTop: space.s,
              resizeMode: "contain",
              backgroundColor: t.bg,
            }}
          />
        ) : null}
      </View>

      <View>
        <MathText style={{ ...font.body, color: t.fg }}>
          {answer + (streaming ? " ▍" : "")}
        </MathText>
        {sources && sources.length > 0 && (
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: space.s, marginTop: space.m }}>
            {sources.map((s) => (
              <Badge key={s} label={s} />
            ))}
          </View>
        )}
      </View>
    </View>
  );
}
