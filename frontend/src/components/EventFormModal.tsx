"use client";

import { useState, useEffect } from "react";
import { createEvent, updateEvent, getTaskTypes } from "@/lib/api";
import type { ClinicEvent, TaskType } from "@/lib/types";

const LOCATION_TYPES = [
  { value: "in_clinic", label: "院内" },
  { value: "outing", label: "外出" },
  { value: "visit", label: "訪問" },
];

const PRIORITIES = [
  { value: "required", label: "必須" },
  { value: "high", label: "高" },
  { value: "medium", label: "中" },
  { value: "low", label: "低" },
];

const TC_TYPES = [
  { value: "fixed", label: "日時確定" },
  { value: "range", label: "範囲指定" },
  { value: "candidates", label: "候補日時" },
];

const STATUSES = [
  { value: "unassigned", label: "未割当" },
  { value: "assigned", label: "割当済" },
  { value: "hold", label: "保留" },
  { value: "done", label: "完了" },
];

interface Props {
  event: ClinicEvent | null; // null = create new
  scheduleId: string | null;
  onSave: () => void;
  onClose: () => void;
}

export function EventFormModal({ event, scheduleId, onSave, onClose }: Props) {
  const [taskTypes, setTaskTypes] = useState<TaskType[]>([]);
  const [saving, setSaving] = useState(false);

  // Form fields
  const [typeCode, setTypeCode] = useState(event?.type_code || "");
  const [subjectName, setSubjectName] = useState(event?.subject_name || "");
  const [locationType, setLocationType] = useState(event?.location_type || "in_clinic");
  const [durationHours, setDurationHours] = useState(event?.duration_hours || 1);
  const [tcType, setTcType] = useState(event?.time_constraint_type || "fixed");
  const [tcDataJson, setTcDataJson] = useState(
    event ? JSON.stringify(event.time_constraint_data, null, 2) : '{"date": "", "start": 9}'
  );
  const [requiredSkills, setRequiredSkills] = useState(event?.required_skills.join(", ") || "");
  const [requiredResources, setRequiredResources] = useState(event?.required_resources.join(", ") || "");
  const [priority, setPriority] = useState(event?.priority || "required");
  const [status, setStatus] = useState(event?.status || "unassigned");
  const [deadline, setDeadline] = useState(event?.deadline || "");
  const [notes, setNotes] = useState(event?.notes || "");

  useEffect(() => {
    getTaskTypes().then(setTaskTypes).catch(() => {});
  }, []);

  // Update tcDataJson template when tcType changes (only for new events)
  useEffect(() => {
    if (event) return;
    if (tcType === "fixed") setTcDataJson('{"date": "", "start": 9}');
    else if (tcType === "range") setTcDataJson('{"weekdays": [], "period": "pm", "month": ""}');
    else if (tcType === "candidates") setTcDataJson('{"slots": [{"date": "", "start": 13}]}');
  }, [tcType, event]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    let tcData: Record<string, unknown>;
    try {
      tcData = JSON.parse(tcDataJson);
    } catch {
      alert("時間条件データのJSON形式が不正です");
      return;
    }

    setSaving(true);
    try {
      const data: Partial<ClinicEvent> = {
        type_code: typeCode || null,
        subject_name: subjectName || null,
        location_type: locationType,
        duration_hours: durationHours,
        time_constraint_type: tcType,
        time_constraint_data: tcData,
        required_skills: requiredSkills.split(",").map((s) => s.trim()).filter(Boolean),
        required_resources: requiredResources.split(",").map((s) => s.trim()).filter(Boolean),
        priority,
        status,
        deadline: deadline || null,
        notes: notes || null,
        schedule_id: scheduleId,
      };

      if (event) {
        await updateEvent(event.id, data);
      } else {
        await createEvent(data);
      }
      onSave();
    } catch (err) {
      alert(err instanceof Error ? err.message : "保存エラー");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center" onClick={onClose}>
      <div
        className="bg-white rounded-lg shadow-xl p-5 w-[28rem] max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-gray-800">
            {event ? "イベント編集" : "イベント作成"}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          {/* Type Code */}
          <div>
            <label className="block text-sm text-gray-600 mb-1">業務種別</label>
            <select
              value={typeCode}
              onChange={(e) => setTypeCode(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
            >
              <option value="">（未指定）</option>
              {taskTypes.map((tt) => (
                <option key={tt.code} value={tt.code}>{tt.display_name} ({tt.code})</option>
              ))}
            </select>
          </div>

          {/* Subject Name */}
          <div>
            <label className="block text-sm text-gray-600 mb-1">対象 (患者名/プログラム名)</label>
            <input
              type="text"
              value={subjectName}
              onChange={(e) => setSubjectName(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
              placeholder="例: 山田"
            />
          </div>

          {/* Location Type + Duration */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm text-gray-600 mb-1">場所</label>
              <select
                value={locationType}
                onChange={(e) => setLocationType(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
              >
                {LOCATION_TYPES.map((lt) => (
                  <option key={lt.value} value={lt.value}>{lt.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">所要時間 (h)</label>
              <input
                type="number"
                min={1}
                value={durationHours}
                onChange={(e) => setDurationHours(Number(e.target.value))}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
              />
            </div>
          </div>

          {/* Time Constraint */}
          <div>
            <label className="block text-sm text-gray-600 mb-1">時間条件タイプ</label>
            <select
              value={tcType}
              onChange={(e) => setTcType(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
            >
              {TC_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">時間条件データ (JSON)</label>
            <textarea
              value={tcDataJson}
              onChange={(e) => setTcDataJson(e.target.value)}
              rows={3}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm font-mono"
            />
          </div>

          {/* Skills + Resources */}
          <div>
            <label className="block text-sm text-gray-600 mb-1">必須スキル (カンマ区切り)</label>
            <input
              type="text"
              value={requiredSkills}
              onChange={(e) => setRequiredSkills(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
              placeholder="例: CP, PSW"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">必要リソース (カンマ区切り)</label>
            <input
              type="text"
              value={requiredResources}
              onChange={(e) => setRequiredResources(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
              placeholder="例: car, room"
            />
          </div>

          {/* Priority + Status */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm text-gray-600 mb-1">優先度</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
              >
                {PRIORITIES.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">ステータス</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
              >
                {STATUSES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Deadline */}
          <div>
            <label className="block text-sm text-gray-600 mb-1">期限</label>
            <input
              type="date"
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
            />
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm text-gray-600 mb-1">備考</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
            />
          </div>

          {/* Buttons */}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="border border-gray-300 px-4 py-1.5 rounded text-sm hover:bg-gray-50"
            >
              キャンセル
            </button>
            <button
              type="submit"
              disabled={saving}
              className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? "保存中..." : "保存"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
