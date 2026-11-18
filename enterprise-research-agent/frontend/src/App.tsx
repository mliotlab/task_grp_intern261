import { Link, Navigate, Route, Routes } from "react-router-dom";

import CollectionsPage from "./pages/CollectionsPage";
import LoginPage from "./pages/LoginPage";
import ResearchPage from "./pages/ResearchPage";

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <Link to="/" className="brand">
          Enterprise Research Agent
        </Link>
        <nav>
          <Link to="/collections">Collections</Link>
          <Link to="/research">Research</Link>
          <Link to="/login">Sign in</Link>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/collections" replace />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/collections" element={<CollectionsPage />} />
          <Route path="/research" element={<ResearchPage />} />
          <Route path="/research/:jobId" element={<ResearchPage />} />
        </Routes>
      </main>
    </div>
  );
}
