"use client";

import { useEffect, useState } from "react";
import { StaffFormModal } from "@/components/StaffFormModal";
import {
  getStaffs,
  createStaff,
  updateStaff,
  deleteStaff,
  replaceStaffSkills,
} from "@/lib/api";
import type { Staff } from "@/lib/types";

export default function StaffsPage() {
  const [staffs, setStaffs] = useState<Staff[]>([]);
  const [showInactive, setShowInactive] = useState(false);
  const [editing, setEditing] = useState<Staff | null | "new">(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStaffs();
  }, []);

  async function loadStaffs() {
    try {
      setLoading(true);
      const data = await getStaffs();
      setStaffs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "読み込みエラー");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(data: Partial<Staff>, skills: { skill_code: string; level: string }[]) {
    try {
      if (editing === "new") {
        const created = await createStaff(data);
        await replaceStaffSkills(created.id, skills);
      } else if (editing) {
        await updateStaff(editing.id, data);
        await replaceStaffSkills(editing.id, skills);
      }
      setEditing(null);
      await loadStaffs();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存エラー");
    }
  }

  async function handleDelete(staff: Staff) {
    if (!confirm(`${staff.name} を無効にしますか？`)) return;
    try {
      await deleteStaff(staff.id);
      await loadStaffs();
    } catch (err) {
      setError(err instanceof Error ? err.message : "削除エラー");
    }
  }

  const filtered = showInactive ? staffs : staffs.filter((s) => s.is_active);

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
        <StaffFormModal
          staff={editing === "new" ? null : editing}
          onSave={handleSave}
          onClose={() => setEditing(null)}
        />
      )}

      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold">職員管理</h2>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-sm">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
            />
            無効職員を表示
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
              <th className="text-left px-3 py-2 font-medium">名前</th>
              <th className="text-left px-3 py-2 font-medium">職種</th>
              <th className="text-left px-3 py-2 font-medium">雇用形態</th>
              <th className="text-center px-3 py-2 font-medium">運転</th>
              <th className="text-center px-3 py-2 font-medium">自転車</th>
              <th className="text-center px-3 py-2 font-medium">有効</th>
              <th className="text-right px-3 py-2 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((staff) => (
              <tr
                key={staff.id}
                className={`border-b border-gray-100 hover:bg-gray-50 ${
                  !staff.is_active ? "opacity-50" : ""
                }`}
              >
                <td className="px-3 py-2">{staff.name}</td>
                <td className="px-3 py-2">{staff.job_category}</td>
                <td className="px-3 py-2">{staff.employment_type}</td>
                <td className="px-3 py-2 text-center">{staff.can_drive ? "○" : "-"}</td>
                <td className="px-3 py-2 text-center">{staff.can_bicycle ? "○" : "-"}</td>
                <td className="px-3 py-2 text-center">{staff.is_active ? "○" : "×"}</td>
                <td className="px-3 py-2 text-right">
                  <button
                    onClick={() => setEditing(staff)}
                    className="text-blue-600 hover:underline text-xs mr-2"
                  >
                    編集
                  </button>
                  {staff.is_active && (
                    <button
                      onClick={() => handleDelete(staff)}
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
                <td colSpan={7} className="px-3 py-8 text-center text-gray-400">
                  職員が登録されていません
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
