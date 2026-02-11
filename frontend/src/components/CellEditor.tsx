"use client";

import { useState } from "react";
import type { TaskType, ColorLegendItem } from "@/lib/types";

interface EditingCell {
  scheduleId: string;
  staffId: string;
  date: string;
  timeBlock: string;
  currentTaskCode: string | null;
  currentDisplayText: string | null;
  currentStatusColor: string | null;
}

interface Props {
  editing: EditingCell;
  taskTypes: TaskType[];
  colorLegend: ColorLegendItem[];
  onSave: (
    taskCode: string | null,
    displayText: string | null,
    statusColor: string | null
  ) => void;
  onClose: () => void;
}

export function CellEditor({
  editing,
  taskTypes,
  colorLegend,
  onSave,
  onClose,
}: Props) {
  const [taskCode, setTaskCode] = useState(editing.currentTaskCode || "");
  const [displayText, setDisplayText] = useState(
    editing.currentDisplayText || ""
  );
  const [statusColor, setStatusColor] = useState(
    editing.currentStatusColor || ""
  );

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSave(
      taskCode || null,
      displayText || null,
      statusColor || null
    );
  }

  return (
    <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-xl p-4 w-80">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-sm">
            セル編集: {editing.date} {editing.timeBlock}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-lg"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              業務コード
            </label>
            <select
              value={taskCode}
              onChange={(e) => setTaskCode(e.target.value)}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
            >
              <option value="">なし</option>
              {taskTypes
                .filter((t) => t.is_active)
                .map((t) => (
                  <option key={t.code} value={t.code}>
                    {t.display_name} ({t.code})
                  </option>
                ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              表示テキスト
            </label>
            <textarea
              value={displayText}
              onChange={(e) => setDisplayText(e.target.value)}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
              rows={2}
              placeholder="患者名、メモなど"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              状態色
            </label>
            <div className="flex gap-2 flex-wrap">
              <button
                type="button"
                onClick={() => setStatusColor("")}
                className={`px-2 py-1 rounded text-xs border ${
                  statusColor === ""
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-300"
                }`}
              >
                なし
              </button>
              {colorLegend.map((c) => (
                <button
                  key={c.code}
                  type="button"
                  onClick={() => setStatusColor(c.code)}
                  className={`px-2 py-1 rounded text-xs border flex items-center gap-1 ${
                    statusColor === c.code
                      ? "border-blue-500 ring-2 ring-blue-300"
                      : "border-gray-300"
                  }`}
                >
                  <span
                    className="w-3 h-3 rounded-sm inline-block"
                    style={{ backgroundColor: c.bg_color }}
                  />
                  {c.display_name}
                </button>
              ))}
            </div>
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="submit"
              className="flex-1 bg-blue-600 text-white py-1.5 rounded text-sm hover:bg-blue-700"
            >
              保存
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-gray-300 py-1.5 rounded text-sm hover:bg-gray-50"
            >
              キャンセル
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
