import React from "react";

export function Skeleton({ height = 16, width = "100%", style }) {
  return <div className="skeleton" style={{ height, width, ...style }} aria-hidden="true" />;
}

export function OverviewSkeleton() {
  return (
    <div className="page" aria-busy="true" aria-label="Loading dashboard">
      <Skeleton height={60} width="40%" />
      <div className="grid grid-hero">
        <div className="card"><Skeleton height={240} /></div>
        <div className="card stack"><Skeleton height={70} /><Skeleton height={70} /><Skeleton height={70} /></div>
      </div>
      <div className="grid grid-4">
        {[0, 1, 2, 3].map((i) => <div className="card" key={i}><Skeleton height={140} /></div>)}
      </div>
    </div>
  );
}

export function EmptyState({ icon: Icon, title, children, action }) {
  return (
    <div className="empty">
      {Icon && <Icon size={30} aria-hidden="true" />}
      <strong>{title}</strong>
      {children && <span>{children}</span>}
      {action}
    </div>
  );
}
