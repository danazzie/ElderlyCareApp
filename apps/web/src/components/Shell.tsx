import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";

const NAV = [
  { to: "/", label: "Home", icon: "🏠" },
  { to: "/plan", label: "Plan", icon: "🗓" },
  { to: "/ask", label: "Ask", icon: "✳️", fab: true },
  { to: "/records", label: "Records", icon: "📁" },
  { to: "/circle", label: "Circle", icon: "👥" },
];

export default function Shell() {
  const { circle, user, logout } = useAuth();
  const nav = useNavigate();
  const [approvals, setApprovals] = useState(0);

  useEffect(() => {
    if (!circle) return;
    api.today(circle.id).then((t) => setApprovals(t.approvals_waiting.length)).catch(() => {});
    const iv = setInterval(() => {
      api.today(circle.id).then((t) => setApprovals(t.approvals_waiting.length)).catch(() => {});
    }, 15000);
    return () => clearInterval(iv);
  }, [circle?.id]);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="logo"><img src="/icon.svg" alt="" /> Ahtama</div>
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.to === "/"}
            className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
            <span>{n.icon}</span> {n.label}
            {n.to === "/records" && approvals > 0 && <span className="badge solid-coral">{approvals}</span>}
          </NavLink>
        ))}
        <NavLink to="/activity" className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
          <span>📜</span> Activity
        </NavLink>
        <div className="foot">
          Circle: <b>{circle?.recipient_name ?? "—"}</b>
          <br />{user?.name}
          <br />
          <button className="btn small ghost" style={{ marginTop: 8 }}
            onClick={() => { logout(); nav("/login"); }}>Sign out</button>
        </div>
      </aside>

      <main className="main"><Outlet /></main>

      <nav className="tabbar">
        {NAV.map((n) =>
          n.fab ? (
            <NavLink key={n.to} to={n.to} className="tab fab-tab">
              <span className="fab">✳</span>
            </NavLink>
          ) : (
            <NavLink key={n.to} to={n.to} end={n.to === "/"}
              className={({ isActive }) => `tab${isActive ? " active" : ""}`}>
              {n.to === "/records" && approvals > 0 && <span className="dot" />}
              <span className="ticon">{n.icon}</span>
              {n.label}
            </NavLink>
          ),
        )}
      </nav>
    </div>
  );
}
