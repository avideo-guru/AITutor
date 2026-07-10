import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export type ChatStreamEvent =
  | { type: 'token'; text: string }
  | { type: 'verification'; verified: boolean | null }
  | { type: 'done' }
  | { type: 'error'; message: string };

function parseFrame(frame: string): ChatStreamEvent | null {
  let event = '';
  let data = '';
  for (const line of frame.split('\n')) {
    if (line.startsWith('event: ')) event = line.slice(7).trim();
    else if (line.startsWith('data: ')) data = line.slice(6);
  }
  if (!event) return null;
  const payload = data ? JSON.parse(data) : {};
  switch (event) {
    case 'token':
      return { type: 'token', text: payload.text ?? '' };
    case 'verification':
      return { type: 'verification', verified: payload.verified ?? null };
    case 'done':
      return { type: 'done' };
    case 'error':
      return { type: 'error', message: payload.message ?? 'Unknown tutor error' };
    default:
      return null;
  }
}

@Injectable({
  providedIn: 'root'
})
export class AiTutorService {
  /**
   * Streams the tutor's answer from the backend (`POST /api/chat`, SSE).
   * Emits token chunks while the answer streams, then the verification
   * verdict that drives the verified/unverified badge.
   */
  streamResponse(subject: string, question: string): Observable<ChatStreamEvent> {
    return new Observable<ChatStreamEvent>((subscriber) => {
      const controller = new AbortController();

      (async () => {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ subject, message: question }),
          signal: controller.signal
        });
        if (!response.ok || !response.body) {
          throw new Error(`Tutor service returned ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          let sep: number;
          while ((sep = buffer.indexOf('\n\n')) !== -1) {
            const frame = buffer.slice(0, sep);
            buffer = buffer.slice(sep + 2);
            const parsed = parseFrame(frame);
            if (parsed) subscriber.next(parsed);
          }
        }
        subscriber.complete();
      })().catch((err) => {
        if (!controller.signal.aborted) subscriber.error(err);
      });

      return () => controller.abort();
    });
  }
}
