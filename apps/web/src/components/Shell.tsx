import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { Brand } from "./Brand";
import { Icon, IconName } from "./Icon";

const NAV: { to: string; label: string; icon: IconName; fab?: boolean }[] = [
  { to: "/", label: "Home", icon: "house" },
  { to: "/plan", label: "Plan", icon: "calendar" },
  { to: "/ask", label: "Ask", icon: "sparkles", fab: true },
  { to: "/records", label: "Records", icon: "folder" },
  { to: "/circle", label: "Circle", icon: "users" },
];

export default function Shell() {
  const { circle, user, logout } = useAuth();
  const nav = useNavigate();
  const [approvals, setApprovals] = useState(0);
  const [menu, setMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!circle) return;
    api.today(circle.id).then((t) => setApprovals(t.approvals_waiting.length)).catch(() => {});
    const iv = setInterval(() => {
      api.today(circle.id).then((t) => setApprovals(t.approvals_waiting.length)).catch(() => {});
    }, 15000);
    return () => clearInterval(iv);
  }, [circle?.id]);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenu(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const signOut = () => {
    setMenu(false);
    logout();
    nav("/login");
  };

  const initial = (user?.name ?? "?").slice(0, 1).toUpperCase();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="logo"><Brand size={32} /></div>
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.to === "/"}
            className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
            <Icon name={n.icon} size={19} /> {n.label}
            {n.to === "/records" && approvals > 0 && <span className="badge solid-coral">{approvals}</span>}
          </NavLink>
        ))}
        <NavLink to="/activity" className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
          <Icon name="scroll" size={19} /> Activity
        </NavLink>
        <div className="foot">
          <div className="tiny">Circle</div>
          <b>{circle?.recipient_name ?? "-"}</b>
          <div className="tiny">{user?.name}</div>
          <button className="btn small ghost" style={{ marginTop: 10, width: "100%" }} onClick={signOut}>
            <Icon name="logOut" size={15} /> Sign out
          </button>
        </div>
      </aside>

      <div className="shell-col">
        <header className="topbar mobile-only">
          <Brand size={28} />
          <div className="account" ref={menuRef}>
            <button className="avatar account-btn" aria-expanded={menu} aria-haspopup="menu"
              aria-label="Account" onClick={() => setMenu((v) => !v)}>
              {initial}
            </button>
            {menu && (
              <div className="account-menu" role="menu">
                <div className="account-who">
                  <b>{user?.name}</b>
                  <div className="tiny">{circle?.recipient_name ?? "No circle"}</div>
                </div>
                <button className="account-item" role="menuitem" onClick={signOut}>
                  <Icon name="logOut" size={16} /> Sign out
                </button>
              </div>
            )}
          </div>
        </header>

        <main className="main"><Outlet /></main>
      </div>

      <nav className="tabbar">
        {NAV.map((n) =>
          n.fab ? (
            <NavLink key={n.to} to={n.to} className="tab fab-tab" aria-label="Ask">
              <span className="fab"><Icon name="sparkles" size={24} /></span>
            </NavLink>
          ) : (
            <NavLink key={n.to} to={n.to} end={n.to === "/"}
              className={({ isActive }) => `tab${isActive ? " active" : ""}`}>
              {n.to === "/records" && approvals > 0 && <span className="dot" />}
              <span className="ticon"><Icon name={n.icon} size={21} /></span>
              {n.label}
            </NavLink>
          ),
        )}
      </nav>
    </div>
  );
}
