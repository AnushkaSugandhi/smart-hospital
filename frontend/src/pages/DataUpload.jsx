import React, { useState } from "react";
import { commitUpload } from "../services/api";
import { CheckCircle2, UploadCloud, Database, AlertCircle, FileSpreadsheet } from "lucide-react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000/api/v1";

function DataUpload({ onDataCommitted }) {
  const [file, setFile] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [savingDb, setSavingDb] = useState(false);
  const [error, setError] = useState("");
  const [saveSuccess, setSaveSuccess] = useState(null);

  async function uploadFile() {
    if (!file) {
      setError("Please choose a CSV or Excel file first.");
      return;
    }

    setLoading(true);
    setError("");
    setReport(null);
    setSaveSuccess(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE}/uploads/profile`, {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (!response.ok || result.error) {
        throw new Error(result.error || "Upload validation failed.");
      }

      setReport(result.report);
    } catch (uploadError) {
      setError(uploadError.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveToDatabase() {
    if (!file) return;
    setSavingDb(true);
    setError("");

    try {
      const result = await commitUpload(file);
      if (result.status === "error") {
        throw new Error(result.error || "Failed to commit data to database.");
      }
      setSaveSuccess(result);
      if (onDataCommitted) {
        onDataCommitted();
      }
    } catch (saveErr) {
      setError(saveErr.message);
    } finally {
      setSavingDb(false);
    }
  }

  function loadSampleData() {
    const csvContent =
      "date,department,admissions,emergency_cases,bed_occupancy,icu_occupancy,doctor_workload,staff_workload\n" +
      "2026-10-03,Emergency,83,21,0.91,0.89,12.3,9.5\n" +
      "2026-10-04,Emergency,85,22,0.93,0.90,12.7,9.7\n" +
      "2026-10-05,Emergency,87,23,0.95,0.92,13.1,10.0\n" +
      "2026-10-06,Emergency,84,20,0.92,0.88,12.5,9.6\n" +
      "2026-10-07,Emergency,80,18,0.89,0.85,11.9,9.2\n";

    const blob = new Blob([csvContent], { type: "text/csv" });
    const sampleFile = new File([blob], "sample_hospital_surge.csv", {
      type: "text/csv",
    });
    setFile(sampleFile);
    setError("");
    setReport(null);
    setSaveSuccess(null);
  }

  return (
    <section className="card upload-page">
      <div className="section-title">
        <FileSpreadsheet size={20} />
        <h2>Data Upload & Quality Engine</h2>
      </div>

      <p className="muted">
        Upload operational spreadsheets (.CSV, .XLSX) to profile data quality,
        inspect missing fields and duplicates, and commit valid operational snapshots into the hospital database.
      </p>

      <div className="upload-box">
        <div className="file-input-row">
          <input
            type="file"
            accept=".csv,.xlsx"
            onChange={(event) => {
              setFile(event.target.files[0]);
              setError("");
              setReport(null);
              setSaveSuccess(null);
            }}
          />
          <button
            type="button"
            className="secondary-btn"
            onClick={loadSampleData}
          >
            Load Sample Surge Data
          </button>
        </div>

        {file && (
          <div className="selected-file-badge">
            <UploadCloud size={16} /> Selected: <b>{file.name}</b> ({(file.size / 1024).toFixed(1)} KB)
          </div>
        )}

        <div className="action-row">
          <button onClick={uploadFile} disabled={loading || !file}>
            {loading ? "Profiling file..." : "Upload and Validate"}
          </button>
        </div>
      </div>

      {error && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {saveSuccess && (
        <div className="alert alert-success">
          <CheckCircle2 size={18} />
          <div>
            <strong>Database Commit Successful!</strong>
            <p>
              {saveSuccess.message} (Range: {saveSuccess.date_min} to {saveSuccess.date_max}).
              The new data has been written to the database and will update dashboard analytics.
            </p>
          </div>
        </div>
      )}

      {report && (
        <div className="simulation report-card">
          <div className="report-header">
            <h3>Data Quality Report</h3>
            <span className="badge">
              {report.valid_records_after_basic_cleaning} Valid Records
            </span>
          </div>

          <div className="metrics-summary-grid">
            <div className="metric-box">
              <span>Total Received</span>
              <b>{report.total_records}</b>
            </div>
            <div className="metric-box">
              <span>Duplicate Rows</span>
              <b>{report.duplicate_records}</b>
            </div>
            <div className="metric-box">
              <span>Missing Values</span>
              <b>{report.missing_values}</b>
            </div>
            <div className="metric-box">
              <span>Invalid Dates</span>
              <b>{report.invalid_dates}</b>
            </div>
          </div>

          {report.missing_columns?.length > 0 && (
            <p className="critical">
              Missing columns: {report.missing_columns.join(", ")}
            </p>
          )}

          {report.cleaned_preview?.length > 0 && (
            <div className="preview-table">
              <div className="table-header-flex">
                <h4>Cleaned Data Preview (Top Rows)</h4>
                <small className="muted">Standardized ISO dates and deduplicated entries</small>
              </div>

              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      {Object.keys(report.cleaned_preview[0]).map((column) => (
                        <th key={column}>{column}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {report.cleaned_preview.map((row, rowIndex) => (
                      <tr key={rowIndex}>
                        {Object.values(row).map((value, columnIndex) => (
                          <td key={columnIndex}>{String(value)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="commit-action-box">
            <div>
              <p>
                <b>Ready to persist?</b> Validating ensures integrity before saving records to PostgreSQL or SQLite.
              </p>
            </div>
            <button
              className="save-db-btn"
              onClick={handleSaveToDatabase}
              disabled={savingDb || report.valid_records_after_basic_cleaning === 0}
            >
              <Database size={16} />
              {savingDb ? "Saving to Database..." : "Save Valid Records to Database"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

export default DataUpload;