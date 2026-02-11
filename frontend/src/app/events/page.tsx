"use client";

import { useEffect, useState } from "react";
import { EventFormModal } from "@/components/EventFormModal";
import { NaturalTextInput } from "@/components/NaturalTextInput";
import { getEvents, getTaskTypes, getSchedules, deleteEvent } from "@/lib/api";
import type { ClinicEvent, TaskType, Schedule } from "@/lib/types";

const STATUS_ICONS: Record<string, { icon: string; color: string; label: string }> = {
  assigned: { icon: "\u25a0", color: "text-green-600", label: "割当済" },
  unassigned: { icon: "\u25a1", color: "text-gray-500", label: "未割当" },
  hold: { icon: "\u25c6", color: "text-yellow-600", label: "保留" },
  done: { icon: "\u25cf", color: "text-blue-600", label: "完了" },
};

const PRIORITY_BADGES: Record<string, { bg: string; text: string; label: string }> = {
  required: { bg: "bg-red-100", text: "text-red-700", label: "必須" },
  high: { bg: "bg-orange-100", text: "text-orange-700", label: "高" },
  medium: { bg: "bg-yellow-100", text: "text-yellow-700", label: "中" },
  low: { bg: "bg-gray-100", text: "text-gray-600", label: "低" },
};

function formatTimeConstraint(event: ClinicEvent): string {
  const { time_constraint_type: type, time_constraint_data: data } = event;
  if (type === "fixed") {
    return `${data.date ?? ""} ${data.start ?? ""}時`;
  }
  if (type === "range") {
    const weekdays = ["月", "火", "水", "木", "金", "土", "日"];
    const days = (data.weekdays as number[] | undefined)?.map((d) => weekdays[d]).join("・") ?? "";
    const period = data.period === "am" ? "午前" : data.period === "pm" ? "午後" : "";
    return [data.month, days, period].filter(Boolean).join(" ");
  }
  if (type === "candidates") {
    const slots = data.slots as Array<{ date?: string; start?: number }> | undefined;
    if (slots?.length) {
      return slots.slice(0, 2).map((s) => `${s.date ?? ""} ${s.start ?? ""}時`).join(", ");
    }
  }
  return "";
}

export default function EventsPage() {
  const [events, setEvents] = useState<ClinicEvent[]>([]);
  const [taskTypes, setTaskTypes] = useState<TaskType[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<ClinicEvent | null | "new">(null);
  const [showNlp, setShowNlp] = useState(false);

  // Filters
  const [filterStatus, setFilterStatus] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterSchedule, setFilterSchedule] = useState("");

  useEffect(() => {
    Promise.all([getTaskTypes(), getSchedules()]).then(([tt, sch]) => {
      setTaskTypes(tt);
      setSchedules(sch);
    });
    loadEvents();
  }, []);

  async function loadEvents() {
    try {
      setLoading(true);
      const params: Record<string, string> = {};
      if (filterStatus) params.status = filterStatus;
      if (filterType) params.type_code = filterType;
      if (filterSchedule) params.schedule_id = filterSchedule;
      const data = await getEvents(params);
      setEvents(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "読み込みエラー");
    } finally {
      setLoading(false);
    }
  }

  // Reload when filters change
  useEffect(() => {
    loadEvents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterStatus, filterType, filterSchedule]);

  async function handleDelete(event: ClinicEvent) {
    const label = event.subject_name || event.type_code || "このイベント";
    if (!confirm(`「${label}」を削除しますか？`)) return;
    try {
      await deleteEvent(event.id);
      await loadEvents();
    } catch (err) {
      setError(err instanceof Error ? err.message : "削除エラー");
    }
  }

  async function handleSave() {
    setEditing(null);
    await loadEvents();
  }

  function handleNlpCreated() {
    setShowNlp(false);
    loadEvents();
  }

  const ttMap = Object.fromEntries(taskTypes.map((tt) => [tt.code, tt.display_name]));

  if (loading && events.length === 0) {
    return (
      <div className="flex items-center justify-center flex-1">
        <div className="text-lg text-gray-500">読み込み中...</div>
      </div>
    );
  }

  return (
    <main className="flex-1 p-4">
      {/* Modals */}
      {editing !== null && (
        <EventFormModal
          event={editing === "new" ? null : editing}
          scheduleId={filterSchedule || (schedules[0]?.id ?? null)}
          onSave={handleSave}
          onClose={() => setEditing(null)}
        />
      )}
      {showNlp && (
        <NaturalTextInput
          scheduleId={filterSchedule || (schedules[0]?.id ?? null)}
          onEventCreated={handleNlpCreated}
          onClose={() => setShowNlp(false)}
        />
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold">イベント一覧</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setEditing("new")}
            className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
          >
            + フォーム入力
          </button>
          <button
            onClick={() => setShowNlp(true)}
            className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm hover:bg-indigo-700"
          >
            自然文入力
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4 text-sm">
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1.5"
        >
          <option value="">ステータス: 全て</option>
          <option value="unassigned">未割当</option>
          <option value="assigned">割当済</option>
          <option value="hold">保留</option>
          <option value="done">完了</option>
        </select>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1.5"
        >
          <option value="">種別: 全て</option>
          {taskTypes.map((tt) => (
            <option key={tt.code} value={tt.code}>{tt.display_name}</option>
          ))}
        </select>
        <select
          value={filterSchedule}
          onChange={(e) => setFilterSchedule(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1.5"
        >
          <option value="">スケジュール: 全て</option>
          {schedules.map((s) => (
            <option key={s.id} value={s.id}>{s.year_month}</option>
          ))}
        </select>
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm mb-4">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">閉じる</button>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm border border-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left border-b">状態</th>
              <th className="px-3 py-2 text-left border-b">種別</th>
              <th className="px-3 py-2 text-left border-b">対象</th>
              <th className="px-3 py-2 text-left border-b">時間</th>
              <th className="px-3 py-2 text-left border-b">優先度</th>
              <th className="px-3 py-2 text-left border-b">メモ</th>
              <th className="px-3 py-2 text-left border-b">操作</th>
            </tr>
          </thead>
          <tbody>
            {events.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-gray-400">
                  イベントがありません
                </td>
              </tr>
            ) : (
              events.map((ev) => {
                const si = STATUS_ICONS[ev.status] ?? STATUS_ICONS.unassigned;
                const pb = PRIORITY_BADGES[ev.priority] ?? PRIORITY_BADGES.medium;
                return (
                  <tr
                    key={ev.id}
                    className="border-b hover:bg-gray-50 cursor-pointer"
                    onClick={() => setEditing(ev)}
                  >
                    <td className="px-3 py-2">
                      <span className={si.color} title={si.label}>{si.icon}</span>
                      <span className="ml-1 text-xs text-gray-500">{si.label}</span>
                    </td>
                    <td className="px-3 py-2">
                      {ttMap[ev.type_code ?? ""] ?? ev.type_code ?? "—"}
                    </td>
                    <td className="px-3 py-2">{ev.subject_name ?? "—"}</td>
                    <td className="px-3 py-2 text-xs">{formatTimeConstraint(ev)}</td>
                    <td className="px-3 py-2">
                      <span className={`px-2 py-0.5 rounded text-xs ${pb.bg} ${pb.text}`}>
                        {pb.label}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-500 truncate max-w-[200px]">
                      {ev.notes ?? ""}
                    </td>
                    <td className="px-3 py-2">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDelete(ev); }}
                        className="text-red-500 hover:text-red-700 text-xs"
                      >
                        削除
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
