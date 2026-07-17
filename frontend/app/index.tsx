// Ask — the home screen, Claude-style: greeting, one composer card with an
// attach menu, quota line, and recent questions below.

import { useQuery } from "@tanstack/react-query";
import { Link, router } from "expo-router";
import React, { useState } from "react";
import { Pressable, Text, View } from "react-native";

import { Brand } from "@/components/Brand";
import { Composer, type ComposerPhoto } from "@/components/Composer";
import { Screen } from "@/components/Screen";
import { api, uploadQuestionImage, type Me, type SessionItem } from "@/lib/api";
import { font, space, useTheme } from "@/lib/theme";
import { useStream } from "@/state/stream";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 5) return "Up late?";
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function relativeTime(iso: string): string {
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60_000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return days === 1 ? "yesterday" : `${days}d ago`;
}

function Recents() {
  const t = useTheme();
  const { data } = useQuery({
    queryKey: ["sessions"],
    queryFn: () =>
      api<{ items: SessionItem[]; next_cursor: string | null }>("/v1/sessions"),
  });
  const items = data?.items.slice(0, 5) ?? [];
  if (items.length === 0) return null;

  return (
    <View style={{ marginTop: space.xl, gap: space.xs }}>
      <View
        style={{
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: space.s,
        }}
      >
        <Text style={[font.small, { color: t.muted, textTransform: "uppercase", letterSpacing: 1 }]}>
          Recent
        </Text>
        <Link href="/history" style={[font.small, { color: t.muted }]}>
          View all →
        </Link>
      </View>
      {items.map((s) => (
        <Pressable
          key={s.id}
          onPress={() => router.push(`/thread/${s.id}`)}
          style={({ pressed }) => ({
            flexDirection: "row",
            justifyContent: "space-between",
            alignItems: "center",
            gap: space.m,
            paddingVertical: space.s + 2,
            paddingHorizontal: space.s,
            borderRadius: 10,
            backgroundColor: pressed ? t.card : "transparent",
          })}
        >
          <Text numberOfLines={1} style={[font.body, { color: t.fg, flex: 1 }]}>
            {s.question || "(photo question)"}
          </Text>
          <Text style={[font.small, { color: t.muted }]}>{relativeTime(s.created_at)}</Text>
        </Pressable>
      ))}
    </View>
  );
}

export default function Ask() {
  const t = useTheme();
  const ask = useStream((s) => s.ask);
  const [text, setText] = useState("");
  const [photo, setPhoto] = useState<ComposerPhoto | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: me } = useQuery({ queryKey: ["me"], queryFn: () => api<Me>("/v1/me") });

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const image_url = photo
        ? await uploadQuestionImage(photo.base64, photo.mime)
        : undefined;
      ask({ text: text.trim() || undefined, image_url });
      setText("");
      setPhoto(null);
      router.push("/thread/live");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen dotted>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <Brand />
        <View style={{ flexDirection: "row", gap: space.l }}>
          <Link href="/history" style={[font.small, { color: t.muted }]}>History</Link>
          <Link href="/account" style={[font.small, { color: t.muted }]}>Account</Link>
        </View>
      </View>

      <View style={{ flex: 1, justifyContent: "center", paddingVertical: space.xl }}>
        <Text
          style={[
            font.displaySerif,
            { color: t.fg, textAlign: "center", marginBottom: space.l },
          ]}
        >
          {greeting()}
        </Text>

        <Composer
          value={text}
          onChangeText={setText}
          photo={photo}
          onPhoto={setPhoto}
          onSubmit={submit}
          busy={busy}
          placeholder="Paste or type a JEE/NEET problem…"
        />

        {error && (
          <Text style={[font.small, { color: t.danger, marginTop: space.s }]}>{error}</Text>
        )}

        {me && me.questions_remaining_today !== null && (
          <Text style={[font.small, { color: t.muted, textAlign: "center", marginTop: space.s }]}>
            {me.questions_remaining_today} of {me.free_daily_limit} free questions left today
          </Text>
        )}

        <Recents />
      </View>
    </Screen>
  );
}
