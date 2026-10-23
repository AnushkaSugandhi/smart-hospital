import React, { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Eye, History, ListChecks, RotateCcw, ShieldCheck, X } from "lucide-react";
import { getUploadBatch, getUploadBatches, getUploadSchema, rollbackUploadBatch } from "../services/api";
import { useApp } from "../context/AppContext";
import { formatUtc } from "../utils/time";
import PageHeader from "../components/PageHeader";
import UploadStepper from "../components/UploadStepper";
import { EmptyState, Skeleton } from "../components/Skeleton";

const PREVIEW_COLS = ["date", "department", "admissions", "emergency_cases", "bed_occupancy", "icu_occupancy"];

function SchemaGuide({ schema }) {
  if (!schema) return <Skeleton height={120} />;
  const group = (required) => schema.columns.filter((c) => c.required === required);
  return (
    <section className="card" aria-labelledby="schema-title">
      <div className="card-title" id="schema-title"><ListChecks size={17} aria-hidden="true" /> What your file should contain</div>
      <p className="card-sub">One row per department per day. Column names are case-insensitive. Older files with only the required columns still work.</p>
      {[["Required columns", true], ["Optional columns", false]].map(([title, req]) => (
        <div key={title} style={{ marginBottom: 12 }}>
          <h3 style={{ fontSize: 13, margin: "0 0 8px" }}>{title}</h3>
          <div className="schema-list">
            {group(req).map((c) => (
              <div className="schema-item" key={c.name}>
                <code>{c.name}</code><span className="pill" style={{ justifySelf: "end" }}>{c.type}</span>
                <small>{c.description} · e.g. {String(c.example)}</small>
              </div>
            ))}
          </div>
        </div>
      ))}
      <div className="row" style={{ fontSize: 12.5 }}>
        <ShieldCheck size={15} aria-hidden="true" style={{ color: "var(--status-good)" }} /> {schema.privacy}
      </div>
    </section>
  );
}

function ConfirmRollback({ batch, onCancel, onConfirm, busy }) {
  return (
    <>
      <motion.div className="overlay" onClick={onCancel} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
      <motion.div className="modal" role="alertdialog" aria-modal="true" aria-labelledby="rb-title" aria-describedby="rb-desc"
        initial={{ opacity: 0, scale: 0.96, x: "-50%", y: "-50%" }} animate={{ opacity: 1, scale: 1, x: "-50%", y: "-50%" }} exit={{ opacity: 0 }}>
        <h2 id="rb-title" style={{ fontSize: 17 }}>Roll back upload #{batch.id}?</h2>
        <p id="rb-desc">
          This removes the {batch.row_count} rows from <b>{batch.filename}</b> ({batch.date_min} to {batch.date_max}) and restores any
          values they replaced. The dashboard, forecasts and AI index will update. This is recorded in the audit log.
        </p>
        <div className="row" style={{ justifyContent: "flex-end", marginTop: 12 }}>
          <button className="btn" onClick={onCancel} autoFocus>Cancel</button>
          <button className="btn btn-danger" onClick={onConfirm} disabled={busy}><RotateCcw size={14} /> {busy ? "Rolling back…" : "Roll back"}</button>
        </div>
      </motion.div>
    </>
  );
}

function VersionHistory({ version }) {
  const { can, notify, refresh } = useApp();
  const [batches, setBatches] = useState(null);
  const [preview, setPreview] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const [busy, setBusy] = useState(false);
  const [showAll, setShowAll] = useState(false);

  const load = useCallback(() => getUploadBatches().then(setBatches).catch(() => setBatches([])), []);
  useEffect(() => { load(); }, [load, version]);

  async function doRollback() {
    setBusy(true);
    try {
      const res = await rollbackUploadBatch(confirm.id);
      notify(`Rolled back #${confirm.id}: removed ${res.removed_rows} rows, restored ${res.restored_rows}`);
      setConfirm(null);
      load();
      refresh();
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card" aria-labelledby="vh-title">
      <div className="card-title" id="vh-title"><History size={17} aria-hidden="true" /> Version history</div>
      {batches == null ? <Skeleton height={120} /> : batches.length === 0 ? (
        <EmptyState icon={History} title="No uploads yet">Each upload you commit appears here and can be previewed or rolled back.</EmptyState>
      ) : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>#</th><th>File</th><th>By</th><th>When</th><th>Rows</th><th>Dates</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr></thead>
            <tbody>
              {(showAll ? batches : batches.slice(0, 8)).map((b) => (
                <tr key={b.id}>
                  <td className="num">{b.id}</td>
                  <td style={{ color: "var(--text)" }}>{b.filename}{b.dropped_columns.length > 0 && <small> · {b.dropped_columns.length} personal column(s) removed</small>}</td>
                  <td>{b.uploaded_by}</td>
                  <td className="num">{formatUtc(b.uploaded_at)}</td>
                  <td className="num">{b.row_count}</td>
                  <td className="num">{b.date_min} → {b.date_max}</td>
                  <td><span className="pill">{b.status === "rolled_back" ? `Rolled back by ${b.rolled_back_by}` : "Active"}</span></td>
                  <td>
                    <div className="row">
                      {can("Analyst") && (
                        <button className="btn btn-sm" onClick={() => getUploadBatch(b.id).then(setPreview)} aria-label={`Preview upload ${b.id}`}>
                          <Eye size={13} /> Preview
                        </button>
                      )}
                      {can("Admin") && b.status !== "rolled_back" && (
                        <button className="btn btn-sm btn-danger" onClick={() => setConfirm(b)} aria-label={`Roll back upload ${b.id}`}>
                          <RotateCcw size={13} /> Rollback
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {batches.length > 8 && (
            <div className="pager">
              <button className="btn btn-sm btn-ghost" onClick={() => setShowAll((v) => !v)}>
                {showAll ? "Show recent only" : `Show all ${batches.length} uploads`}
              </button>
            </div>
          )}
        </div>
      )}

      <AnimatePresence>
        {confirm && <ConfirmRollback key="confirm" batch={confirm} busy={busy} onCancel={() => setConfirm(null)} onConfirm={doRollback} />}
        {preview && (
          <React.Fragment key="preview">
            <motion.div className="overlay" onClick={() => setPreview(null)} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
            <motion.div className="modal" role="dialog" aria-modal="true" aria-labelledby="pv-title"
              initial={{ opacity: 0, x: "-50%", y: "-48%" }} animate={{ opacity: 1, x: "-50%", y: "-50%" }} exit={{ opacity: 0 }}>
              <div className="spread">
                <h2 id="pv-title" style={{ fontSize: 16 }}>Upload #{preview.batch.id} · {preview.batch.filename}</h2>
                <button className="icon-btn" onClick={() => setPreview(null)} aria-label="Close preview"><X size={15} /></button>
              </div>
              <p className="card-sub" style={{ marginTop: 6 }}>{preview.rows.length ? `First ${preview.rows.length} rows` : "Rows were removed when this upload was rolled back."}</p>
              {preview.rows.length > 0 && (
                <div className="table-wrap" style={{ maxHeight: 360 }}>
                  <table>
                    <thead><tr>{PREVIEW_COLS.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                    <tbody>
                      {preview.rows.map((r, i) => (
                        <tr key={i}>{PREVIEW_COLS.map((c) => <td key={c} className="num">{r[c]}</td>)}</tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </motion.div>
          </React.Fragment>
        )}
      </AnimatePresence>
    </section>
  );
}

export default function DataUpload() {
  const [schema, setSchema] = useState(null);
  const [version, setVersion] = useState(0);
  useEffect(() => { getUploadSchema().then(setSchema).catch(() => {}); }, []);

  return (
    <div className="page">
      <PageHeader page="upload" />
      <UploadStepper schema={schema} onCommitted={() => setVersion((v) => v + 1)} />
      <VersionHistory version={version} />
      <SchemaGuide schema={schema} />
    </div>
  );
}
