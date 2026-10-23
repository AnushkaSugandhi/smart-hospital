import {
  BarChart3, ClipboardList, GitBranch, History, LayoutDashboard, Play, ShieldCheck, UploadCloud,
} from "lucide-react";

// Sidebar groups, titles, one-line descriptions and the minimum role to see a page.
export const PAGES = [
  { key: "overview", label: "Overview", group: "Monitor", Icon: LayoutDashboard,
    description: "Live resource pressure, alerts and what to do next." },
  { key: "hindsight", label: "Hindsight", group: "Analyze", Icon: History,
    description: "Past situations most similar to today, and what worked then." },
  { key: "forecast", label: "Forecasting", group: "Analyze", Icon: BarChart3,
    description: "Projected demand and occupancy for the coming days." },
  { key: "cascade", label: "CascadeFlow", group: "Analyze", Icon: GitBranch,
    description: "How a surge in emergency spreads to wards, ICU and staff." },
  { key: "whatif", label: "What-if Simulator", group: "Analyze", Icon: Play,
    description: "Test a scenario before acting — nothing changes in the hospital." },
  { key: "decision", label: "Decision Center", group: "Act", Icon: ClipboardList,
    description: "Review recommendations and record decisions for the audit trail." },
  { key: "upload", label: "Data Upload", group: "Data & admin", Icon: UploadCloud, minRole: "Analyst",
    description: "Add daily operational data, check it, and undo uploads if needed." },
  { key: "audit", label: "Audit Log", group: "Data & admin", Icon: ShieldCheck, minRole: "Admin",
    description: "Who did what and when — filterable and exportable." },
];

export const PAGE_BY_KEY = Object.fromEntries(PAGES.map((p) => [p.key, p]));
export const GROUPS = [...new Set(PAGES.map((p) => p.group))];
