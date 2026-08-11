/**
 * Assistant UI intent only - open/close state and a seed prompt. All
 * durable state (turns) lives in Postgres via react-query; all live
 * state (the token stream) lives inside the drawer component.
 */
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

type AssistantContextValue = {
  open: boolean;
  seedPrompt: string | null;
  openAssistant: (opts?: { seedPrompt?: string }) => void;
  closeAssistant: () => void;
  toggleAssistant: () => void;
};

const AssistantContext = createContext<AssistantContextValue | null>(null);

export function AssistantProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [seedPrompt, setSeedPrompt] = useState<string | null>(null);

  const openAssistant = useCallback((opts?: { seedPrompt?: string }) => {
    setSeedPrompt(opts?.seedPrompt ?? null);
    setOpen(true);
  }, []);
  const closeAssistant = useCallback(() => setOpen(false), []);
  const toggleAssistant = useCallback(() => setOpen((v) => !v), []);

  const value = useMemo(
    () => ({ open, seedPrompt, openAssistant, closeAssistant, toggleAssistant }),
    [open, seedPrompt, openAssistant, closeAssistant, toggleAssistant],
  );
  return <AssistantContext.Provider value={value}>{children}</AssistantContext.Provider>;
}

export function useAssistant(): AssistantContextValue {
  const ctx = useContext(AssistantContext);
  if (!ctx) throw new Error("useAssistant must be used inside AssistantProvider");
  return ctx;
}
