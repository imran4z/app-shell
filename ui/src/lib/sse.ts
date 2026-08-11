/**
 * Manual SSE frame parser over fetch - NOT EventSource, because chat
 * needs POST bodies (BLUEPRINT.md §9). Buffers, splits on \n\n, parses
 * event:/data: lines, dispatches to a typed handler. Returns an
 * AbortController; NOTE the connection is only a viewer - aborting never
 * stops the run (cancel is a server call).
 */

export type SseHandler = (event: string, data: string) => void;

export function streamSse(
  url: string,
  init: RequestInit,
  onEvent: SseHandler,
  onDone: (error?: Error) => void,
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(url, { ...init, signal: controller.signal });
      if (!res.ok) {
        let detail = res.statusText;
        try {
          const body = await res.json();
          if (typeof body?.detail === "string") detail = body.detail;
        } catch {
          /* keep statusText */
        }
        throw new Error(`API ${res.status}: ${detail}`);
      }
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";
        for (const frame of frames) {
          let event = "message";
          const dataLines: string[] = [];
          for (const line of frame.split("\n")) {
            if (line.startsWith("event:")) event = line.slice(6).trim();
            else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
          }
          if (dataLines.length > 0) onEvent(event, dataLines.join("\n"));
        }
      }
      onDone();
    } catch (err) {
      if ((err as Error).name === "AbortError") onDone();
      else onDone(err as Error);
    }
  })();

  return controller;
}
