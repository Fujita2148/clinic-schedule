"use client";

import { useState } from "react";
import type { Schedule, NlpParsedEvent } from "@/lib/types";
import { getExportCsvUrl, parseEventFromText, createEvent } from "@/lib/api";

interface Props {
  schedules: Schedule[];
  currentSchedule: Schedule | null;
  onSelectSchedule: (schedule: Schedule) => void;
  onCreateSchedule: () => void;
  onRefresh: () => void;
  onUpdateStatus?: (status: string) => void;
  onSolve?: () => void;
  solving?: boolean;
  onEventCreated?: () => void;
}

export function GridToolbar({
  schedules,
  currentSchedule,
  onSelectSchedule,
  onCreateSchedule,
  onRefresh,
  onUpdateStatus,
  onSolve,
  solving,
  onEventCreated,
}: Props) {
  const [nlpText, setNlpText] = useState("");
  const [nlpParsing, setNlpParsing] = useState(false);
  const [nlpParsed, setNlpParsed] = useState<NlpParsedEvent | null>(null);
  const [nlpError, setNlpError] = useState<string | null>(null);

  async function handleNlpSubmit() {
    if (!nlpText.trim()) return;
    setNlpParsing(true);
    setNlpError(null);
    setNlpParsed(null);
    try {
      const res = await parseEventFromText(nlpText.trim(), currentSchedule?.id);
      setNlpParsed(res.parsed);
    } catch (err) {
      setNlpError(err instanceof Error ? err.message : "パースエラー");
    } finally {
      setNlpParsing(false);
    }
  }

  async function handleNlpConfirm() {
    if (!nlpParsed) return;
    try {
      await createEvent({
        type_code: nlpParsed.type_code,
        subject_name: nlpParsed.subject_name,
        location_type: nlpParsed.location_type,
        duration_hours: nlpParsed.duration_hours,
        time_constraint_type: nlpParsed.time_constraint.type,
        time_constraint_data: nlpParsed.time_constraint.data,
        required_skills: nlpParsed.required_skills,
        preferred_skills: nlpParsed.preferred_skills,
        required_resources: nlpParsed.required_resources,
        priority: nlpParsed.priority,
        notes: nlpParsed.notes,
        natural_text: nlpText.trim(),
        schedule_id: currentSchedule?.id ?? null,
      });
      setNlpText("");
      setNlpParsed(null);
      onEventCreated?.();
    } catch (err) {
      setNlpError(err instanceof Error ? err.message : "作成エラー");
    }
  }
  const status = currentSchedule?.status;

  return (
    <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-4 flex-wrap">
      <h1 className="text-lg font-bold text-gray-800 whitespace-nowrap">
        シフト表
      </h1>

      <div className="flex items-center gap-2">
        <select
          value={currentSchedule?.id || ""}
          onChange={(e) => {
            const sched = schedules.find((s) => s.id === e.target.value);
            if (sched) onSelectSchedule(sched);
          }}
          className="border border-gray-300 rounded px-3 py-1.5 text-sm"
        >
          <option value="" disabled>
            月を選択
          </option>
          {schedules.map((s) => (
            <option key={s.id} value={s.id}>
              {s.year_month} ({s.status})
            </option>
          ))}
        </select>

        <button
          onClick={onCreateSchedule}
          className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
        >
          + 新規
        </button>
      </div>

      {currentSchedule && onUpdateStatus && (
        <div className="flex items-center gap-2">
          {status === "draft" && (
            <button
              onClick={() => onUpdateStatus("reviewing")}
              className="bg-yellow-500 text-white px-3 py-1.5 rounded text-sm hover:bg-yellow-600"
            >
              確認中へ
            </button>
          )}
          {status === "reviewing" && (
            <>
              <button
                onClick={() => onUpdateStatus("confirmed")}
                className="bg-green-600 text-white px-3 py-1.5 rounded text-sm hover:bg-green-700"
              >
                確定
              </button>
              <button
                onClick={() => onUpdateStatus("draft")}
                className="border border-gray-300 px-3 py-1.5 rounded text-sm hover:bg-gray-50"
              >
                下書きに戻す
              </button>
            </>
          )}
          {status === "confirmed" && (
            <span className="bg-green-100 text-green-800 px-3 py-1.5 rounded text-sm font-medium">
              確定済み
            </span>
          )}
        </div>
      )}

      {currentSchedule && status !== "confirmed" && onSolve && (
        <button
          onClick={onSolve}
          disabled={solving}
          className="bg-purple-600 text-white px-3 py-1.5 rounded text-sm hover:bg-purple-700 disabled:opacity-50"
        >
          {solving ? "生成中..." : "案生成"}
        </button>
      )}

      <div className="flex items-center gap-2 ml-auto">
        <button
          onClick={onRefresh}
          className="border border-gray-300 px-3 py-1.5 rounded text-sm hover:bg-gray-50"
        >
          更新
        </button>

        {currentSchedule && (
          <a
            href={getExportCsvUrl(currentSchedule.id)}
            download
            className="border border-gray-300 px-3 py-1.5 rounded text-sm hover:bg-gray-50"
          >
            CSV出力
          </a>
        )}
      </div>

      {/* Natural text input bar */}
      {currentSchedule && status !== "confirmed" && (
        <div className="w-full flex items-center gap-2 pt-2 border-t border-gray-100 mt-1">
          <span className="text-xs text-gray-500 whitespace-nowrap">自然文入力:</span>
          <input
            type="text"
            value={nlpText}
            onChange={(e) => setNlpText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleNlpSubmit(); }}
            placeholder="例: 山田さんの心理検査2回目を今月の木曜午後に"
            disabled={nlpParsing}
            className="flex-1 border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
          <button
            onClick={handleNlpSubmit}
            disabled={nlpParsing || !nlpText.trim()}
            className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm hover:bg-indigo-700 disabled:opacity-50 whitespace-nowrap"
          >
            {nlpParsing ? "解析中..." : "送信"}
          </button>
          {nlpError && (
            <span className="text-xs text-red-500">{nlpError}</span>
          )}
        </div>
      )}

      {/* NLP parse result inline */}
      {nlpParsed && (
        <div className="w-full bg-indigo-50 border border-indigo-200 rounded p-3 mt-1 text-sm">
          <div className="flex items-start gap-4">
            <div className="flex-1 text-xs text-gray-700">
              {nlpParsed.type_code && <span className="mr-2">種別: {nlpParsed.type_code}</span>}
              {nlpParsed.subject_name && <span className="mr-2">対象: {nlpParsed.subject_name}</span>}
              <span className="mr-2">{nlpParsed.duration_hours}h</span>
              {nlpParsed.required_skills.length > 0 && (
                <span className="mr-2">スキル: {nlpParsed.required_skills.join(",")}</span>
              )}
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleNlpConfirm}
                className="bg-green-600 text-white px-3 py-1 rounded text-xs hover:bg-green-700"
              >
                確定
              </button>
              <button
                onClick={() => setNlpParsed(null)}
                className="border border-gray-300 px-3 py-1 rounded text-xs hover:bg-gray-50"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
