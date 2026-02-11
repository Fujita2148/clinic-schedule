"use client";

import { useEffect, useState } from "react";
import { RuleFormModal } from "@/components/RuleFormModal";
import { getRules, toggleRule, deleteRule } from "@/lib/api";
import type { Rule } from "@/lib/types";

const TEMPLATE_LABELS: Record<string, string> = {
  headcount: "人員配置",
  availability: "勤務制限",
  skill_req: "スキル要件",
  resource_req: "リソース要件",
  preference: "優先配置",
  recurring: "定期予定",
  specific_date: "特定日",
};

export default function RulesPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [showInactive, setShowInactive] = useState(false);
  const [editing, setEditing] = useState<Rule | null | "new">(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadRules();
  }, []);

  async function loadRules() {
    try {
      setLoading(true);
      const data = await getRules();
      setRules(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "読み込みエラー");
    } finally {
      setLoading(false);
    }
  }

  async function handleToggle(rule: Rule) {
    try {
      await toggleRule(rule.id);
      await loadRules();
    } catch (err) {
      setError(err instanceof Error ? err.message : "切替エラー");
    }
  }

  async function handleDelete(rule: Rule) {
    if (!confirm(`「${rule.natural_text}」を削除しますか？`)) return;
    try {
      await deleteRule(rule.id);
      await loadRules();
    } catch (err) {
      setError(err instanceof Error ? err.message : "削除エラー");
    }
  }

  async function handleSave() {
    setEditing(null);
    await loadRules();
  }

  const filtered = showInactive ? rules : rules.filter((r) => r.is_active);

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
        <RuleFormModal
          rule={editing === "new" ? null : editing}
          onSave={handleSave}
          onClose={() => setEditing(null)}
        />
      )}

      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold">ルール管理</h2>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-sm">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
            />
            無効ルールを表示
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
          <button onClick={() => setError(null)} className="ml-2 underline text-sm">
            閉じる
          </button>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-center px-3 py-2 font-medium w-12">ON</th>
              <th className="text-left px-3 py-2 font-medium">自然文</th>
              <th className="text-left px-3 py-2 font-medium">種別</th>
              <th className="text-left px-3 py-2 font-medium">制約</th>
              <th className="text-left px-3 py-2 font-medium">タグ</th>
              <th className="text-right px-3 py-2 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((rule) => (
              <tr
                key={rule.id}
                className={`border-b border-gray-100 hover:bg-gray-50 ${
                  !rule.is_active ? "opacity-50" : ""
                }`}
              >
                <td className="px-3 py-2 text-center">
                  <button
                    onClick={() => handleToggle(rule)}
                    className={`w-8 h-5 rounded-full relative transition-colors ${
                      rule.is_active ? "bg-blue-500" : "bg-gray-300"
                    }`}
                    title={rule.is_active ? "ON → OFF" : "OFF → ON"}
                  >
                    <span
                      className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                        rule.is_active ? "left-3.5" : "left-0.5"
                      }`}
                    />
                  </button>
                </td>
                <td className="px-3 py-2">{rule.natural_text}</td>
                <td className="px-3 py-2 text-xs">
                  {TEMPLATE_LABELS[rule.template_type] || rule.template_type}
                </td>
                <td className="px-3 py-2">
                  {rule.hard_or_soft === "hard" ? (
                    <span className="inline-block bg-red-100 text-red-700 text-xs px-2 py-0.5 rounded">
                      必須
                    </span>
                  ) : (
                    <span className="inline-block bg-amber-100 text-amber-700 text-xs px-2 py-0.5 rounded">
                      推奨 (重み:{rule.weight})
                    </span>
                  )}
                </td>
                <td className="px-3 py-2 text-xs">
                  {rule.tags.length > 0
                    ? rule.tags.map((t) => (
                        <span
                          key={t}
                          className="inline-block bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded mr-1"
                        >
                          {t}
                        </span>
                      ))
                    : "-"}
                </td>
                <td className="px-3 py-2 text-right">
                  <button
                    onClick={() => setEditing(rule)}
                    className="text-blue-600 hover:underline text-xs mr-2"
                  >
                    編集
                  </button>
                  <button
                    onClick={() => handleDelete(rule)}
                    className="text-red-600 hover:underline text-xs"
                  >
                    削除
                  </button>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-gray-400">
                  ルールが登録されていません
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
