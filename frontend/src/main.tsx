import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, ArrowUpRight, CheckCircle2, CircleDashed, FileCode2, GitBranch, Play, ShieldCheck, Terminal, Upload, Zap } from "lucide-react";
import "./styles.css";

type Run = { id: string; repository: string; task: string; status: string; verdict?: string; language?: string; attempts: number; created_at?: string };
type Event = { stage: string; message: string; type: string; timestamp: number };

const stages = ["intake", "analysis", "baseline", "planning", "root-cause", "patch", "verification"];

function App() {
  const [repo, setRepo] = useState("");
  const [task, setTask] = useState("");
  const [run, setRun] = useState<Run | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [history, setHistory] = useState<Run[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { fetch("/api/runs").then(r => r.json()).then(setHistory).catch(() => undefined); }, []);

  async function launch() {
    setError(""); setBusy(true); setEvents([]);
    try {
      const response = await fetch("/api/runs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ repository: repo, task }) });
      if (!response.ok) throw new Error((await response.json()).detail || "Could not start run");
      const created = await response.json();
      setRun({ ...created, repository: repo, task, attempts: 0 });
      const stream = new EventSource(created.stream_url);
      stream.onmessage = (message) => { const event = JSON.parse(message.data) as Event; setEvents(previous => [...previous, event]); if (event.type === "error" || event.type === "warning") setBusy(false); };
      stream.onerror = () => { stream.close(); setBusy(false); fetch(`/api/runs/${created.id}`).then(r => r.json()).then(setRun).catch(() => undefined); };
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not start run"); setBusy(false); }
  }

  const activeStage = events.length ? events[events.length - 1].stage : undefined;
  return <main>
    <aside className="sidebar"><div className="brand"><span className="brand-mark"><Zap size={17} /></span><span>RepoPilot</span></div><p className="eyebrow">AUTONOMOUS ENGINEERING</p><nav><a className="selected"><Activity size={16} /> Mission control</a><a><GitBranch size={16} /> Repositories</a><a><ShieldCheck size={16} /> Verification log</a></nav><div className="sidebar-foot"><div className="online-dot" /> Agent runtime online<div className="version">HNX26PSI09 · v1.0</div></div></aside>
    <section className="workspace"><header><div><p className="kicker">MISSION CONTROL / NEW RUN</p><h1>Prove the fix.</h1><p className="subhead">Point RepoPilot at a repository. It will investigate, modify the real files, and earn its verdict through tests.</p></div><div className="header-status"><span className="pulse" /> SAFE MODE <span className="divider" /> 3 max attempts</div></header>
      <div className="grid"><section className="panel intake"><div className="panel-title"><span>01</span><h2>Define the mission</h2></div><label>Repository URL or local path<input value={repo} onChange={e => setRepo(e.target.value)} placeholder="https://github.com/org/project.git" /></label><label>Task for the engineer<textarea value={task} onChange={e => setTask(e.target.value)} placeholder="Fix the discount calculation when a coupon is expired..." rows={5} /></label><div className="intake-actions"><button className="upload"><Upload size={15} /> Upload .zip</button><button className="launch" disabled={busy || !repo || !task} onClick={launch}><Play size={15} /> {busy ? "Agent running" : "Launch agent"}<ArrowUpRight size={15} /></button></div>{error && <div className="error">{error}</div>}</section>
      <section className="panel monitor"><div className="panel-title"><span>02</span><h2>Live mission trace</h2>{run && <code>{run.id}</code>}</div><div className="pipeline">{stages.map((stage, index) => { const seen = events.some(e => e.stage === stage); const current = activeStage === stage; return <div className={`stage ${seen ? "seen" : ""} ${current ? "current" : ""}`} key={stage}><div className="stage-icon">{seen ? <CheckCircle2 size={15} /> : <CircleDashed size={15} />}</div><div><strong>{stage.replace("-", " ")}</strong><small>{seen ? (events.find(e => e.stage === stage)?.message || "Complete") : index === 6 ? "Awaiting evidence" : "Queued"}</small></div></div>; })}</div><div className="terminal"><div className="terminal-bar"><Terminal size={13} /> AGENT TELEMETRY <span>● LIVE</span></div>{events.length === 0 ? <div className="empty-trace">Launch a mission to stream evidence here.</div> : events.slice(-5).map((event, index) => <div className="log" key={`${event.timestamp}-${index}`}><time>{new Date(event.timestamp * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time><b>{event.stage}</b><span>{event.message}</span></div>)}</div></section></div>
      <section className="lower"><div><p className="kicker">VERIFICATION CONTRACT</p><h2>Every change has to earn trust.</h2><p className="muted">Baseline first. Minimal patch. Compile. Re-run the suite. Compare every test. No green checkmark without evidence.</p></div><div className="contract"><div><ShieldCheck size={19} /><b>Regression guardian</b><span>Previously passing tests stay passing</span></div><div><FileCode2 size={19} /><b>Minimal diff policy</b><span>Focused files, reviewable edits</span></div></div></section>
      <section className="history"><div className="panel-title"><span>03</span><h2>Recent missions</h2></div>{history.length === 0 ? <p className="muted">Your verified engineering history will appear here.</p> : history.slice(0, 4).map(item => <div className="history-row" key={item.id}><span className={`status-dot ${item.status}`} /><b>{item.task}</b><code>{item.language || "pending"}</code><span>{item.status}</span></div>)}</section>
    </section>
  </main>;
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);