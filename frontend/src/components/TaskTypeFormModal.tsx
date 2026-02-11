"use client";

import { useState } from "react";
import type { TaskType } from "@/lib/types";

interface Props {
  taskType: TaskType | null; // null = create mode
  onSave: (data: Partial<TaskType>) => void;
  onClose: () => void;
}

const TIME_BLOCKS = [
  { code: "am", label: "午前" },
  { code: "lunch", label: "昼" },
  { code: "pm", label: "午後" },
  { code: "15", label: "15時" },
  { code: "16", label: "16時" },
  { code: "17", label: "17時" },
  { code: "18plus", label: "18時〜" },
];

const LOCATION_TYPES = [
  { value: "in_clinic", label: "院内" },
  { value: "visit", label: "訪問" },
  { value: "remote", label: "リモート" },
  { value: "any", label: "不問" },
];

export function TaskTypeFormModal({ taskType, onSave, onClose }: Props) {
  const [code, setCode] = useState(taskType?.code || "");
  const [displayName, setDisplayName] = useState(taskType?.display_name || "");
  const [defaultBlocks, setDefaultBlocks] = useState<Set<string>>(
    new Set(taskType?.default_blocks || ["am"])
  );
  const [requiredSkills, setRequiredSkills] = useState(
    taskType?.required_skills?.join(", ") || ""
  );
  const [tags, setTags] = useState(taskType?.tags?.join(", ") || "");
  const [locationType, setLocationType] = useState(taskType?.location_type || "in_clinic");

  function toggleBlock(blockCode: string) {
    setDefaultBlocks((prev) => {
      const next = new Set(prev);
      if (next.has(blockCode)) next.delete(blockCode);
      else next.add(blockCode);
      return next;
    });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!code.trim() || !displayName.trim()) return;
    onSave({
      code: code.trim(),
      display_name: displayName.trim(),
      default_blocks: Array.from(defaultBlocks),
      required_skills: requiredSkills
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      tags: tags
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      location_type: locationType,
    });
  }

  return (
    <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-xl p-5 w-96 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-base">
            {taskType ? "業務コード編集" : "業務コード新規作成"}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg">
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">コード</label>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              disabled={!!taskType}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm disabled:bg-gray-100"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">表示名</label>
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">既定ブロック</label>
            <div className="flex gap-2 flex-wrap">
              {TIME_BLOCKS.map((tb) => (
                <label key={tb.code} className="flex items-center gap-1 text-xs">
                  <input
                    type="checkbox"
                    checked={defaultBlocks.has(tb.code)}
                    onChange={() => toggleBlock(tb.code)}
                  />
                  {tb.label}
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              必要スキル (カンマ区切り)
            </label>
            <input
              value={requiredSkills}
              onChange={(e) => setRequiredSkills(e.target.value)}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
              placeholder="nursing, driving"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              タグ (カンマ区切り)
            </label>
            <input
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
              placeholder="外来, 訪問"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">場所</label>
            <select
              value={locationType}
              onChange={(e) => setLocationType(e.target.value)}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
            >
              {LOCATION_TYPES.map((lt) => (
                <option key={lt.value} value={lt.value}>
                  {lt.label}
                </option>
              ))}
            </select>
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
