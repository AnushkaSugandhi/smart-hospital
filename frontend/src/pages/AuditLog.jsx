import React, { useEffect, useState } from "react";
import { Download, ShieldCheck } from "lucide-react";
import { exportAuditCsv, getAuditLog, getAuditMeta } from "../services/api";
import { useApp } from "../context/AppContext";
import PageHeader from "../components/PageHeader";
import AuditTable, { actionLabel } from "../components/AuditTable";
import { EmptyState, Skeleton } from "../components/Skeleton";

const PAGE_SIZE = 50;
const EMPTY = { username: "", action: "", date_from: "", date_to: "", q: "" };

export default function AuditLog() {
  const { notify } = useApp();
  const [filters, setFilters] = useState(EMPTY);
  const [meta, setMeta] = useState({ actions: [], users: [] });
  const [data, setData] = useState(null);
  const [offset, setOffset] = useState(0);

  useEffect(() => { getAuditMeta().then(setMeta).catch(() => {}); }, []);
  useEffect(() => {
    const id = setTimeout(() => {
      getAuditLog({ ...filters, limit: PAGE_SIZE, offset }).then(setData).catch((e) => notify(e.message, "error"));
    }, 250);
    return () => clearTimeout(id);
  }, [filters, offset, notify]);

  const set = (k) => (e) => { setOffset(0); setFilters({ ...filters, [k]: e.target.value }); };

  return (
    <div className="page">
      <PageHeader page="audit">
        <button className="btn" onClick={() => exportAuditCsv(filters).catch((e) => notify(e.message, "error"))}>
          <Download size={14} /> Export CSV
        </button>
      </PageHeader>
      <section className="card">
        <div className="row-wrap" style={{ marginBottom: 12, alignItems: "end" }}>
          <label className="field">User
            <select value={filters.username} onChange={set("username")}>
              <option value="">Everyone</option>
              {meta.users.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </label>
          <label className="field">Action
            <select value={filters.action} onChange={set("action")}>
              <option value="">All actions</option>
              {meta.actions.map((a) => <option key={a} value={a}>{actionLabel(a)}</option>)}
            </select>
          </label>
          <label className="field">From<input type="date" value={filters.date_from} onChange={set("date_from")} /></label>
          <label className="field">To<input type="date" value={filters.date_to} onChange={set("date_to")} /></label>
          <label className="field" style={{ minWidth: 200 }}>Search details<input type="search" value={filters.q} onChange={set("q")} placeholder="e.g. ICU, batch 3" /></label>
          <button className="btn btn-ghost" onClick={() => { setOffset(0); setFilters(EMPTY); }}>Clear</button>
        </div>
        {!data ? <Skeleton height={240} /> : data.items.length === 0 ? (
          <EmptyState icon={ShieldCheck} title="No matching entries">Try widening the date range or clearing filters.</EmptyState>
        ) : (
          <>
            <AuditTable items={data.items} />
            <div className="pager">
              <span>{offset + 1}–{Math.min(offset + PAGE_SIZE, data.total)} of {data.total}</span>
              <button className="btn btn-sm" disabled={offset === 0} onClick={() => setOffset(Math.max(offset - PAGE_SIZE, 0))}>Previous</button>
              <button className="btn btn-sm" disabled={offset + PAGE_SIZE >= data.total} onClick={() => setOffset(offset + PAGE_SIZE)}>Next</button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
