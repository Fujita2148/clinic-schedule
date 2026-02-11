"use client";

import { useEffect, useState } from "react";
import { TaskTypeFormModal } from "@/components/TaskTypeFormModal";
import {
  getTaskTypes,
  createTaskType,
  updateTaskType,
  deleteTaskType,
} from "@/lib/api";
import type { TaskType } from "@/lib/types";

export default function TaskTypesPage() {
  const [taskTypes, setTaskTypes] = useState<TaskType[]>([]);
  const [showInactive, setShowInactive] = useState(false);
  const [editing, setEditing] = useState<TaskType | null | "new">(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadTaskTypes();
  }, []);

  async function loadTaskTypes() {
    try {
      setLoading(true);
      const data = await getTaskTypes();
      setTaskTypes(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "読み込みエラー");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(data: Partial<TaskType>) {
    try {
      if (editing === "new") {
        await createTaskType(data);
      } else if (editing) {
        await updateTaskType(editing.code, data);
      }
      setEditing(null);
      await loadTaskTypes();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存エラー");
    }
  }

  async function handleDelete(tt: TaskType) {
    if (!confirm(`${tt.display_name} (${tt.code}) を無効にしますか？`)) return;
    try {
      await deleteTaskType(tt.code);
      await loadTaskTypes();
    } catch (err) {
      setError(err instanceof Error ? err.message : "削除エラー");
    }
  }

  const filtered = showInactive ? taskTypes : taskTypes.filter((t) => t.is_active);

  const locationLabel: Record<string, string> = {
    in_clinic: "院内",
    visit: "訪問",
    remote: "リモート",
    any: "不問",
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center flex-1">
        <div className="text-lg text-gray-500">読み込み中...</div>
      </div>
    );
  }

  return (
    <main className="flex-1 p-4">
      {editing !== null && (
        <TaskTypeFormModal
          taskType={editing === "new" ? null : editing}
          onSave={handleSave}
          onClose={() => setEditing(null)}
        />
      )}

      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold">業務コード管理</h2>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-sm">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
            />
            無効項目を表示
          </label>
          <button
            onClick={() => setEditing("new")}
            className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
          >
            + 新規作成
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 mb-4 rounded">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline text-sm">閉じる</button>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-3 py-2 font-medium">コード</th>
              <th className="text-left px-3 py-2 font-medium">表示名</th>
              <th className="text-left px-3 py-2 font-medium">既定ブロック</th>
              <th className="text-left px-3 py-2 font-medium">必要スキル</th>
              <th className="text-left px-3 py-2 font-medium">タグ</th>
              <th className="text-left px-3 py-2 font-medium">場所</th>
              <th className="text-center px-3 py-2 font-medium">有効</th>
              <th className="text-right px-3 py-2 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((tt) => (
              <tr
                key={tt.code}
                className={`border-b border-gray-100 hover:bg-gray-50 ${
                  !tt.is_active ? "opacity-50" : ""
                }`}
              >
                <td className="px-3 py-2 font-mono text-xs">{tt.code}</td>
                <td className="px-3 py-2">{tt.display_name}</td>
                <td className="px-3 py-2 text-xs">{tt.default_blocks.join(", ")}</td>
                <td className="px-3 py-2 text-xs">{tt.required_skills.join(", ") || "-"}</td>
                <td className="px-3 py-2 text-xs">{tt.tags.join(", ") || "-"}</td>
                <td className="px-3 py-2 text-xs">{locationLabel[tt.location_type] || tt.location_type}</td>
                <td className="px-3 py-2 text-center">{tt.is_active ? "○" : "×"}</td>
                <td className="px-3 py-2 text-right">
                  <button
                    onClick={() => setEditing(tt)}
                    className="text-blue-600 hover:underline text-xs mr-2"
                  >
                    編集
                  </button>
                  {tt.is_active && (
                    <button
                      onClick={() => handleDelete(tt)}
                      className="text-red-600 hover:underline text-xs"
                    >
                      無効化
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={8} className="px-3 py-8 text-center text-gray-400">
                  業務コードが登録されていません
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
