import React, { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Check, Download, EyeOff, FileSpreadsheet, RotateCcw, UploadCloud } from "lucide-react";
import { commitUpload, downloadTemplate, profileUpload } from "../services/api";
import { useApp } from "../context/AppContext";

const STEPS = ["Upload", "Validate", "Preview", "Commit"];

const SAMPLE =
  "date,department,admissions,emergency_cases,bed_occupancy,icu_occupancy,doctor_workload,staff_workload,ventilators_total,ventilators_in_use,oxygen_stock_hours,patient_name\n" +
  "2026-10-03,Emergency,83,21,0.91,0.89,12.3,9.5,24,20,30,Ravi Kumar\n" +
  "2026-10-04,Emergency,85,22,0.93,0.90,12.7,9.7,24,21,22,Anita Rao\n" +
  "2026-10-05,Emergency,87,23,0.95,0.92,13.1,10.0,24,22,14,Sam Lee\n" +
  "2026-10-06,Emergency,84,abc,0.92,0.88,12.5,9.6,24,20,40,Priya N\n" +
  "2026-10-06,Emergency,84,abc,0.92,0.88,12.5,9.6,24,20,40,Priya N\n";

function Steps({ current }) {
  return (
    <ol className="stepper" aria-label="Upload progress">
      {STEPS.map((label, i) => (
        <li key={label} className={i < current ? "done" : i === current ? "current" : ""} aria-current={i === current ? "step" : undefined}>
          <span className="dot">{i < current ? <Check size={15} aria-hidden="true" /> : i + 1}</span>
          <span className="lbl">{label}</span>
        </li>
      ))}
    </ol>
  );
}

function SuccessCheck() {
  return (
    <svg className="checkmark" viewBox="0 0 72 72" aria-hidden="true">
      <motion.circle cx="36" cy="36" r="32" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.6 }} />
      <motion.path d="M22 37 l10 10 l19 -21" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.4, delay: 0.5 }} />
    </svg>
  );
}

function Stat({ label, value, tone }) {
  return <div className="stat"><span>{label}</span><b style={tone ? { color: `var(--${tone})` } : undefined}>{value}</b></div>;
}

function PreviewTable({ rows, errorsByRow }) {
  if (!rows?.length) return null;
  const cols = Object.keys(rows[0]).filter((c) => !c.startsWith("_"));
  return (
    <div className="table-wrap" style={{ maxHeight: 340 }}>
      <table>
        <caption className="sr-only">First rows of the file. Rows with errors are highlighted.</caption>
        <thead><tr><th>Row</th>{cols.map((c) => <th key={c}>{c}</th>)}<th>Problems</th></tr></thead>
        <tbody>
          {rows.map((r) => {
            const errs = errorsByRow[r._row] || [];
            const bad = new Set(errs.map((e) => e.column));
            return (
              <tr key={r._row} className={errs.length ? "row-error" : ""}>
                <td className="num">{r._row}</td>
                {cols.map((c) => <td key={c} className={bad.has(c) ? "cell-error" : ""}>{r[c] == null ? <span className="muted">—</span> : String(r[c])}</td>)}
                <td>{errs.length ? errs.map((e) => `${e.column}: ${e.error}`).join("; ") : <span className="muted">OK</span>}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function UploadStepper({ schema, onCommitted }) {
  const { refresh, notify } = useApp();
  const [step, setStep] = useState(0);
  const [file, setFile] = useState(null);
  const [report, setReport] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [over, setOver] = useState(false);
  const inputRef = useRef(null);
  const maxBytes = (schema?.max_size_mb || 5) * 1024 * 1024;

  function reset() {
    setStep(0); setFile(null); setReport(null); setResult(null); setError("");
  }

  async function choose(f) {
    if (!f) return;
    setError("");
    const ext = f.name.slice(f.name.lastIndexOf(".")).toLowerCase();
    if (!(schema?.accepted_formats || [".csv", ".xlsx"]).includes(ext)) { setError("Please choose a .csv or .xlsx file."); return; }
    if (f.size > maxBytes) { setError(`That file is ${(f.size / 1048576).toFixed(1)} MB. The limit is ${schema?.max_size_mb || 5} MB.`); return; }
    setFile(f);
    setStep(1);
    setBusy(true);
    try {
      const res = await profileUpload(f);
      if (res.error) throw new Error(res.error);
      setReport(res.report);
    } catch (e) {
      setError(e.message || "We couldn't read that file.");
      setStep(0);
    } finally {
      setBusy(false);
    }
  }

  async function commit() {
    setBusy(true);
    setError("");
    try {
      const res = await commitUpload(file);
      if (res.status === "error") throw new Error(res.error);
      setResult(res);
      setStep(3);
      notify(`Imported ${res.saved_count} rows`);
      refresh();
      onCommitted?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const errorsByRow = {};
  (report?.row_errors || []).forEach((e) => { (errorsByRow[e.row] ||= []).push(e); });

  return (
    <section className="card" aria-labelledby="upload-title">
      <div className="card-title" id="upload-title"><FileSpreadsheet size={17} aria-hidden="true" /> Upload data</div>
      <Steps current={step} />
      {error && <div className="form-error" role="alert" style={{ margin: "12px 0" }}>{error}</div>}

      <AnimatePresence mode="wait">
        <motion.div key={step} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.25 }}
          style={{ marginTop: 14 }}>
          {step === 0 && (
            <div className="stack">
              <div
                className={`dropzone ${over ? "over" : ""}`}
                role="button"
                tabIndex={0}
                aria-label="Choose a file to upload, or drop it here"
                onClick={() => inputRef.current?.click()}
                onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
                onDragOver={(e) => { e.preventDefault(); setOver(true); }}
                onDragLeave={() => setOver(false)}
                onDrop={(e) => { e.preventDefault(); setOver(false); choose(e.dataTransfer.files[0]); }}
              >
                <UploadCloud size={34} aria-hidden="true" />
                <strong>Drag and drop your file here, or click to browse</strong>
                <small>{(schema?.accepted_formats || [".csv", ".xlsx"]).join(" or ")} · up to {schema?.max_size_mb || 5} MB · {schema?.max_rows?.toLocaleString() || "20,000"} rows</small>
                <input ref={inputRef} type="file" accept=".csv,.xlsx" hidden onChange={(e) => choose(e.target.files[0])} />
              </div>
              <div className="row-wrap">
                <button className="btn" onClick={() => downloadTemplate().catch(() => notify("Could not download template", "error"))}>
                  <Download size={14} /> Download CSV template
                </button>
                <button className="btn btn-ghost" onClick={() => choose(new File([SAMPLE], "sample_surge_with_issues.csv", { type: "text/csv" }))}>
                  Try a sample file (with a few deliberate errors)
                </button>
              </div>
            </div>
          )}

          {step === 1 && (
            <div className="stack">
              {busy || !report ? <p className="row"><span className="spin" style={{ display: "inline-flex" }}><RotateCcw size={14} /></span> Checking {file?.name}…</p> : (
                <>
                  <div className="stat-grid">
                    <Stat label="Rows received" value={report.total_records} />
                    <Stat label="Valid rows" value={report.valid_records_after_basic_cleaning} />
                    <Stat label="Rows with errors" value={report.invalid_rows} />
                    <Stat label="Duplicate rows" value={report.duplicate_records} />
                    <Stat label="Missing values" value={report.missing_values} />
                  </div>
                  {report.missing_columns.length > 0 && (
                    <div className="form-error"><b>Missing required columns:</b> {report.missing_columns.join(", ")}. Download the template to see the expected format.</div>
                  )}
                  {report.privacy.dropped_columns.length > 0 && (
                    <div className="inset row" style={{ alignItems: "flex-start" }}>
                      <EyeOff size={16} aria-hidden="true" style={{ color: "var(--status-good)", flex: "0 0 auto" }} />
                      <span style={{ fontSize: 13 }}>
                        <b>Personal data detected and removed:</b> {report.privacy.dropped_columns.join(", ")}. These columns are masked below and will not be stored.
                      </span>
                    </div>
                  )}
                  {report.conversions.map((c) => <div key={c} className="inset" style={{ fontSize: 13 }}>ℹ {c}</div>)}
                  {report.ignored_columns.length > 0 && <small>Ignored (not part of the schema): {report.ignored_columns.join(", ")}</small>}
                  <div className="row-wrap">
                    <button className="btn" onClick={reset}>Choose another file</button>
                    <button className="btn btn-primary" onClick={() => setStep(2)} disabled={!report.can_commit}>Continue to preview</button>
                  </div>
                </>
              )}
            </div>
          )}

          {step === 2 && report && (
            <div className="stack">
              <p style={{ margin: 0 }}>
                First {report.raw_preview.length} rows as received (personal fields masked). Rows with problems are highlighted and will be skipped;
                <b> {report.valid_records_after_basic_cleaning} valid rows</b> will be saved.
              </p>
              <PreviewTable rows={report.raw_preview} errorsByRow={errorsByRow} />
              {Object.keys(report.missing_by_column).length > 0 && (
                <small>Missing values by column: {Object.entries(report.missing_by_column).map(([c, n]) => `${c} (${n})`).join(", ")}</small>
              )}
              {report.row_errors.length > 0 && (
                <details>
                  <summary className="row"><AlertTriangle size={14} aria-hidden="true" style={{ color: "var(--status-warning)" }} /> {report.row_errors.length} row-level problems{report.row_errors_truncated ? " (first 200 shown)" : ""}</summary>
                  <ul style={{ fontSize: 12.5, color: "var(--text-2)" }}>
                    {report.row_errors.map((e, i) => <li key={i}>Row {e.row}, <b>{e.column}</b>: {e.error} (value “{e.value}”)</li>)}
                  </ul>
                </details>
              )}
              <div className="row-wrap">
                <button className="btn" onClick={() => setStep(1)}>Back</button>
                <button className="btn btn-primary" onClick={commit} disabled={busy}>
                  {busy ? "Saving…" : `Commit ${report.valid_records_after_basic_cleaning} rows`}
                </button>
              </div>
            </div>
          )}

          {step === 3 && result && (
            <div className="empty" style={{ color: "var(--text-2)" }}>
              <SuccessCheck />
              <strong>Upload complete</strong>
              <span>
                Saved {result.saved_count} rows ({result.date_min} to {result.date_max}) as version #{result.batch_id}.
                {result.replaced_count > 0 && ` ${result.replaced_count} earlier rows were replaced and can be restored by rolling back.`}
                {result.skipped_rows > 0 && ` ${result.skipped_rows} rows were skipped.`}
              </span>
              <button className="btn btn-primary" onClick={reset}>Upload another file</button>
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </section>
  );
}
