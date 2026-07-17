// Sign-in, calm neo-minimalist. Wide screens: asymmetric 60/40 split — the
// geometric lattice grows on the open left panel behind a mono tag and the
// pitch line, the form sits right of a hairline divider. Narrow screens: one
// centered column. Focus = sharp ink border (Input), primary = monochrome
// ink button; the indigo accent stays confined to the Brand dot. Elements
// tagged data-animate get the GSAP entrance stagger on web.

import React, { useState } from "react";
import {
  ActivityIndicator,
  Platform,
  Pressable,
  Text,
  useWindowDimensions,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Branches } from "@/components/Branches";
import { Brand } from "@/components/Brand";
import { Button } from "@/components/Button";
import { GoogleG } from "@/components/GoogleG";
import { Input } from "@/components/Input";
import { supabase } from "@/lib/auth";
import { useEntrance } from "@/lib/entrance";
import { font, space, useTheme } from "@/lib/theme";

// react-native-web forwards dataSet to data-* attributes; RN types omit it.
const animate = { dataSet: { animate: "1" } } as object;

const mono = Platform.select({
  web: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
  default: "monospace",
});

function GoogleButton({ onPress }: { onPress: () => void }) {
  const t = useTheme();
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => ({
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "center",
        gap: space.s + 2,
        backgroundColor: t.card,
        borderWidth: 1,
        borderColor: t.border,
        borderRadius: 8,
        paddingVertical: 12,
        opacity: pressed ? 0.85 : 1,
      })}
    >
      <GoogleG size={18} />
      <Text style={[font.body, { color: t.fg, fontWeight: "600" }]}>
        Continue with Google
      </Text>
    </Pressable>
  );
}

// Monochrome primary: solid ink, no accent color. Utility over decoration.
function InkButton({
  label,
  onPress,
  disabled,
  loading,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
}) {
  const t = useTheme();
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      style={({ pressed }) => ({
        backgroundColor: t.fg,
        borderRadius: 8,
        paddingVertical: 12,
        paddingHorizontal: space.l,
        alignItems: "center",
        opacity: disabled || loading ? 0.4 : pressed ? 0.8 : 1,
      })}
    >
      {loading ? (
        <ActivityIndicator color={t.bg} />
      ) : (
        <Text style={[font.body, { color: t.bg, fontWeight: "600" }]}>{label}</Text>
      )}
    </Pressable>
  );
}

function Divider() {
  const t = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: space.m }}>
      <View style={{ flex: 1, height: 1, backgroundColor: t.border }} />
      <Text style={[font.small, { color: t.muted }]}>or</Text>
      <View style={{ flex: 1, height: 1, backgroundColor: t.border }} />
    </View>
  );
}

export default function SignIn() {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const wide = width >= 900;

  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEntrance();

  async function submit() {
    setBusy(true);
    setError(null);
    setNotice(null);
    const { error } =
      mode === "signin"
        ? await supabase.auth.signInWithPassword({ email, password })
        : await supabase.auth.signUp({ email, password });
    if (error) setError(error.message);
    else if (mode === "signup") setNotice("Check your email to confirm your account.");
    setBusy(false);
    // On success the auth gate in _layout redirects automatically.
  }

  async function google() {
    setError(null);
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: Platform.OS === "web" ? { redirectTo: window.location.origin } : {},
    });
    if (error) setError(error.message);
  }

  const form = (
    <View style={{ width: "100%", maxWidth: 360, gap: space.m }}>
      {Platform.OS === "web" && (
        <>
          <View {...animate}>
            <GoogleButton onPress={google} />
          </View>
          <View {...animate}>
            <Divider />
          </View>
        </>
      )}

      <View {...animate} style={{ gap: space.m }}>
        <Input
          placeholder="Email"
          autoCapitalize="none"
          keyboardType="email-address"
          value={email}
          onChangeText={setEmail}
        />
        <Input
          placeholder="Password"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
        />
      </View>

      {error && <Text style={[font.small, { color: t.danger }]}>{error}</Text>}
      {notice && <Text style={[font.small, { color: t.muted }]}>{notice}</Text>}

      <View {...animate} style={{ gap: space.m }}>
        <InkButton
          label={mode === "signin" ? "Sign in" : "Create account"}
          onPress={submit}
          loading={busy}
          disabled={!email || !password}
        />
        <Button
          label={mode === "signin" ? "New here? Create an account" : "Have an account? Sign in"}
          variant="ghost"
          onPress={() => setMode(mode === "signin" ? "signup" : "signin")}
        />
      </View>
    </View>
  );

  return (
    <View style={{ flex: 1, backgroundColor: t.bg, paddingTop: insets.top }}>
      <View
        pointerEvents="none"
        style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }}
      >
        <Branches />
      </View>

      {wide ? (
        <View style={{ flex: 1, flexDirection: "row" }}>
          <View style={{ flex: 3, justifyContent: "center", padding: space.xl * 2 }}>
            <View {...animate} style={{ gap: space.m }}>
              <Text
                style={[font.small, { color: t.muted, fontFamily: mono, letterSpacing: 1 }]}
              >
                {"// AITUTOR.01"}
              </Text>
              <Brand size="lg" />
              <Text style={[font.displaySerif, { color: t.fg, maxWidth: 460 }]}>
                Every answer, worked step by step.
              </Text>
              <Text style={[font.body, { color: t.muted, maxWidth: 400 }]}>
                Grounded, step-by-step answers for JEE & NEET — from your syllabus,
                not thin air.
              </Text>
            </View>
          </View>
          <View
            style={{
              flex: 2,
              justifyContent: "center",
              alignItems: "center",
              padding: space.xl,
              borderLeftWidth: 1,
              borderLeftColor: t.border,
              backgroundColor: t.bg,
            }}
          >
            {form}
          </View>
        </View>
      ) : (
        <View
          style={{
            flex: 1,
            justifyContent: "center",
            alignItems: "center",
            padding: space.m,
            gap: space.l,
          }}
        >
          <View {...animate} style={{ alignItems: "center" }}>
            <Brand size="lg" />
            <Text
              style={[font.body, { color: t.muted, marginTop: space.s, textAlign: "center" }]}
            >
              Grounded, step-by-step answers for JEE & NEET.
            </Text>
          </View>
          {form}
        </View>
      )}
    </View>
  );
}
