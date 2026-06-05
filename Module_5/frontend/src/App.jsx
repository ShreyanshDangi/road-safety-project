// Module 5 — Heatmap Dashboard
// React + Tailwind + Leaflet.js + Chart.js
// Talks to FastAPI backend at http://localhost:8005/api

import { useState, useEffect, useCallback, useRef } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import "leaflet/dist/leaflet.css";
import "./index.css";

// ── API helpers ──────────────────────────────────────────────────────────────
//(relative — works at any domain):
const API      = "/api";
const AUTH_API = "";
const MODULE4_API = "";

// Token helpers
const getToken   = ()  => localStorage.getItem("authority_token");
const setToken   = (t) => localStorage.setItem("authority_token", t);
const clearToken = ()  => localStorage.removeItem("authority_token");

// Modified apiFetch — now sends Authorization header
async function apiFetch(path) {
  const token = getToken();
  const res = await fetch(API + path, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (res.status === 401) {
    clearToken();
    window.dispatchEvent(new CustomEvent("auth:expired"));
    return null;
  }
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ── Constants ────────────────────────────────────────────────────────────────
const SEV_COLOR = { HIGH: "#E24B4A", MEDIUM: "#EF9F27", LOW: "#639922" };
const DENSITY_COLOR = { high: "#E24B4A", medium: "#EF9F27", low: "#639922", isolated: "#888780" };

const STATUS_STYLE = {
  PENDING:     "bg-red-50   text-red-800  border border-red-200",
  IN_PROGRESS: "bg-blue-50  text-blue-800 border border-blue-200",
  RESOLVED:    "bg-green-50 text-green-800 border border-green-200",
  FLAGGED:     "bg-yellow-50 text-yellow-800 border border-yellow-200",
};

const STATUS_LABEL = {
  PENDING:     "Open",
  IN_PROGRESS: "Assigned",
  RESOLVED:    "Verified",
  FLAGGED:     "Flagged",
};

const PRIORITY_STYLE = {
  HIGH:   "bg-red-100 text-red-700 border border-red-200",
  MEDIUM: "bg-orange-100 text-orange-700 border border-orange-200",
  LOW:    "bg-green-100 text-green-700 border border-green-200",
};

const AUTHORITY_ICON = {
  PWD:       "🏗️",
  Municipal: "🏛️",
  NHAI:      "🛣️",
  Panchayat: "🏘️",
};

// ── Helpers ──────────────────────────────────────────────────────────────────
function formatDate(dateStr) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  return isNaN(d) ? dateStr : d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function formatTime(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return isNaN(d) ? "" : d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

// ── Login Screen ─────────────────────────────────────────────────────────────
function LoginScreen({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState(null);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${AUTH_API}/auth/login`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Login failed");
        return;
      }
      setToken(data.access_token);
      onLogin(data.username);
    } catch (err) {
      setError("Cannot reach server. Make sure main.py is running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 w-full max-w-sm p-8">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center mb-3">
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
          </div>
          <h1 className="text-xl font-semibold text-gray-900">Authority Portal</h1>
          <p className="text-sm text-gray-400 mt-1">Road Safety Management System</p>
        </div>
        
        {/* Form */}
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="Enter your username"
              required
              className="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm
                focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
              className="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm
                focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </div>
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-2.5">
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-blue-600 text-white rounded-xl font-medium text-sm
              hover:bg-blue-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed
              flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
                Signing in…
              </>
            ) : "Sign In"}
          </button>
        </form>
        <p className="text-xs text-gray-400 text-center mt-6">
          Citizen complaint portal →{" "}
          <a href="http://localhost:8000/citizen" target="_blank" rel="noreferrer"
            className="text-blue-500 hover:underline">
            localhost:8000/citizen
          </a>
        </p>
      </div>
    </div>
  );
}

// ── Sub-components ───────────────────────────────────────────────────────────
function MetricCard({ label, value, sub, colorClass = "text-gray-900" }) {
  return (
    <div className="bg-gray-50 rounded-xl p-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-2xl font-medium ${colorClass}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

// ── Image Lightbox ───────────────────────────────────────────────────────────
function ImageLightbox({ src, alt, onClose }) {
  useEffect(() => {
    const handleKey = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-[60] p-4"
      onClick={onClose}
    >
      <div className="relative max-w-4xl max-h-full w-full flex flex-col items-center" onClick={e => e.stopPropagation()}>
        <button
          onClick={onClose}
          className="absolute -top-10 right-0 text-white text-2xl w-8 h-8 flex items-center justify-center rounded-full hover:bg-white hover:bg-opacity-20 transition-colors"
        >
          ×
        </button>
        <img
          src={src}
          alt={alt}
          className="max-w-full max-h-[85vh] object-contain rounded-xl shadow-2xl"
        />
        <p className="text-white text-xs mt-3 opacity-60">{alt} · Click anywhere or press Esc to close</p>
      </div>
    </div>
  );
}

// ── Complaint Row — detailed card for authorities ────────────────────────────
function ComplaintRow({ item, onOpen }) {
  const priority = item.priority || "LOW";
  const status   = item.status   || "PENDING";
  const authority = item.authority || "—";

  return (
    <div className="rounded-xl border border-gray-100 bg-gray-50 hover:bg-white hover:border-gray-200 hover:shadow-sm transition-all duration-150 overflow-hidden">
      {/* Top bar with priority indicator */}
      <div
        className="h-1 w-full"
        style={{ background: SEV_COLOR[priority] }}
      />

      <div className="p-3 space-y-2">
        {/* Row 1: ID + Status + Priority */}
        <div className="flex items-center justify-between gap-2">
          <span className="font-mono text-xs text-gray-400 truncate">
            #{String(item.complaint_id).slice(0, 12)}…
          </span>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-semibold ${PRIORITY_STYLE[priority]}`}>
              {priority}
            </span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${STATUS_STYLE[status]}`}>
              {STATUS_LABEL[status]}
            </span>
          </div>
        </div>

        {/* Row 2: Damage class + AI confidence */}
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-semibold text-gray-900 leading-tight">
            {item.damage_class || "Unknown Damage"}
          </p>
          <div className="flex-shrink-0 text-right">
            <div className="flex items-center gap-1">
              <div className="w-12 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${Math.round((item.confidence || 0) * 100)}%`,
                    background: (item.confidence || 0) >= 0.75 ? "#639922" : (item.confidence || 0) >= 0.5 ? "#EF9F27" : "#E24B4A"
                  }}
                />
              </div>
              <span className="text-[10px] text-gray-500 font-mono">
                {((item.confidence || 0) * 100).toFixed(0)}%
              </span>
            </div>
            <p className="text-[9px] text-gray-400 text-right">AI score</p>
          </div>
        </div>

        {/* Row 3: Location */}
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <svg className="w-3 h-3 flex-shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a2 2 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span className="truncate">{item.address || item.city || "Location not available"}</span>
        </div>

        {/* Row 4: GPS coordinates */}
        {item.lat && item.lon && (
          <div className="flex items-center gap-1 text-[10px] text-gray-400 font-mono">
            <svg className="w-2.5 h-2.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064" />
            </svg>
            {Number(item.lat).toFixed(5)}, {Number(item.lon).toFixed(5)}
          </div>
        )}

        {/* Row 5: Authority + Date */}
        <div className="flex items-center justify-between gap-2 pt-1 border-t border-gray-100">
          <div className="flex items-center gap-1.5">
            <span className="text-sm">{AUTHORITY_ICON[authority] || "🏢"}</span>
            <div>
              <p className="text-xs font-semibold text-gray-700">{authority}</p>
              <p className="text-[9px] text-gray-400">Responsible Authority</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-[10px] text-gray-500">{formatDate(item.reported_at || item.created_at)}</p>
            <p className="text-[9px] text-gray-400">{formatTime(item.reported_at || item.created_at)}</p>
          </div>
        </div>

        {/* Row 6: Action button */}
        <button
          onClick={() => onOpen(item)}
          className="w-full text-xs py-1.5 rounded-lg border border-orange-200 text-orange-700 bg-orange-50 hover:bg-orange-100 transition-colors font-medium"
        >
          View & Submit Repair →
        </button>
      </div>
    </div>
  );
}

function MapLayer({ clusters, noise }) {
  const map = useMap();

  useEffect(() => {
    if (clusters.length === 0 && noise.length === 0) return;
    const allPts = [
      ...clusters.map((c) => [c.centroid_lat, c.centroid_lon]),
      ...noise.map((n) => [n.lat, n.lon]),
    ].filter(([lat, lon]) => lat != null && lon != null);

    if (allPts.length > 0) {
      try {
        const L = window.L;
        if (L) map.fitBounds(L.latLngBounds(allPts), { padding: [30, 30] });
      } catch (_) {}
    }
  }, [clusters, noise, map]);

  return (
    <>
      {clusters.map((cl) => (
        <CircleMarker
          key={`cluster-${cl.cluster_id}`}
          center={[cl.centroid_lat, cl.centroid_lon]}
          radius={Math.max(14, cl.count * 6)}
          pathOptions={{
            color:       DENSITY_COLOR[cl.density],
            fillColor:   DENSITY_COLOR[cl.density],
            fillOpacity: 0.45,
            weight:      2,
          }}
        >
          <Popup>
            <strong>Cluster #{cl.cluster_id + 1}</strong><br />
            {cl.count} complaints · {cl.density} density<br />
            {cl.dominant_city || "—"}<br />
            <small>
              High: {cl.priority_counts?.HIGH || 0} · Med: {cl.priority_counts?.MEDIUM || 0} · Low: {cl.priority_counts?.LOW || 0}
            </small>
          </Popup>
        </CircleMarker>
      ))}
      {noise.map((pt) => (
        <CircleMarker
          key={`noise-${pt.complaint_id}`}
          center={[pt.lat, pt.lon]}
          radius={5}
          pathOptions={{
            color:       SEV_COLOR[pt.priority] || "#888",
            fillColor:   SEV_COLOR[pt.priority] || "#888",
            fillOpacity: 0.6,
            weight:      1,
          }}
        >
          <Popup>
            <strong>{String(pt.complaint_id).slice(0, 8)}…</strong><br />
            {pt.damage_class || "—"} · {pt.address || pt.city || "—"}<br />
            {pt.authority || "—"} · {STATUS_LABEL[pt.status] || pt.status}
          </Popup>
        </CircleMarker>
      ))}
    </>
  );
}

// ── Repair Panel Modal ───────────────────────────────────────────────────────
function RepairPanel({ complaint, onClose, onVerified }) {
  const [repairImage,    setRepairImage]    = useState(null);
  const [repairImageURL, setRepairImageURL] = useState(null);
  const [submitting,     setSubmitting]     = useState(false);
  const [result,         setResult]         = useState(null);
  const [lightboxSrc,    setLightboxSrc]    = useState(null);

  // Lock page scroll while modal is open; restore when it unmounts
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prev; };
  }, []);

  const verdictConfig = {
    REPAIRED:     { icon: "✅", label: "Repair Verified",  bg: "bg-green-50  border-green-200",  text: "text-green-800" },
    NOT_REPAIRED: { icon: "❌", label: "Not Repaired",     bg: "bg-red-50    border-red-200",    text: "text-red-800"   },
    SUSPICIOUS:   { icon: "⚠️", label: "Suspicious",      bg: "bg-yellow-50 border-yellow-200", text: "text-yellow-800"},
    INCONCLUSIVE: { icon: "❓", label: "Inconclusive",     bg: "bg-gray-50   border-gray-200",   text: "text-gray-700"  },
  };

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setRepairImage(file);
    setRepairImageURL(URL.createObjectURL(file));
    setResult(null);
  };

  const handleSubmit = async () => {
    if (!repairImage) return;
    setSubmitting(true);
    setResult(null);

    let repairLat = complaint.lat;
    let repairLon = complaint.lon;
    try {
      const pos = await new Promise((res, rej) =>
        navigator.geolocation.getCurrentPosition(res, rej, { timeout: 5000 })
      );
      repairLat = pos.coords.latitude;
      repairLon = pos.coords.longitude;
    } catch (_) {}

    const formData = new FormData();
    formData.append("complaint_id", complaint.complaint_id);
    formData.append("after_image",  repairImage);
    formData.append("repair_lat",   repairLat);
    formData.append("repair_lon",   repairLon);

    try {
      const res = await fetch(`${MODULE4_API}/repair/submit`, {
        method: "POST",
        body:   formData,
      });

      // Parse JSON regardless of status so we can surface backend error messages
      let data;
      try {
        data = await res.json();
      } catch {
        throw new Error(`HTTP ${res.status} — response was not valid JSON`);
      }

      if (!res.ok) {
        throw new Error(
          data?.detail || data?.message || data?.reason || `HTTP ${res.status} from Module 4`
        );
      }

      setResult(data);
      // Data is refreshed in the background; authority closes the panel manually
    } catch (err) {
      const isCors = err instanceof TypeError && err.message.toLowerCase().includes("fetch");
      setResult({
        verdict: "INCONCLUSIVE",
        reason: isCors
          ? "Network error — Module 4 may be blocking cross-origin requests (CORS). Add the frontend origin to Module 4's allowed origins and retry."
          : `Module 4 error: ${err.message}`,
      });
      console.error("[RepairPanel] submit error:", err);
    } finally {
      setSubmitting(false);
    }
  };

  const vc = result ? (verdictConfig[result.verdict] || verdictConfig.INCONCLUSIVE) : null;
  const priority = complaint.priority || "LOW";
  const status   = complaint.status   || "PENDING";
  const authority = complaint.authority || "—";

  // If a conclusive verdict was reached, refresh the dashboard when authority closes
  const handleClose = () => {
    const conclusive = result?.verdict === "REPAIRED" || result?.verdict === "NOT_REPAIRED";
    if (conclusive) onVerified();
    else onClose();
  };

  return (
    <>
      {/* Lightbox for before image */}
      {lightboxSrc && (
        <ImageLightbox
          src={lightboxSrc}
          alt="Before repair — damage photo"
          onClose={() => setLightboxSrc(null)}
        />
      )}

      <div
        className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
        onClick={(e) => { if (e.target === e.currentTarget) handleClose(); }}
      >
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden max-h-[95vh] flex flex-col">

          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 flex-shrink-0">
            <div>
              <h3 className="font-semibold text-gray-900 text-base">Submit Repair Proof</h3>
              <p className="text-xs text-gray-400 mt-0.5 font-mono">
                #{String(complaint.complaint_id).slice(0, 20)}…
              </p>
            </div>
            <button
              onClick={handleClose}
              className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600 text-lg transition-colors"
            >
              ×
            </button>
          </div>

          {/* Scrollable content */}
          <div className="p-5 space-y-4 overflow-y-auto flex-1">

            {/* ── Detailed Complaint Info for Authority ── */}
            <div className="rounded-xl border border-gray-200 overflow-hidden">

              {/* Priority banner */}
              <div
                className="px-4 py-2 flex items-center justify-between"
                style={{ background: SEV_COLOR[priority] + "18", borderBottom: `2px solid ${SEV_COLOR[priority]}40` }}
              >
                <div className="flex items-center gap-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                    style={{ background: SEV_COLOR[priority] }}
                  />
                  <span className="text-sm font-bold" style={{ color: SEV_COLOR[priority] }}>
                    {priority} PRIORITY
                  </span>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_STYLE[status]}`}>
                  {STATUS_LABEL[status]}
                </span>
              </div>

              {/* Before image + basic info */}
              <div className="p-3 flex gap-3">
                <div className="flex-shrink-0 relative group">
                  {complaint.image_url ? (
                    <>
                      <img
                        src={complaint.image_url}
                        alt="Before repair"
                        className="w-24 h-24 object-cover rounded-xl border border-gray-200 cursor-zoom-in"
                        onClick={() => setLightboxSrc(complaint.image_url)}
                      />
                      {/* Zoom hint */}
                      <button
                        onClick={() => setLightboxSrc(complaint.image_url)}
                        className="absolute inset-0 flex items-end justify-center pb-1.5 opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <span className="bg-black bg-opacity-60 text-white text-[9px] px-1.5 py-0.5 rounded-full">
                          🔍 Expand
                        </span>
                      </button>
                    </>
                  ) : (
                    <div className="w-24 h-24 rounded-xl bg-gray-100 border border-gray-200 flex items-center justify-center text-gray-300 text-2xl">
                      📷
                    </div>
                  )}
                  <p className="text-[9px] text-gray-400 text-center mt-1">Before</p>
                </div>

                <div className="flex-1 min-w-0 space-y-1.5">
                  <p className="text-sm font-bold text-gray-900">
                    {complaint.damage_class || "Road Damage"}
                  </p>

                  {/* AI confidence */}
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${Math.round((complaint.confidence || 0) * 100)}%`,
                          background: (complaint.confidence || 0) >= 0.75 ? "#639922"
                            : (complaint.confidence || 0) >= 0.5 ? "#EF9F27" : "#E24B4A"
                        }}
                      />
                    </div>
                    <span className="text-xs text-gray-500 font-mono flex-shrink-0">
                      {((complaint.confidence || 0) * 100).toFixed(0)}% AI
                    </span>
                  </div>

                  {/* Description / remarks */}
                  {complaint.description && (
                    <p className="text-xs text-gray-500 italic leading-tight">
                      "{complaint.description}"
                    </p>
                  )}
                </div>
              </div>

              {/* Detail grid */}
              <div className="grid grid-cols-2 gap-px bg-gray-100 border-t border-gray-100">
                {/* Authority */}
                <div className="bg-white px-3 py-2">
                  <p className="text-[9px] text-gray-400 uppercase tracking-wider mb-0.5">Responsible Authority</p>
                  <p className="text-sm font-semibold text-gray-900 flex items-center gap-1">
                    <span>{AUTHORITY_ICON[authority] || "🏢"}</span>
                    {authority}
                  </p>
                  {complaint.department && (
                    <p className="text-[10px] text-gray-500">{complaint.department}</p>
                  )}
                </div>

                {/* Location */}
                <div className="bg-white px-3 py-2">
                  <p className="text-[9px] text-gray-400 uppercase tracking-wider mb-0.5">Location</p>
                  <p className="text-xs font-medium text-gray-800 truncate">
                    {complaint.address || complaint.city || "—"}
                  </p>
                  {complaint.ward && (
                    <p className="text-[10px] text-gray-500">Ward: {complaint.ward}</p>
                  )}
                </div>

                {/* GPS */}
                <div className="bg-white px-3 py-2">
                  <p className="text-[9px] text-gray-400 uppercase tracking-wider mb-0.5">GPS Coordinates</p>
                  {complaint.lat && complaint.lon ? (
                    <p className="text-xs font-mono text-gray-700">
                      {Number(complaint.lat).toFixed(5)},<br />{Number(complaint.lon).toFixed(5)}
                    </p>
                  ) : (
                    <p className="text-xs text-gray-400">Not available</p>
                  )}
                </div>

                {/* Reported */}
                <div className="bg-white px-3 py-2">
                  <p className="text-[9px] text-gray-400 uppercase tracking-wider mb-0.5">Reported On</p>
                  <p className="text-xs font-medium text-gray-800">
                    {formatDate(complaint.reported_at || complaint.created_at)}
                  </p>
                  <p className="text-[10px] text-gray-500">
                    {formatTime(complaint.reported_at || complaint.created_at)}
                  </p>
                </div>

                {/* Damage severity details */}
                {complaint.area_affected && (
                  <div className="bg-white px-3 py-2">
                    <p className="text-[9px] text-gray-400 uppercase tracking-wider mb-0.5">Area Affected</p>
                    <p className="text-xs font-medium text-gray-800">{complaint.area_affected}</p>
                  </div>
                )}

                {/* Duplicate count */}
                {complaint.duplicate_count > 0 && (
                  <div className="bg-white px-3 py-2">
                    <p className="text-[9px] text-gray-400 uppercase tracking-wider mb-0.5">Duplicate Reports</p>
                    <p className="text-xs font-medium text-orange-700">
                      {complaint.duplicate_count} similar report{complaint.duplicate_count > 1 ? "s" : ""} merged
                    </p>
                  </div>
                )}

                {/* Reporter info */}
                {complaint.reporter_name && (
                  <div className="bg-white px-3 py-2">
                    <p className="text-[9px] text-gray-400 uppercase tracking-wider mb-0.5">Reported By</p>
                    <p className="text-xs font-medium text-gray-800">{complaint.reporter_name}</p>
                    {complaint.reporter_contact && (
                      <p className="text-[10px] text-gray-500">{complaint.reporter_contact}</p>
                    )}
                  </div>
                )}

                {/* Verification status */}
                <div className="bg-white px-3 py-2">
                  <p className="text-[9px] text-gray-400 uppercase tracking-wider mb-0.5">Verification</p>
                  <p className="text-xs font-medium text-gray-800">
                    {complaint.verified_by_ai ? "✅ AI verified" : "⏳ Pending AI review"}
                  </p>
                </div>
              </div>

              {/* Remarks / notes from system */}
              {complaint.remarks && (
                <div className="px-3 py-2 bg-amber-50 border-t border-amber-100">
                  <p className="text-[9px] text-amber-700 uppercase tracking-wider mb-0.5 font-semibold">System Notes</p>
                  <p className="text-xs text-amber-800">{complaint.remarks}</p>
                </div>
              )}
            </div>

            {/* After image upload */}
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">After-Repair Photo</p>
              <label className="block cursor-pointer">
                <div className={`border-2 border-dashed rounded-xl transition-all
                  ${repairImageURL
                    ? "border-gray-200 p-0 overflow-hidden"
                    : "border-gray-200 p-6 text-center hover:border-blue-400 hover:bg-blue-50"}`}
                >
                  {repairImageURL ? (
                    <div className="relative">
                      <img
                        src={repairImageURL}
                        alt="After repair"
                        className="w-full h-40 object-cover"
                      />
                      <div className="absolute bottom-2 right-2 bg-black bg-opacity-50 text-white text-xs px-2 py-1 rounded-lg">
                        Tap to change
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="text-3xl mb-2">📷</div>
                      <p className="text-sm text-gray-500">
                        <span className="text-blue-600 font-medium">Upload after-repair photo</span>
                      </p>
                      <p className="text-xs text-gray-400 mt-1">JPG or PNG</p>
                    </>
                  )}
                </div>
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={handleImageChange}
                />
              </label>
            </div>

            {/* Verdict result */}
            {result && vc && (
              <div className={`rounded-xl p-4 border ${vc.bg}`}>
                <p className={`font-semibold text-sm mb-1 ${vc.text}`}>
                  {vc.icon} {vc.label}
                </p>
                <p className="text-xs text-gray-600 leading-relaxed">{result.reason}</p>
                <div className="flex flex-wrap gap-3 mt-2 text-xs text-gray-500">
                  {result.ssim_score != null &&
                    <span>SSIM: {result.ssim_score.toFixed(3)}</span>
                  }
                  {result.potholes_detected != null &&
                    <span>Potholes found: {result.potholes_detected}</span>
                  }
                  {result.gps_distance_m != null &&
                    <span>GPS distance: {result.gps_distance_m.toFixed(0)}m</span>
                  }
                  {result.confidence_level &&
                    <span>Confidence: {result.confidence_level}</span>
                  }
                </div>
              </div>
            )}

            {/* Submit button */}
            <button
              disabled={!repairImage || submitting}
              onClick={handleSubmit}
              className={`w-full py-3 rounded-xl font-semibold text-sm transition-all flex items-center justify-center gap-2
                ${!repairImage || submitting
                  ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                  : "bg-blue-600 text-white hover:bg-blue-700 active:scale-95"}`}
            >
              {submitting ? (
                <>
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                  </svg>
                  Verifying with Module 4…
                </>
              ) : result ? (
                "Resubmit"
              ) : (
                "Submit & Verify Repair"
              )}
            </button>

          </div>
        </div>
      </div>
    </>
  );
}

// ── Main Dashboard ───────────────────────────────────────────────────────────
export function HeatmapDashboard({ username, onLogout }) {
  const [stats,      setStats]      = useState(null);
  const [complaints, setComplaints] = useState([]);
  const [clusters,   setClusters]   = useState([]);
  const [noise,      setNoise]      = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState(null);

  const [priority,   setPriority]   = useState("all");
  const [authority,  setAuthority]  = useState("all");
  const [status,     setStatus]     = useState("all");
  const [eps,        setEps]        = useState(50);
  const [exclDupes,  setExclDupes]  = useState(true);

  const [selectedComplaint, setSelectedComplaint] = useState(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const priQ    = priority  !== "all" ? `&priority=${priority}`   : "";
      const authQ   = authority !== "all" ? `&authority=${authority}` : "";
      const statusQ = status    !== "all" ? `&status=${status}`       : "";
      const dupeQ   = `&exclude_duplicates=${exclDupes}`;

      const [statsRes, cmpRes, clRes] = await Promise.all([
        apiFetch("/stats"),
        apiFetch(`/complaints?${priQ}${authQ}${statusQ}${dupeQ}`),
        apiFetch(`/clusters?eps=${eps}&min_pts=2${priQ}${authQ}${statusQ}${dupeQ}`),
      ]);

      setStats(statsRes);
      setComplaints(cmpRes.complaints || []);
      setClusters(clRes.clusters || []);
      setNoise(clRes.noise || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [priority, authority, status, eps, exclDupes]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleExport = () => {
    const priQ    = priority  !== "all" ? `&priority=${priority}`   : "";
    const authQ   = authority !== "all" ? `&authority=${authority}` : "";
    const statusQ = status    !== "all" ? `&status=${status}`       : "";
    window.open(`${API}/export/csv?${priQ}${authQ}${statusQ}`, "_blank");
  };

  const trendData = stats?.daily_trend?.slice(-14) || [];

  return (
    <div className="min-h-screen bg-gray-50 font-sans">

      {/* Repair Panel Modal */}
      {selectedComplaint && (
        <RepairPanel
          complaint={selectedComplaint}
          onClose={() => setSelectedComplaint(null)}
          onVerified={() => {
            setSelectedComplaint(null);
            fetchAll();
          }}
        />
      )}

      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
          </div>
          <div>
            <h1 className="text-lg font-medium text-gray-900">Road Damage Heatmap</h1>
            <p className="text-xs text-gray-400">Module 5 — DBSCAN Cluster Dashboard</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchAll}
            className="text-sm px-3 py-1.5 border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-600 flex items-center gap-1">
            ↻ Refresh
          </button>
          <button onClick={handleExport}
            className="text-sm px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-1">
            ↓ Export CSV
          </button>
          <button
            onClick={onLogout}
            className="text-sm px-3 py-1.5 border border-red-200 rounded-lg hover:bg-red-50 text-red-600 flex items-center gap-1"
          >
            Sign out {username ? `(${username})` : ""}
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
            ⚠ Backend error: {error}
          </div>
        )}

        {/* Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <MetricCard
            label="Total Reports"
            value={stats?.total_complaints || 0}
            sub="all time"
          />
          <MetricCard
            label="High Priority"
            value={stats?.severity?.high || 0}
            sub={`${stats?.total_complaints ? Math.round((stats.severity.high || 0) / stats.total_complaints * 100) : 0}% of total`}
            colorClass="text-red-700"
          />
          <MetricCard
            label="Open"
            value={stats?.status?.open || 0}
            sub="awaiting action"
            colorClass="text-amber-700"
          />
          <MetricCard
            label="Verified Fixed"
            value={stats?.status?.verified || 0}
            sub="by Module 4"
            colorClass="text-green-700"
          />
          <MetricCard
            label="Avg AI Score"
            value={`${((stats?.avg_ai_score || 0) * 100).toFixed(0)}%`}
            sub="YOLOv8 confidence"
          />
        </div>

        {/* Filters */}
        <div className="bg-white border border-gray-200 rounded-xl px-4 py-3 flex flex-wrap gap-4 items-end">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Priority</label>
            <select value={priority} onChange={e => setPriority(e.target.value)}
              className="text-sm border border-gray-200 rounded-lg px-2 py-1.5">
              <option value="all">All</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Authority</label>
            <select value={authority} onChange={e => setAuthority(e.target.value)}
              className="text-sm border border-gray-200 rounded-lg px-2 py-1.5">
              <option value="all">All</option>
              <option value="PWD">PWD</option>
              <option value="Municipal">Municipal</option>
              <option value="NHAI">NHAI</option>
              <option value="Panchayat">Panchayat</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Status</label>
            <select value={status} onChange={e => setStatus(e.target.value)}
              className="text-sm border border-gray-200 rounded-lg px-2 py-1.5">
              <option value="all">All</option>
              <option value="PENDING">Open</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="RESOLVED">Resolved</option>
              <option value="FLAGGED">Flagged</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Cluster radius: {eps}m</label>
            <input type="range" min="20" max="200" step="10" value={eps}
              onChange={e => setEps(Number(e.target.value))} className="w-32" />
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input type="checkbox" checked={exclDupes}
              onChange={e => setExclDupes(e.target.checked)} className="rounded" />
            Exclude duplicates (Module 2)
          </label>
          {loading && <span className="text-xs text-blue-500 animate-pulse ml-auto">Clustering…</span>}
        </div>

        {/* Map + List — fixed height row; list scrolls internally, page stays still */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          <div
            className="lg:col-span-2 bg-white border border-gray-200 rounded-xl overflow-hidden"
            style={{ height: 460 }}
          >
            <MapContainer
              center={[25.340, 74.645]}
              zoom={13}
              style={{ height: "100%", width: "100%" }}
              scrollWheelZoom={true}
              zoomControl={true}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <MapLayer clusters={clusters} noise={noise} />
            </MapContainer>
          </div>

          {/* Complaint list — self-scrolling, same height as map */}
          <div
            className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col"
            style={{ height: 460 }}
          >
            <div className="flex items-center justify-between mb-3 flex-shrink-0">
              <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Active Complaints</h2>
              <span className="text-xs text-gray-400">{complaints.length} shown</span>
            </div>
            <div className="flex flex-col gap-2 overflow-y-auto flex-1 pr-0.5">
              {complaints
                .sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
                .map(item => (
                  <ComplaintRow
                    key={item.complaint_id}
                    item={item}
                    onOpen={(c) => setSelectedComplaint(c)}
                  />
                ))
              }
              {complaints.length === 0 && !loading && (
                <p className="text-sm text-gray-400 text-center py-8">No complaints match current filters.</p>
              )}
            </div>
          </div>
        </div>

        {/* Trend + Cluster Summary */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
              Reports by Day (last 14 days)
            </h2>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={trendData} margin={{ top: 0, right: 4, left: -20, bottom: 0 }}>
                <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={d => d.slice(5)} />
                <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                <Tooltip formatter={(v) => [v, "Reports"]} labelFormatter={l => `Date: ${l}`} />
                <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                  {trendData.map((_, i) => <Cell key={i} fill="#378ADD" />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            {trendData.length === 0 && (
              <p className="text-sm text-gray-400 text-center py-8">No trend data available.</p>
            )}
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
              DBSCAN Cluster Summary
            </h2>
            <div className="space-y-2">
              {clusters.length === 0 && (
                <p className="text-sm text-gray-400 text-center py-8">
                  No clusters with current parameters.
                </p>
              )}
              {clusters.map(cl => (
                <div key={`summary-${cl.cluster_id}`}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg border border-gray-100">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium flex-shrink-0"
                    style={{ background: DENSITY_COLOR[cl.density] }}>
                    {cl.count}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">{cl.dominant_city || "—"}</p>
                    <p className="text-xs text-gray-500">
                      {cl.density} density · {Object.entries(cl.authorities || {}).map(([d, n]) => `${d}: ${n}`).join(", ")}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-red-600">{cl.priority_counts?.HIGH || 0} high</p>
                    <p className="text-xs text-gray-400">
                      {cl.centroid_lat?.toFixed(4)}, {cl.centroid_lon?.toFixed(4)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-3 pt-3 border-t border-gray-100 flex gap-4 text-xs text-gray-400">
              <span>● high ≥5 pts</span>
              <span>● medium 3–4</span>
              <span>● low 1–2</span>
              <span>eps = {eps}m</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

// ── App Wrapper ──────────────────────────────────────────────────────────────
export default function App() {
  const [authed,   setAuthed]   = useState(!!getToken());
  const [username, setUsername] = useState(null);

  // Handle token expiry from any apiFetch call
  useEffect(() => {
    const handler = () => { clearToken(); setAuthed(false); };
    window.addEventListener("auth:expired", handler);
    return () => window.removeEventListener("auth:expired", handler);
  }, []);

  // Verify stored token on mount
  useEffect(() => {
    const token = getToken();
    if (!token) return;
    fetch(`${AUTH_API}/auth/verify`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(d => setUsername(d.username))
      .catch(() => { clearToken(); setAuthed(false); });
  }, []);

  if (!authed) {
    return <LoginScreen onLogin={(u) => { setAuthed(true); setUsername(u); }} />;
  }

  return <HeatmapDashboard username={username} onLogout={() => {
    clearToken();
    setAuthed(false);
    setUsername(null);
  }} />;
}