// Answer thread. id === "live" renders the streaming thread from the Zustand
// store (all exchanges, follow-up composer, feedback); any other id loads a
// past session directly via GET /v1/sessions/{id}.

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import React, { useEffect, useState } from "react";
import { Text, View } from "react-native";

import { Bubble } from "@/components/Bubble";
import { Button } from "@/components/Button";
import { Feedback } from "@/components/Feedback";
import { Input } from "@/components/Input";
import { Screen } from "@/components/Screen";
import { ApiError, getSession } from "@/lib/api";
import { font, space, useTheme } from "@/lib/theme";
import { useStream } from "@/state/stream";

function LiveThread() {
  const t = useTheme();
  const s = useStream();
  const qc = useQueryClient();
  const [followUp, setFollowUp] = useState("");

  useEffect(() => {
    if (s.status === "done") {
      qc.invalidateQueries({ queryKey: ["sessions"] });
      qc.invalidateQueries({ queryKey: ["me"] });
    }
  }, [s.status, qc]);

  function sendFollowUp() {
    const text = followUp.trim();
    if (!text) return;
    setFollowUp("");
    s.followUp(text);
  }

  return (
    <View style={{ gap: space.l }}>
      {s.history.map((ex, i) => (
        <View key={ex.sessionId ?? i} style={{ gap: space.s }}>
          <Bubble
            question={ex.question}
            imageUrl={ex.imageUrl}
            answer={ex.answer}
            sources={ex.sources}
          />
          {ex.sessionId && <Feedback sessionId={ex.sessionId} />}
        </View>
      ))}

      <Bubble
        question={s.question}
        imageUrl={s.imageUrl}
        answer={s.answer}
        streaming={s.status === "streaming"}
        sources={s.sources}
      />
      {s.status === "error" && (
        <Text style={[font.body, { color: t.danger }]}>{s.error}</Text>
      )}

      {s.status === "done" && (
        <View style={{ gap: space.m }}>
          {s.sessionId && <Feedback sessionId={s.sessionId} />}
          <Input
            placeholder="Ask a follow-up…"
            value={followUp}
            onChangeText={setFollowUp}
            onSubmitEditing={sendFollowUp}
            returnKeyType="send"
          />
          <Button
            label="Send follow-up"
            onPress={sendFollowUp}
            disabled={!followUp.trim()}
          />
          <Button
            label="Ask a new question"
            variant="ghost"
            onPress={() => {
              s.reset();
              router.replace("/");
            }}
          />
        </View>
      )}
    </View>
  );
}

function PastThread({ id }: { id: string }) {
  const t = useTheme();
  const { data, isLoading, error } = useQuery({
    queryKey: ["session", id],
    queryFn: () => getSession(id),
    retry: (count, err) =>
      !(err instanceof ApiError && err.status === 404) && count < 2,
  });

  if (isLoading) return <Text style={[font.body, { color: t.muted }]}>Loading…</Text>;
  if (error || !data)
    return <Text style={[font.body, { color: t.muted }]}>Session not found.</Text>;
  return (
    <View style={{ gap: space.s }}>
      <Bubble
        question={data.question}
        imageUrl={data.image_url}
        answer={data.answer ?? ""}
      />
      <Feedback sessionId={data.id} initial={data.feedback_rating} />
    </View>
  );
}

export default function Thread() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return (
    <Screen back>
      {id === "live" ? <LiveThread /> : <PastThread id={id!} />}
    </Screen>
  );
}
