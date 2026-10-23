import React from "react";
import { MessageSquare, Plus, Trash2 } from "lucide-react";
import { deleteChatSession } from "../services/api";
import { useApp } from "../context/AppContext";
import { useChat } from "../chat/ChatContext";
import ChatView from "../chat/ChatView";
import PageHeader from "../components/PageHeader";
import { formatUtc } from "../utils/time";

export default function AskAI() {
  const { notify } = useApp();
  const { sessions, sessionId, openSession, newChat, refreshSessions } = useChat();

  async function remove(id) {
    try {
      await deleteChatSession(id);
      if (id === sessionId) newChat();
      refreshSessions();
    } catch (e) {
      notify(e.message, "error");
    }
  }

  return (
    <div className="page">
      <PageHeader page="ask">
        <button className="btn btn-primary" onClick={newChat}><Plus size={14} /> New chat</button>
      </PageHeader>
      <div className="ask-layout">
        <aside className="card ask-history" aria-labelledby="hist-title">
          <div className="card-title" id="hist-title"><MessageSquare size={16} aria-hidden="true" /> Chat history</div>
          {sessions.length === 0 ? <small>Your conversations appear here.</small> : (
            <ul>
              {sessions.map((s) => (
                <li key={s.id} className={s.id === sessionId ? "active" : ""}>
                  <button className="hist-open" onClick={() => openSession(s.id)} aria-current={s.id === sessionId ? "true" : undefined}>
                    <span>{s.title}</span>
                    <small>{formatUtc(s.updated_at)}</small>
                  </button>
                  <button className="icon-btn sm" onClick={() => remove(s.id)} aria-label={`Delete chat ${s.title}`}><Trash2 size={13} /></button>
                </li>
              ))}
            </ul>
          )}
        </aside>
        <section className="card ask-main" aria-label="Conversation">
          <ChatView />
        </section>
      </div>
    </div>
  );
}
