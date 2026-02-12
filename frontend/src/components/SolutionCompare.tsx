"use client";

import { useState } from "react";
import type { SolutionSummary } from "@/lib/types";
import { applySolution } from "@/lib/api";

interface Props {
  scheduleId: string;
  solutions: SolutionSummary[];
  onApplied: () => void;
  onClose: () => void;
}

const PRESET_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  A: { bg: "bg-blue-50", border: "border-blue-300", text: "text-blue-700" },
  B: { bg: "bg-green-50", border: "border-green-300", text: "text-green-700" },
  C: { bg: "bg-purple-50", border: "border-purple-300", text: "text-purple-700" },
};

export function SolutionCompare({ scheduleId, solutions, onApplied, onClose }: Props) {
  const [applying, setApplying] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleApply(preset: string) {
    if (!confirm(`案${preset}を適用しますか？現在の未ロック割当は上書きされます。`)) return;
    setApplying(preset);
    setError(null);
    try {
      const res = await applySolution(scheduleId, preset);
      alert(res.message);
      onApplied();
    } catch (err) {
      setError(err instanceof Error ? err.message : "適用エラー");
    } finally {
      setApplying(null);
    }
  }

  const bestObjective = Math.min(
    ...solutions
      .filter((s) => s.objective_value !== null && s.status !== "INFEASIBLE")
      .map((s) => s.objective_value!)
  );

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-bold">案比較 (A/B/C)</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">
            &times;
          </button>
        </div>

        {error && (
          <div className="mx-6 mt-4 bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">
            {error}
          </div>
        )}

        <div className="p-6 grid grid-cols-3 gap-4">
          {solutions.map((sol) => {
            const colors = PRESET_COLORS[sol.preset] || PRESET_COLORS.A;
            const isBest = sol.objective_value === bestObjective && sol.status !== "INFEASIBLE";
            const isFeasible = sol.status === "OPTIMAL" || sol.status === "FEASIBLE";

            return (
              <div
                key={sol.preset}
                className={`rounded-lg border-2 p-4 ${colors.bg} ${colors.border} ${
                  !isFeasible ? "opacity-60" : ""
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <span className={`text-lg font-bold ${colors.text}`}>
                    案{sol.preset}
                  </span>
                  {isBest && (
                    <span className="bg-yellow-100 text-yellow-700 text-xs px-2 py-0.5 rounded font-medium">
                      推奨
                    </span>
                  )}
                </div>

                <div className="text-sm font-medium text-gray-700 mb-3">
                  {sol.label}
                </div>

                <dl className="space-y-1.5 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-gray-500">ステータス</dt>
                    <dd className={isFeasible ? "text-green-600 font-medium" : "text-red-600 font-medium"}>
                      {sol.status === "OPTIMAL" ? "最適解" :
                       sol.status === "FEASIBLE" ? "実行可能解" :
                       sol.status === "INFEASIBLE" ? "解なし" : sol.status}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">割当数</dt>
                    <dd>{sol.num_assignments}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">イベント配置数</dt>
                    <dd>{sol.num_events_placed}</dd>
                  </div>
                  {sol.objective_value !== null && (
                    <div className="flex justify-between">
                      <dt className="text-gray-500">目的関数値</dt>
                      <dd className="font-mono text-xs">{sol.objective_value.toFixed(1)}</dd>
                    </div>
                  )}
                  {sol.stats.wall_time !== null && (
                    <div className="flex justify-between">
                      <dt className="text-gray-500">計算時間</dt>
                      <dd>{sol.stats.wall_time.toFixed(1)}秒</dd>
                    </div>
                  )}
                </dl>

                <button
                  onClick={() => handleApply(sol.preset)}
                  disabled={!isFeasible || applying !== null}
                  className={`mt-4 w-full py-2 rounded text-sm font-medium transition-colors disabled:opacity-50 ${
                    isFeasible
                      ? `${colors.text} border ${colors.border} hover:bg-white`
                      : "bg-gray-100 text-gray-400"
                  }`}
                >
                  {applying === sol.preset ? "適用中..." : "この案を適用"}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
