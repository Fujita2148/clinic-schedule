"use client";

import type { Schedule } from "@/lib/types";
import { getExportCsvUrl } from "@/lib/api";

interface Props {
  schedules: Schedule[];
  currentSchedule: Schedule | null;
  onSelectSchedule: (schedule: Schedule) => void;
  onCreateSchedule: () => void;
  onRefresh: () => void;
  onUpdateStatus?: (status: string) => void;
  onSolve?: () => void;
  solving?: boolean;
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
}: Props) {
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
    </header>
  );
}
