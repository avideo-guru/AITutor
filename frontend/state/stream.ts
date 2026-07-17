// The one Zustand store: the live streaming thread. Everything else is
// server state and belongs to TanStack Query.
//
// A thread is: completed exchanges (`history`) + the exchange currently
// streaming (the flat fields below). `ask` starts a fresh thread; `followUp`
// carries the thread_id the backend returned in `meta`, so the server loads
// prior turns as context (P0.3 — this was wired server-side but never sent
// from the client until now).

import { create } from "zustand";

import { askStream } from "@/lib/api";

type Status = "idle" | "streaming" | "done" | "error";

export type Exchange = {
  question: string;
  imageUrl: string | null;
  answer: string;
  sessionId: string | null;
  sources: string[];
};

type StreamState = {
  question: string;
  imageUrl: string | null;
  answer: string;
  status: Status;
  sessionId: string | null;
  threadId: string | null;
  sources: string[];
  history: Exchange[];
  error: string | null;
  ask: (q: { text?: string; image_url?: string; chapter?: string }) => void;
  followUp: (text: string) => void;
  reset: () => void;
};

export const useStream = create<StreamState>((set, get) => {
  const start = (q: { text?: string; image_url?: string; chapter?: string; thread_id?: string }) => {
    set({
      question: q.text ?? "(photo question)",
      imageUrl: q.image_url ?? null,
      answer: "",
      status: "streaming",
      sessionId: null,
      sources: [],
      error: null,
    });
    // Fire-and-forget: the stream keeps running across navigation.
    askStream(q, {
      onToken: (t) => set((s) => ({ answer: s.answer + t })),
      onMeta: (m) =>
        set({ sessionId: m.session_id, threadId: m.thread_id, sources: m.sources }),
      onError: (_code, message) => set({ status: "error", error: message }),
      onDone: () => set({ status: "done" }),
    }).catch((e: Error) =>
      set({ status: "error", error: e.message || "Connection lost" }),
    );
  };

  return {
    question: "",
    imageUrl: null,
    answer: "",
    status: "idle",
    sessionId: null,
    threadId: null,
    sources: [],
    history: [],
    error: null,

    ask: (q) => {
      set({ history: [], threadId: null });
      start(q);
    },

    followUp: (text) => {
      const s = get();
      if (!text.trim() || s.status === "streaming") return;
      // Archive the finished exchange before the flat fields are reused.
      set({
        history: [
          ...s.history,
          {
            question: s.question,
            imageUrl: s.imageUrl,
            answer: s.answer,
            sessionId: s.sessionId,
            sources: s.sources,
          },
        ],
      });
      start({ text: text.trim(), thread_id: s.threadId ?? undefined });
    },

    reset: () =>
      set({
        question: "", imageUrl: null, answer: "", status: "idle",
        sessionId: null, threadId: null, sources: [], history: [], error: null,
      }),
  };
});
