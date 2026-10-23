import React, { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle, ArrowRight, BarChart3, BookOpen, Bot, Check, ClipboardList, Copy, Database, Info, Send,
  ShieldCheck, Square, ThumbsDown, ThumbsUp,
} from "lucide-react";
import { useApp } from "../context/AppContext";
import { useChat } from "./ChatContext";
import Markdown from "./Markdown";
import MiniChart from "./MiniChart";

const SOURCE_ICON = { live: Database, policy: BookOpen, decision: ClipboardList, snapshot_week: BarChart3, alert: AlertTriangle, audit: ShieldCheck, event: Info };
const SOURCE_LABEL = { live: "Live data", policy: "Policy", decision: "Decision", snapshot_week: "History", alert: "Alert", audit: "Audit", event: "Past event" };

function Typing() {
  return <span className="typing" aria-label="Assistant is typing"><i /><i /><i /></span>;
}

function SourceChips({ sources, highlight }) {
  if (!sources?.length) return null;
  return (
    <div className="source-chips" aria-label="Sources">
      {sources.map((s) => {
        const Icon = SOURCE_ICON[s.type] || Info;
        const when = s.date_start ? (s.date_start === s.date_end ? s.date_start : `${s.date_start} → ${s.date_end}`) : "";
        return (
          <span key={s.id} className={`source-chip ${highlight === s.ref ? "hl" : ""}`} title={[s.title, when].filter(Boolean).join(" · ")}>
            <Icon size={12} aria-hidden="true" />
            {s.ref && <b>{s.ref}</b>}
            <span className="src-type">{SOURCE_LABEL[s.type] || s.type}</span>
            <span className="src-title">{s.title}</span>
          </span>
        );
      })}
    </div>
  );
}

function AssistantMessage({ m, status }) {
  const { navigate } = useApp();
  const { rate } = useChat();
  const [copied, setCopied] = useState(false);
  const [highlight, setHighlight] = useState(null);

  async function copy() {
    try { await navigator.clipboard.writeText(m.content); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch {}
  }

  return (
    <div className="msg assistant">
      <span className="msg-avatar" aria-hidden="true"><Bot size={15} /></span>
      <div className={`bubble ${m.error ? "bubble-error" : ""}`}>
        {m.pending && !m.content && <div className="row muted" style={{ fontSize: 12.5 }}><Typing /> {status}</div>}
        {m.content && <Markdown text={m.content} onCite={setHighlight} />}
        {m.pending && m.content && <span className="caret" aria-hidden="true" />}
        {(m.charts || []).map((c, i) => <MiniChart key={i} chart={c} />)}
        {!m.pending && !m.error && (
          <>
            {m.confidence === "low" && (
              <div className="low-conf" role="note"><AlertTriangle size={13} aria-hidden="true" /> Low confidence — sources are weak or missing. Check the data directly.</div>
            )}
            {(m.actions || []).length > 0 && (
              <div className="row-wrap" style={{ marginTop: 8 }}>
                {m.actions.map((a, i) => (
                  <button key={i} className="btn btn-sm" onClick={() => navigate(a.page, a.params)}>{a.label} <ArrowRight size={13} /></button>
                ))}
              </div>
            )}
            <SourceChips sources={m.sources} highlight={highlight} />
            {typeof m.id === "number" && (
              <div className="msg-tools">
                <button className={`icon-btn sm ${m.feedback === "up" ? "on" : ""}`} aria-pressed={m.feedback === "up"} aria-label="Helpful"
                  onClick={() => rate(m.id, m.feedback === "up" ? null : "up")}><ThumbsUp size={13} /></button>
                <button className={`icon-btn sm ${m.feedback === "down" ? "on" : ""}`} aria-pressed={m.feedback === "down"} aria-label="Not helpful"
                  onClick={() => rate(m.id, m.feedback === "down" ? null : "down")}><ThumbsDown size={13} /></button>
                <button className="icon-btn sm" onClick={copy} aria-label="Copy answer">{copied ? <Check size={13} /> : <Copy size={13} />}</button>
                {m.mode === "offline" && <span className="muted" style={{ fontSize: 11 }}>Data-only answer</span>}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default function ChatView({ compact = false }) {
  const { messages, send, stop, streaming, status, meta } = useChat();
  const [draft, setDraft] = useState("");
  const listRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages]);
  useEffect(() => { inputRef.current?.focus(); }, []);

  function submit(e) {
    e?.preventDefault();
    if (!draft.trim()) return;
    send(draft);
    setDraft("");
  }

  return (
    <div className={`chat-view ${compact ? "compact" : ""}`}>
      <div className="chat-list" ref={listRef} aria-live="polite" aria-busy={streaming}>
        {messages.length === 0 ? (
          <div className="chat-empty">
            <span className="chat-hero" aria-hidden="true"><Bot size={26} /></span>
            <strong>Ask Smart Hospital</strong>
            <span>Live numbers come from the dashboard; history, decisions and policies from hospital records. Every answer shows its sources.</span>
            <div className="suggestions">
              {(meta.suggestions || []).slice(0, compact ? 4 : 6).map((s, i) => (
                <motion.button key={s} className="suggestion" onClick={() => send(s)}
                  initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0, transition: { delay: 0.05 * i } }}>
                  {s}
                </motion.button>
              ))}
            </div>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {messages.map((m, i) => (
              <motion.div key={m.id ?? i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
                {m.role === "user" ? (
                  <div className="msg user"><div className="bubble">{m.content}</div></div>
                ) : (
                  <AssistantMessage m={m} status={status} />
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>

      <form className="chat-composer" onSubmit={submit}>
        <label htmlFor={compact ? "chat-input-panel" : "chat-input-page"} className="sr-only">Ask a question</label>
        <textarea
          id={compact ? "chat-input-panel" : "chat-input-page"}
          ref={inputRef}
          rows={1}
          value={draft}
          placeholder="Ask about beds, ICU, forecasts, decisions or policies…"
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
          maxLength={2000}
        />
        {streaming ? (
          <button type="button" className="icon-btn" onClick={stop} aria-label="Stop answering"><Square size={15} /></button>
        ) : (
          <button type="submit" className="icon-btn send" disabled={!draft.trim()} aria-label="Send question"><Send size={15} /></button>
        )}
      </form>
      <p className="chat-disclaimer"><ShieldCheck size={12} aria-hidden="true" /> {meta.disclaimer || "AI supports decisions and does not replace medical judgment."}</p>
    </div>
  );
}
