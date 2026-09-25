import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Shell from "./components/Shell";
import Ask from "./pages/Ask";
import Circle from "./pages/Circle";
import DocumentReview from "./pages/DocumentReview";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Plan from "./pages/Plan";
import Records from "./pages/Records";

export default function App() {
  const { user, circle, loading } = useAuth();
  if (loading) return <div className="empty" style={{ paddingTop: "40dvh" }}><span className="spin dark" /></div>;

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" /> : <Login />} />
      {user && circle ? (
        <Route element={<Shell />}>
          <Route path="/" element={<Home />} />
          <Route path="/plan" element={<Plan />} />
          <Route path="/ask" element={<Ask />} />
          <Route path="/records" element={<Records />} />
          <Route path="/records/:docId" element={<DocumentReview />} />
          <Route path="/circle" element={<Circle />} />
          <Route path="/activity" element={<Circle activityOnly />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Route>
      ) : user ? (
        <Route path="*" element={<NoCircle />} />
      ) : (
        <Route path="*" element={<Navigate to="/login" />} />
      )}
    </Routes>
  );
}

function NoCircle() {
  const { createCircle, join, logout } = useAuth();
  return (
    <div className="hero">
      <div className="panel login-panel stack" style={{ margin: "auto" }}>
        <h3>Set up a care circle</h3>
        <p className="muted">Create a circle for the person you care for, or join with an invitation code.</p>
        <button className="btn primary" onClick={() => {
          const name = prompt("Who are you caring for? (name)");
          if (name) createCircle({ recipient_name: name, consent: confirm(`Do you confirm ${name} (or their legal representative) consents to keeping their care record in Ihtama?`) });
        }}>Create a circle</button>
        <button className="btn ghost" onClick={() => {
          const code = prompt("Invitation code (try AHMED123)");
          if (code) join(code.trim(), prompt("Your role: member or caregiver?", "member") ?? "member");
        }}>Join with a code</button>
        <button className="btn small ghost" onClick={logout}>Sign out</button>
      </div>
    </div>
  );
}
