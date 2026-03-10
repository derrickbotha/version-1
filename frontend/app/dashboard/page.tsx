"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import { getMe, listAssignments, getResearchStats, type Assignment, type User } from "@/lib/api";
import { BookOpen, CheckCircle, Clock, Zap, BarChart3, Plus } from "lucide-react";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";

const STATUS_COLORS: Record<string, string> = {
  pending:      "bg-gray-100 text-gray-600",
  researching:  "bg-blue-100 text-blue-700",
  writing:      "bg-purple-100 text-purple-700",
  qa_check:     "bg-yellow-100 text-yellow-700",
  prof_review:  "bg-orange-100 text-orange-700",
  completed:    "bg-green-100 text-green-700",
  failed:       "bg-red-100 text-red-700",
};

export default function Dashboard() {
  const [user, setUser]           = useState<User | null>(null);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [stats, setStats]         = useState<any>(null);
  const [loading, setLoading]     = useState(true);

  useEffect(() => {
    Promise.all([getMe(), listAssignments(), getResearchStats()])
      .then(([u, a, s]) => { setUser(u); setAssignments(a); setStats(s); })
      .catch(() => { window.location.href = "/auth/login"; })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="flex h-screen items-center justify-center">
      <div className="animate-spin w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full" />
    </div>
  );

  const completed  = assignments.filter(a => a.status === "completed").length;
  const inProgress = assignments.filter(a => !["completed","failed"].includes(a.status)).length;

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-surface">
        <div className="max-w-5xl mx-auto px-6 py-8">

          {/* Header */}
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900">
              Welcome back, {user?.full_name?.split(" ")[0]} 👋
            </h1>
            <p className="text-gray-500 mt-1">
              {user?.academic_level?.replace("_", " ")} · {user?.institution ?? "Independent"}
            </p>
          </div>

          {/* Stats cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {[
              { label: "Total Assignments", value: assignments.length, icon: BookOpen, color: "text-blue-600 bg-blue-50" },
              { label: "Completed",         value: completed,          icon: CheckCircle, color: "text-green-600 bg-green-50" },
              { label: "In Progress",       value: inProgress,         icon: Clock, color: "text-orange-600 bg-orange-50" },
              { label: "Papers Indexed",    value: stats?.total_sources ?? 0, icon: BarChart3, color: "text-purple-600 bg-purple-50" },
            ].map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="card">
                <div className={`w-10 h-10 rounded-lg ${color} flex items-center justify-center mb-3`}>
                  <Icon className="w-5 h-5" />
                </div>
                <p className="text-2xl font-bold text-gray-900">{value}</p>
                <p className="text-sm text-gray-500 mt-0.5">{label}</p>
              </div>
            ))}
          </div>

          {/* Knowledge Graph Stats */}
          {stats && (
            <div className="card mb-8 bg-gradient-to-br from-brand-50 to-white border-brand-100">
              <div className="flex items-center gap-2 mb-4">
                <Zap className="w-5 h-5 text-brand-600" />
                <h2 className="font-semibold text-gray-900">Research Intelligence Graph</h2>
              </div>
              <div className="grid grid-cols-3 gap-6 text-center">
                <div>
                  <p className="text-3xl font-bold text-brand-700">{stats.total_nodes}</p>
                  <p className="text-xs text-gray-500 mt-1">Knowledge Nodes</p>
                </div>
                <div>
                  <p className="text-3xl font-bold text-brand-700">{stats.total_edges}</p>
                  <p className="text-xs text-gray-500 mt-1">Relationships</p>
                </div>
                <div>
                  <p className="text-3xl font-bold text-brand-700">{stats.total_sources}</p>
                  <p className="text-xs text-gray-500 mt-1">Indexed Papers</p>
                </div>
              </div>
            </div>
          )}

          {/* Recent Assignments */}
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900">Recent Assignments</h2>
            <Link href="/assignments/new" className="btn-primary text-sm flex items-center gap-2">
              <Plus className="w-4 h-4" /> New Assignment
            </Link>
          </div>

          {assignments.length === 0 ? (
            <div className="card text-center py-12">
              <BookOpen className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">No assignments yet.</p>
              <Link href="/assignments/new" className="btn-primary inline-flex mt-4 text-sm">
                Start your first assignment
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {assignments.slice(0, 8).map((a) => (
                <Link key={a.id} href={`/assignments/${a.id}`}
                  className="card flex items-center justify-between hover:border-brand-200 hover:shadow-md transition-all cursor-pointer">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{a.title}</p>
                    <p className="text-sm text-gray-500 mt-0.5">
                      {a.word_count.toLocaleString()} words · {a.citation_style ?? "Harvard"} ·{" "}
                      {formatDistanceToNow(new Date(a.created_at), { addSuffix: true })}
                    </p>
                  </div>
                  <div className="ml-4 flex items-center gap-3">
                    {a.quality_score && (
                      <span className="text-sm font-medium text-green-600">{a.quality_score}/100</span>
                    )}
                    <span className={`badge ${STATUS_COLORS[a.status] ?? "bg-gray-100 text-gray-600"}`}>
                      {a.status.replace("_", " ")}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
