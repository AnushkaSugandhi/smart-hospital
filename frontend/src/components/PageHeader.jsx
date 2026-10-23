import React from "react";
import { PAGE_BY_KEY } from "../config/pages";
import { useApp } from "../context/AppContext";

export default function PageHeader({ page, children }) {
  const { navigate } = useApp();
  const meta = PAGE_BY_KEY[page];
  return (
    <div className="page-header">
      <div>
        <nav className="crumbs" aria-label="Breadcrumb">
          <ol>
            <li><button className="link-btn" style={{ textDecoration: "none", color: "inherit" }} onClick={() => navigate("overview")}>Home</button></li>
            <li>{meta.group}</li>
            <li aria-current="page">{meta.label}</li>
          </ol>
        </nav>
        <h1>{meta.label}</h1>
        <p>{meta.description}</p>
      </div>
      {children && <div className="row-wrap">{children}</div>}
    </div>
  );
}
