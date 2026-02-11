"use client";

import { useState } from "react";
import type { Violation } from "@/lib/types";
import { explainViolations } from "@/lib/api";

interface Props {
  violations: Violation[];
  onCheck: () => void;
  loading: boolean;
  scheduleId: string | null;
}

export function ViolationsPanel({ violations, onCheck, loading, scheduleId }: Props) {
  const [expanded, setExpanded] = useState(true);
  const [explaining, setExplaining] = useState(false);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [explainError, setExplainError] = useState<string | null>(null);

  const hardCount = violations.filter((v) => v.violation_type === "hard").length;
  const softCount = violations.filter((v) => v.violation_type === "soft").length;

  async function handleExplain() {
    if (!scheduleId || violations.length === 0) return;
    setExplaining(true);
    setExplainError(null);
    setExplanation(null);
    try {
      const res = await explainViolations(scheduleId);
      setExplanation(res.explanation);
    } catch (err) {
      setExplainError(err instanceof Error ? err.message : "AI説明の取得に失敗しました");
    } finally {
      setExplaining(false);
    }
  }

  return (
    <div className="border-t border-gray-200 bg-white">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-2">
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-sm text-gray-500 hover:text-gray-700"
          title={expanded ? "折りたたむ" : "展開"}
        >
          {expanded ? "\u25BC" : "\u25B6"}
        </button>

        <span className="text-sm font-medium">
          違反チェック
        </span>

        {violations.length > 0 && (
          <span className="flex items-center gap-2 text-xs">
            {hardCount > 0 && (
              <span className="bg-red-100 text-red-700 px-2 py-0.5 rounded">
                必須違反 {hardCount}件
              </span>
            )}
            {softCount > 0 && (
              <span className="bg-amber-100 text-amber-700 px-2 py-0.5 rounded">
                推奨違反 {softCount}件
              </span>
            )}
          </span>
        )}
        {violations.length === 0 && !loading && (
          <span className="text-xs text-green-600">違反なし</span>
        )}

        <div className="ml-auto flex items-center gap-2">
          {violations.length > 0 && scheduleId && (
            <button
              onClick={handleExplain}
              disabled={explaining}
              className="bg-indigo-100 text-indigo-700 px-3 py-1 rounded text-xs hover:bg-indigo-200 disabled:opacity-50"
            >
              {explaining ? "分析中..." : "AI説明"}
            </button>
          )}
          <button
            onClick={onCheck}
            disabled={loading}
            className="border border-gray-300 px-3 py-1 rounded text-xs hover:bg-gray-50 disabled:opacity-50"
          >
            {loading ? "検証中..." : "検証実行"}
          </button>
        </div>
      </div>

      {/* AI Explanation */}
      {expanded && (explanation || explainError) && (
        <div className="px-4 pb-3">
          {explainError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-xs mb-2">
              {explainError}
            </div>
          )}
          {explanation && (
            <div className="bg-indigo-50 border border-indigo-200 px-3 py-2 rounded text-xs text-gray-700 mb-2 whitespace-pre-wrap">
              <div className="font-medium text-indigo-700 mb-1">AI分析:</div>
              {explanation}
            </div>
          )}
        </div>
      )}

      {/* Violation list */}
      {expanded && violations.length > 0 && (
        <div className="px-4 pb-3 max-h-48 overflow-y-auto">
          <div className="space-y-1.5">
            {violations.map((v) => (
              <div
                key={v.id}
                className={`flex items-start gap-2 px-3 py-2 rounded text-xs ${
                  v.violation_type === "hard"
                    ? "bg-red-50 border border-red-200"
                    : "bg-amber-50 border border-amber-200"
                }`}
              >
                <span className="flex-shrink-0 mt-0.5">
                  {v.violation_type === "hard" ? "\u26D4" : "\u26A0\uFE0F"}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-gray-800">{v.description}</div>
                  <div className="flex items-center gap-3 mt-0.5 text-gray-500">
                    {v.affected_date && <span>{v.affected_date}</span>}
                    {v.affected_time_block && <span>{v.affected_time_block}</span>}
                    {v.severity !== null && <span>重み: {v.severity}</span>}
                  </div>
                  {v.suggestion && (
                    <div className="mt-1 text-blue-600">{v.suggestion}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
