import React, { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Bot, Maximize2, Plus, X } from "lucide-react";
import { useApp } from "../context/AppContext";
import Drawer from "../components/Drawer";
import { useChat } from "./ChatContext";
import ChatView from "./ChatView";

// Floating bottom-right button that opens the assistant in a slide-over.
export default function ChatPanel() {
  const { route, navigate } = useApp();
  const { newChat } = useChat();
  const [open, setOpen] = useState(false);
  if (route.page === "ask") return null; // the full page is already open

  return (
    <>
      <AnimatePresence>
        {!open && (
          <motion.button className="chat-fab" onClick={() => setOpen(true)} aria-label="Ask Smart Hospital"
            initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.6, opacity: 0 }}
            whileHover={{ scale: 1.06 }} whileTap={{ scale: 0.96 }}>
            <Bot size={22} aria-hidden="true" />
            <span className="fab-label">Ask AI</span>
          </motion.button>
        )}
      </AnimatePresence>
      <Drawer open={open} onClose={() => setOpen(false)} labelledBy="chat-panel-title" className="chat-drawer" width="min(480px, 100vw)">
        <div className="drawer-head">
          <div className="row"><Bot size={18} aria-hidden="true" /><h2 id="chat-panel-title" style={{ fontSize: 16 }}>Ask Smart Hospital</h2></div>
          <div className="row">
            <button className="icon-btn" onClick={newChat} aria-label="New chat"><Plus size={16} /></button>
            <button className="icon-btn" onClick={() => { setOpen(false); navigate("ask"); }} aria-label="Open full page"><Maximize2 size={15} /></button>
            <button className="icon-btn" onClick={() => setOpen(false)} aria-label="Close assistant"><X size={16} /></button>
          </div>
        </div>
        <ChatView compact />
      </Drawer>
    </>
  );
}
