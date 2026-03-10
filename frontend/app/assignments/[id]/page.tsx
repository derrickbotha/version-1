"use client";
import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import { getAssignment, getAssignmentStatus, downloadUrl, type Assignment } from "@/lib/api";
import { CheckCircle, Clock, AlertCircle, Download, RefreshCw, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import clsx from "clsx";

const STAGES = [
  { key: "pending",      label: "Queued",          desc: "Assignment received, waiting to start" },
  { key: "researching",  label: "Researching",     desc: "Perplexity Sonar finding academic sources" },
  { key: "writing",      label: "Writing",          desc: "DeepSeek composing your assignment" },
  { key: "qa_check",     label: "QA Check",         desc: "Plagiarism, tone, and citation validation" },
  { key: "prof_review",  label: "Professor Review", desc: "Qualified professor reviewing your work" },
  { key: "completed",    label: "Completed",        desc: "Your assignment is ready" },
];

const STATUS_ORDER = STAGES.map(s => s.key);

function StageIndicator({ currentStatus }: { currentStatus: string }) {
  const currentIdx = STATUS_ORDER.indexOf(currentStatus);

  return (
    <div className="space-y-3">
      {STAGES.map((stage, idx) => {
        const done    = idx < currentIdx;
        const active  = idx === currentIdx;
        const pending = idx > currentIdx;

        return (
          <div key={stage.key} className="flex items-start gap-3">
            <div className={clsx(
              "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5",
              done    ? "bg-green-100" :
              active  ? "bg-brand-100 animate-pulse" :
                        "bg-gray-100"
            )}>
              {done ? (
                <CheckCircle className="w-4 h-4 text-green-600" />
              ) : active ? (
                <Clock className="w-4 h-4 text-brand-600" />
              ) : (
                <span className="w-2 h-2 rounded-full bg-gray-300" />
              )}
            </div>
            <div className={clsx("flex-1", pending && "opacity-40")}>
              <p className={clsx("text-sm font-medium",
                done ? "text-green-700" : active ? "text-brand-700" : "text-gray-500"
              )}>{stage.label}</p>
              <p className="text-xs text-gray-400">{stage.desc}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function AssignmentDetail() {
  const { id } = useParams<{ id: string }>();
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [pipelineLog, setPipelineLog] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const [a, s] = await Promise.all([getAssignment(id), getAssignmentStatus(id)]);
      setAssignment(a);
      setPipelineLog(s.pipeline_log ?? []);
    } catch {
      window.location.href = "/assignments";
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [id]);

  useEffect(() => {
    load();
    // Poll status every 15s while in progress
    const interval = setInterval(() => {
      if (assignment && !["completed", "failed"].includes(assignment.status)) {
        load();
      }
    }, 15000);
    return () => clearInterval(interval);
  }, [load, assignment?.status]);

  if (loading) return (
    <div className="flex h-screen items-center justify-center">
      <div className="animate-spin w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full" />
    </div>
  );

  const a = assignment!;
  const completed = a.status === "completed";
  const failed    = a.status === "failed";

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-surface">
        <div className="max-w-4xl mx-auto px-6 py-8">

          {/* Back */}
          <Link href="/assignments" className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-6">
            <ArrowLeft className="w-4 h-4" /> All Assignments
          </Link>

          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{a.title}</h1>
              <p className="text-gray-500 mt-1 text-sm">
                {a.word_count.toLocaleString()} words · {a.academic_level?.replace("_", " ")} ·{" "}
                Created {formatDistanceToNow(new Date(a.created_at), { addSuffix: true })}
              </p>
            </div>
            <button
              onClick={() => { setRefreshing(true); load(); }}
              disabled={refreshing}
              className="btn-secondary flex items-center gap-2 text-sm"
            >
              <RefreshCw className={clsx("w-4 h-4", refreshing && "animate-spin")} />
              Refresh
            </button>
          </div>

          <div className="grid grid-cols-3 gap-6">

            {/* Pipeline progress */}
            <div className="col-span-2 space-y-5">

              {/* Status banner */}
              {completed && (
                <div className="bg-green-50 border border-green-200 rounded-xl p-5 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="w-6 h-6 text-green-600" />
                    <div>
                      <p className="font-semibold text-green-800">Assignment Complete!</p>
                      <p className="text-sm text-green-600">Quality score: {a.quality_score ?? "—"}/100 · Plagiarism: {a.plagiarism_score ?? "—"}</p>
                    </div>
                  </div>
                  <a href={downloadUrl(a.id)} download className="btn-primary flex items-center gap-2 text-sm">
                    <Download className="w-4 h-4" /> Download DOCX
                  </a>
                </div>
              )}

              {failed && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-5 flex items-center gap-3">
                  <AlertCircle className="w-6 h-6 text-red-500" />
                  <div>
                    <p className="font-semibold text-red-800">Pipeline Failed</p>
                    <p className="text-sm text-red-600">Please contact support or try resubmitting.</p>
                  </div>
                </div>
              )}

              {/* Pipeline log */}
              <div className="card">
                <h2 className="font-semibold text-gray-900 mb-4">Pipeline Log</h2>
                {pipelineLog.length === 0 ? (
                  <p className="text-sm text-gray-400">No log entries yet — pipeline may still be starting.</p>
                ) : (
                  <div className="space-y-2">
                    {pipelineLog.map((entry, idx) => (
                      <div key={idx} className="flex items-start gap-3 text-sm p-3 bg-gray-50 rounded-lg">
                        <span className="font-mono text-xs text-gray-400 mt-0.5 w-20 flex-shrink-0">
                          {new Date(entry.ts).toLocaleTimeString()}
                        </span>
                        <div>
                          <span className="font-medium text-gray-700">{entry.stage}</span>
                          {entry.result && (
                            <p className="text-gray-500 text-xs mt-0.5">
                              {typeof entry.result === "object"
                                ? Object.entries(entry.result)
                                    .map(([k, v]) => `${k}: ${v}`)
                                    .join(" · ")
                                : String(entry.result)}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Sidebar: Stage indicator + details */}
            <div className="space-y-5">
              <div className="card">
                <h2 className="font-semibold text-gray-900 mb-4">Progress</h2>
                <StageIndicator currentStatus={a.status} />
              </div>

              <div className="card text-sm space-y-3">
                <h2 className="font-semibold text-gray-900">Details</h2>
                {[
                  ["Review Type", a.review_type?.replace("_", " ")],
                  ["Delivery",    a.delivery_method?.replace("_", " ")],
                  ["Citation",    a.citation_style ?? "Harvard"],
                  ["Words",       a.word_count?.toLocaleString()],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-gray-500">{k}</span>
                    <span className="font-medium capitalize">{v}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
