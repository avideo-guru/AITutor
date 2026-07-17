// One-tap 👍/👎 on an answer. This is the data flywheel's intake — the
// backend endpoint existed since P0.3 but nothing in the app ever called it.
// Optimistic: the tap paints immediately, reverts if the POST fails.

import React, { useState } from "react";
import { Pressable, Text, View } from "react-native";

import { sendFeedback } from "@/lib/api";
import { font, space, useTheme } from "@/lib/theme";

type Rating = "up" | "down";

export function Feedback({
  sessionId,
  initial = null,
}: {
  sessionId: string;
  initial?: Rating | null;
}) {
  const t = useTheme();
  const [rating, setRating] = useState<Rating | null>(initial);

  async function rate(r: Rating) {
    const prev = rating;
    setRating(r);
    try {
      await sendFeedback(sessionId, r);
    } catch {
      setRating(prev); // quiet revert — feedback must never block reading
    }
  }

  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: space.s }}>
      <Text style={[font.small, { color: t.muted }]}>Was this helpful?</Text>
      {(["up", "down"] as const).map((r) => (
        <Pressable
          key={r}
          onPress={() => rate(r)}
          hitSlop={8}
          style={{
            paddingVertical: 4,
            paddingHorizontal: 10,
            borderRadius: 8,
            borderWidth: 1,
            borderColor: rating === r ? t.accent : t.border,
            backgroundColor: rating === r ? t.card : "transparent",
            opacity: rating && rating !== r ? 0.45 : 1,
          }}
        >
          <Text style={font.body}>{r === "up" ? "👍" : "👎"}</Text>
        </Pressable>
      ))}
    </View>
  );
}
