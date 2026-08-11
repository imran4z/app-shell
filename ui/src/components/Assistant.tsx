/**
 * The ⌘J assistant drawer (BLUEPRINT.md §3/§9). Durable transcript comes
 * from react-query (GET turns); a separate ephemeral `live` object holds
 * the in-flight token stream + tool chips and is discarded on finish +
 * refetch. Mutating tools pause on an approval card; approve/reject POSTs
 * /resume and tails the continuation.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Check, Loader2, Plus, Send, Sparkles, Wrench, X } from "lucide-react";

import { Button } from "@/components/Button";
import { useAssistant } from "@/lib/AssistantContext";
import { cn } from "@/lib/cn";
import { streamSse } from "@/lib/sse";

const CONVO_KEY = "appshell.assistant.conversation";

type Turn = {
  id: number;
  role: "user" | "assistant" | "tool";
  content: string;
  tool_calls: { id: string; name: string; input: unknown }[] | null;
  tool_results: { tool_use_id: string; content: string; is_error: boolean }[] | null;
};

type ToolChip = { id: string; name: string; status: "running" | "ok" | "error" };

type Live = {
  streaming: boolean;
  text: string;
  chips: ToolChip[];
  pendingApproval: { id: string; name: string; input: unknown }[] | null;
  error: string | null;
};

const IDLE_LIVE: Live = {
  streaming: false,
  text: "",
  chips: [],
  pendingApproval: null,
  error: null,
};

async function fetchTurns(conversationId: number): Promise<Turn[]> {
  const res = await fetch(`/api/assistant/conversations/${conversationId}/turns`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export function AssistantDrawer() {
  const { open, closeAssistant, seedPrompt } = useAssistant();
  const [conversationId, setConversationId] = useState<number | null>(() => {
    const raw = localStorage.getItem(CONVO_KEY);
    return raw ? Number(raw) : null;
  });
  const [draft, setDraft] = useState("");
  const [live, setLive] = useState<Live>(IDLE_LIVE);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const qc = useQueryClient();

  const turns = useQuery({
    queryKey: ["assistant-turns", conversationId],
    queryFn: () => fetchTurns(conversationId!),
    enabled: open && conversationId != null,
  });

  useEffect(() => {
    if (seedPrompt && open) setDraft(seedPrompt);
  }, [seedPrompt, open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeAssistant();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, closeAssistant]);

  // Keep the newest message visible while streaming.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [live.text, live.chips.length, turns.data?.length]);

  const finishStream = () => {
    qc.invalidateQueries({ queryKey: ["assistant-turns"] });
    qc.invalidateQueries({ queryKey: ["items"] });
    qc.invalidateQueries({ queryKey: ["item-stats"] });
  };

  const handleEvent = (event: string, data: string) => {
    if (event === "meta") {
      try {
        const cid = JSON.parse(data).conversation_id as number;
        setConversationId(cid);
        localStorage.setItem(CONVO_KEY, String(cid));
      } catch {
        /* ignore malformed meta */
      }
    } else if (event === "delta") {
      setLive((l) => ({ ...l, text: l.text + data }));
    } else if (event === "tool_call") {
      try {
        const call = JSON.parse(data);
        setLive((l) => ({
          ...l,
          chips: [...l.chips, { id: call.id, name: call.name, status: "running" }],
        }));
      } catch {
        /* ignore */
      }
    } else if (event === "tool_result") {
      try {
        const r = JSON.parse(data);
        setLive((l) => ({
          ...l,
          chips: l.chips.map((c) =>
            c.id === r.id ? { ...c, status: r.is_error ? "error" : "ok" } : c,
          ),
        }));
      } catch {
        /* ignore */
      }
    } else if (event === "approval_required") {
      try {
        setLive((l) => ({ ...l, pendingApproval: JSON.parse(data).calls, streaming: false }));
      } catch {
        /* ignore */
      }
      finishStream();
    } else if (event === "turn_persisted") {
      setLive((l) => ({ ...l, text: "" }));
      qc.invalidateQueries({ queryKey: ["assistant-turns"] });
    } else if (event === "error") {
      setLive((l) => ({ ...l, error: data, streaming: false }));
      finishStream();
    } else if (event === "done" || event === "cancelled") {
      setLive((l) => ({ ...IDLE_LIVE, pendingApproval: l.pendingApproval }));
      finishStream();
    }
  };

  const startStream = (url: string, payload: unknown) => {
    setLive({ ...IDLE_LIVE, streaming: true });
    abortRef.current?.abort();
    abortRef.current = streamSse(
      url,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
      handleEvent,
      (err) => {
        if (err) setLive((l) => ({ ...l, error: String(err), streaming: false }));
        else setLive((l) => ({ ...l, streaming: false }));
        finishStream();
      },
    );
  };

  const send = () => {
    const message = draft.trim();
    if (!message || live.streaming) return;
    setDraft("");
    startStream("/api/assistant/chat", {
      message,
      conversation_id: conversationId ?? undefined,
    });
  };

  const decide = (decision: "approve" | "reject") => {
    if (conversationId == null) return;
    setLive((l) => ({ ...l, pendingApproval: null }));
    startStream(`/api/assistant/conversations/${conversationId}/resume`, { decision });
  };

  const newThread = () => {
    abortRef.current?.abort();
    localStorage.removeItem(CONVO_KEY);
    setConversationId(null);
    setLive(IDLE_LIVE);
  };

  return (
    <div
      className={cn(
        "fixed top-0 right-0 z-50 h-full w-full sm:w-[440px]",
        "border-l border-[var(--color-border)] bg-[var(--color-canvas-elev1)] shadow-2xl",
        "transition-transform duration-200 ease-out",
        open ? "translate-x-0" : "translate-x-full",
      )}
      role="dialog"
      aria-modal="true"
      aria-label="Assistant"
      aria-hidden={!open}
    >
      {/* Header */}
      <div
        className="flex h-[60px] items-center gap-3 border-b border-[var(--color-border)] px-4"
        style={{
          background:
            "radial-gradient(120% 80% at 100% 0%, var(--color-accent-bg), transparent 60%)",
        }}
      >
        <span
          className="grid h-8 w-8 place-items-center rounded-lg text-black"
          style={{ background: "linear-gradient(135deg, var(--color-accent), var(--color-signal))" }}
        >
          <Sparkles size={15} />
        </span>
        <div>
          <p className="text-sm font-medium leading-tight">Assistant</p>
          <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-[var(--color-text-faint)]">
            {live.streaming ? "thinking..." : conversationId ? `thread #${conversationId}` : "new thread"}
          </p>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <button
            type="button"
            onClick={newThread}
            aria-label="New thread"
            title="New thread"
            className="grid h-7 w-7 place-items-center rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover-wash"
          >
            <Plus size={14} />
          </button>
          <button
            type="button"
            onClick={closeAssistant}
            aria-label="Close assistant"
            className="grid h-7 w-7 place-items-center rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover-wash"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Transcript */}
      <div ref={scrollRef} className="flex h-[calc(100%-60px-76px)] flex-col gap-3 overflow-y-auto p-4">
        {conversationId == null && !live.streaming && (
          <div className="mt-10 text-center">
            <Sparkles size={22} className="mx-auto text-[var(--color-text-faint)]" />
            <p className="mt-3 text-sm font-medium">Operate the app by asking</p>
            <p className="mx-auto mt-1 max-w-[36ch] text-xs text-[var(--color-text-muted)]">
              Try "what's in the system?" - mutating actions will pause for your approval.
            </p>
          </div>
        )}

        {turns.data?.map((turn) => <TurnRow key={turn.id} turn={turn} />)}

        {/* Live overlay: streaming text + tool chips */}
        {live.chips.map((chip) => (
          <ToolChipRow key={chip.id} chip={chip} />
        ))}
        {live.text && (
          <div className="whitespace-pre-wrap text-sm leading-relaxed">{live.text}</div>
        )}
        {live.streaming && !live.text && (
          <div className="flex items-center gap-2 text-xs text-[var(--color-text-faint)]">
            <Loader2 size={12} className="animate-spin" /> Working...
          </div>
        )}

        {live.pendingApproval && (
          <div className="rounded-xl border border-[var(--color-warning)]/40 bg-[var(--color-warning-bg)] p-3">
            <p className="text-xs font-medium">The assistant wants to run:</p>
            <ul className="mt-1.5 space-y-1">
              {live.pendingApproval.map((c) => (
                <li key={c.id} className="font-mono text-xs text-[var(--color-text-muted)]">
                  {c.name}({JSON.stringify(c.input)})
                </li>
              ))}
            </ul>
            <div className="mt-2.5 flex gap-2">
              <Button variant="primary" size="sm" onClick={() => decide("approve")}>
                <Check size={12} /> Approve
              </Button>
              <Button variant="danger" size="sm" onClick={() => decide("reject")}>
                <X size={12} /> Reject
              </Button>
            </div>
          </div>
        )}

        {live.error && (
          <div className="rounded-lg border border-[var(--color-danger)]/40 bg-[var(--color-danger-bg)] px-3 py-2 text-xs text-[var(--color-danger)]">
            {live.error}
          </div>
        )}
      </div>

      {/* Composer */}
      <form
        className="flex h-[76px] items-center gap-2 border-t border-[var(--color-border)] px-4"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={live.pendingApproval ? "Resolve the approval first..." : "Ask the assistant..."}
          disabled={!!live.pendingApproval}
          className="h-10 flex-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas)] px-3 text-sm outline-none transition-colors placeholder:text-[var(--color-text-faint)] focus:border-[var(--color-accent)] disabled:opacity-50"
        />
        <Button
          type="submit"
          variant="primary"
          size="md"
          disabled={live.streaming || !draft.trim() || !!live.pendingApproval}
          aria-label="Send"
        >
          {live.streaming ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
        </Button>
      </form>
    </div>
  );
}

// --- Sub-components ------------------------------------------------------

function TurnRow({ turn }: { turn: Turn }) {
  if (turn.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-[var(--color-accent-bg)] px-3.5 py-2 text-sm">
          {turn.content}
        </div>
      </div>
    );
  }
  if (turn.role === "tool") {
    return (
      <div className="flex flex-wrap gap-1.5">
        {(turn.tool_results ?? []).map((r) => (
          <span
            key={r.tool_use_id}
            className={cn(
              "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 font-mono text-[10px]",
              r.is_error
                ? "border-[var(--color-danger)]/30 text-[var(--color-danger)]"
                : "border-[var(--color-border)] text-[var(--color-text-faint)]",
            )}
          >
            <Wrench size={10} /> result
          </span>
        ))}
      </div>
    );
  }
  return (
    <div className="space-y-1.5">
      {(turn.tool_calls ?? []).map((c) => (
        <span
          key={c.id}
          className="inline-flex items-center gap-1 rounded-md border border-[var(--color-info)]/30 bg-[var(--color-info)]/10 px-2 py-0.5 font-mono text-[10px] text-[var(--color-info)]"
        >
          <Wrench size={10} /> {c.name}
        </span>
      ))}
      {turn.content && (
        <div className="whitespace-pre-wrap text-sm leading-relaxed">{turn.content}</div>
      )}
    </div>
  );
}

function ToolChipRow({ chip }: { chip: ToolChip }) {
  return (
    <span
      className={cn(
        "inline-flex w-fit items-center gap-1.5 rounded-md border px-2 py-1 font-mono text-[11px]",
        chip.status === "running" && "border-[var(--color-info)]/30 text-[var(--color-info)]",
        chip.status === "ok" && "border-[var(--color-success)]/30 text-[var(--color-success)]",
        chip.status === "error" && "border-[var(--color-danger)]/30 text-[var(--color-danger)]",
      )}
    >
      {chip.status === "running" ? (
        <Loader2 size={11} className="animate-spin" />
      ) : chip.status === "ok" ? (
        <Check size={11} />
      ) : (
        <X size={11} />
      )}
      {chip.name}
    </span>
  );
}
