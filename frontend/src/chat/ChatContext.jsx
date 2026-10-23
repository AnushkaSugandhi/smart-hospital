import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { getChatSession, getChatSessions, getChatSuggestions, sendChatFeedback, streamChat } from "../services/api";

const ChatContext = createContext(null);
export const useChat = () => useContext(ChatContext);

const FRIENDLY_ERROR = "Sorry, I couldn't reach the assistant just now. Please try again in a moment.";

// One conversation shared by the floating panel and the Ask AI page.
export function ChatProvider({ children }) {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [status, setStatus] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [meta, setMeta] = useState({ suggestions: [], disclaimer: "", mode: "" });
  const abortRef = useRef(null);

  const refreshSessions = useCallback(() => getChatSessions().then(setSessions).catch(() => {}), []);
  useEffect(() => {
    getChatSuggestions().then(setMeta).catch(() => {});
    refreshSessions();
  }, [refreshSessions]);

  const patchLast = (fn) => setMessages((list) => {
    const copy = list.slice();
    copy[copy.length - 1] = fn(copy[copy.length - 1]);
    return copy;
  });

  const send = useCallback(async (text) => {
    const question = text.trim();
    if (!question || streaming) return;
    const controller = new AbortController();
    abortRef.current = controller;
    setStreaming(true);
    setStatus("Thinking…");
    setMessages((list) => [
      ...list,
      { role: "user", content: question, id: `u-${Date.now()}` },
      { role: "assistant", content: "", pending: true, charts: [], sources: [], actions: [], id: `a-${Date.now()}` },
    ]);
    try {
      await streamChat(question, sessionId, (type, data) => {
        if (type === "meta") setSessionId(data.session_id);
        else if (type === "status") setStatus(data.text);
        else if (type === "token") patchLast((m) => ({ ...m, content: m.content + data.text }));
        else if (type === "chart") patchLast((m) => ({ ...m, charts: [...(m.charts || []), data] }));
        else if (type === "done") patchLast((m) => ({ ...m, ...data, id: data.message_id, pending: false }));
        else if (type === "error") patchLast((m) => ({ ...m, content: m.content || data.message, error: true, pending: false }));
      }, controller.signal);
    } catch (e) {
      if (e.name !== "AbortError") {
        const msg = e.status === 429 ? e.message : FRIENDLY_ERROR;
        patchLast((m) => ({ ...m, content: m.content || msg, error: true, pending: false }));
      }
    } finally {
      patchLast((m) => (m?.pending ? { ...m, pending: false } : m));
      setStreaming(false);
      setStatus("");
      refreshSessions();
    }
  }, [sessionId, streaming, refreshSessions]);

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const newChat = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setSessionId(null);
  }, []);

  const openSession = useCallback(async (id) => {
    abortRef.current?.abort();
    const data = await getChatSession(id);
    setSessionId(id);
    setMessages(data.messages);
  }, []);

  const rate = useCallback(async (messageId, value) => {
    setMessages((list) => list.map((m) => (m.id === messageId ? { ...m, feedback: value } : m)));
    try { await sendChatFeedback(messageId, value); } catch {}
  }, []);

  const value = { messages, sessionId, sessions, status, streaming, meta, send, stop, newChat, openSession, rate, refreshSessions };
  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}
