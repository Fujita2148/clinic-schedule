"use client";

import { useEffect, useState } from "react";
import {
  getSchedules,
  getViolations,
  checkViolations,
  explainViolations,
  runMultiSolve,
  applySolution,
} from "@/lib/api";
import type { Schedule, Violation, SolutionSummary } from "@/lib/types";

export default function ReportsPage() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [violations, setViolations] = useState<Violation[]>([]);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [solutions, setSolutions] = useState<SolutionSummary[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkLoading, setCheckLoading] = useState(false);
  const [explainLoading, setExplainLoading] = useState(false);
  const [solveLoading, setSolveLoading] = useState(false);
  const [applyingPreset, setApplyingPreset] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSchedules().then((s) => {
      setSchedules(s);
      if (s.length > 0) {
        setSelectedId(s[0].id);
      }
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    if (selectedId) {
      setViolations([]);
      setExplanation(null);
      setSolutions(null);
      getViolations(selectedId).then(setViolations).catch(() => {});
    }
  }, [selectedId]);

  const hardViolations = violations.filter((v) => v.violation_type === "hard");
  const softViolations = violations.filter((v) => v.violation_type === "soft");
  const totalPenalty = softViolations.reduce((sum, v) => sum + (v.severity ?? 0), 0);

  async function handleCheck() {
    if (!selectedId) return;
    setCheckLoading(true);
    try {
      const viols = await checkViolations(selectedId);
      setViolations(viols);
      setExplanation(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "検証エラー");
    } finally {
      setCheckLoading(false);
    }
  }

  async function handleExplain() {
    if (!selectedId) return;
    setExplainLoading(true);
    try {
      const res = await explainViolations(selectedId);
      setExplanation(res.explanation);
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI説明エラー");
    } finally {
      setExplainLoading(false);
    }
  }

  async function handleMultiSolve() {
    if (!selectedId) return;
    setSolveLoading(true);
    try {
      const res = await runMultiSolve(selectedId);
      setSolutions(res.solutions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "案生成エラー");
    } finally {
      setSolveLoading(false);
    }
  }

  async function handleApply(preset: string) {
    if (!selectedId) return;
    if (!confirm(`案${preset}を適用しますか？`)) return;
    setApplyingPreset(preset);
    try {
      const res = await applySolution(selectedId, preset);
      alert(res.message);
      // Refresh violations
      const viols = await checkViolations(selectedId);
      setViolations(viols);
      setSolutions(null);
      setExplanation(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "適用エラー");
    } finally {
      setApplyingPreset(null);
    }
  }

  const selectedSchedule = schedules.find((s) => s.id === selectedId);

  if (loading) {
    return (
      <div className="flex items-center justify-center flex-1">
        <div className="text-lg text-gray-500">読み込み中...</div>
      </div>
    );
  }

  return (
    <main className="flex-1 p-4 max-w-5xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <h2 className="text-lg font-bold">違反/未充足レポート</h2>
        <select
          value={selectedId || ""}
          onChange={(e) => setSelectedId(e.target.value)}
          className="border border-gray-300 rounded px-3 py-1.5 text-sm"
        >
          {schedules.map((s) => (
            <option key={s.id} value={s.id}>
              {s.year_month} ({s.status})
            </option>
          ))}
        </select>
        <button
          onClick={handleCheck}
          disabled={checkLoading || !selectedId}
          className="border border-gray-300 px-3 py-1.5 rounded text-sm hover:bg-gray-50 disabled:opacity-50"
        >
          {checkLoading ? "検証中..." : "検証実行"}
        </button>
        <button
          onClick={handleExplain}
          disabled={explainLoading || !selectedId || violations.length === 0}
          className="bg-indigo-100 text-indigo-700 px-3 py-1.5 rounded text-sm hover:bg-indigo-200 disabled:opacity-50"
        >
          {explainLoading ? "分析中..." : "AI分析"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 mb-4 rounded">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline text-sm">閉じる</button>
        </div>
      )}

      {/* AI explanation */}
      {explanation && (
        <div className="bg-indigo-50 border border-indigo-200 rounded p-4 mb-6">
          <div className="font-medium text-indigo-700 mb-2">AI分析結果</div>
          <div className="text-sm text-gray-700 whitespace-pre-wrap">{explanation}</div>
        </div>
      )}

      {/* Violation summary */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white border border-gray-200 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-red-600">{hardViolations.length}</div>
          <div className="text-sm text-gray-500 mt-1">必須違反</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-amber-600">{softViolations.length}</div>
          <div className="text-sm text-gray-500 mt-1">推奨違反</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-gray-700">{totalPenalty.toLocaleString()}</div>
          <div className="text-sm text-gray-500 mt-1">合計ペナルティ</div>
        </div>
      </div>

      {/* Hard violations */}
      {hardViolations.length > 0 && (
        <section className="mb-6">
          <h3 className="font-medium text-red-700 mb-2">
            ハード違反: {hardViolations.length}件
          </h3>
          <div className="space-y-2">
            {hardViolations.map((v) => (
              <div key={v.id} className="bg-red-50 border border-red-200 rounded p-3">
                <div className="flex items-start gap-2">
                  <span className="text-sm mt-0.5">{"\u26D4"}</span>
                  <div className="flex-1">
                    <div className="text-sm text-gray-800">{v.description}</div>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                      {v.affected_date && <span>{v.affected_date}</span>}
                      {v.affected_time_block && <span>{v.affected_time_block}</span>}
                      {v.affected_staff.length > 0 && (
                        <span>対象: {v.affected_staff.join(", ")}</span>
                      )}
                    </div>
                    {v.suggestion && (
                      <div className="mt-1 text-xs text-blue-600">{v.suggestion}</div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Soft violations */}
      {softViolations.length > 0 && (
        <section className="mb-6">
          <h3 className="font-medium text-amber-700 mb-2">
            ソフト違反: {softViolations.length}件 (合計ペナルティ: {totalPenalty.toLocaleString()})
          </h3>
          <div className="space-y-2">
            {softViolations.map((v) => (
              <div key={v.id} className="bg-amber-50 border border-amber-200 rounded p-3">
                <div className="flex items-start gap-2">
                  <span className="text-sm mt-0.5">{"\u26A0\uFE0F"}</span>
                  <div className="flex-1">
                    <div className="text-sm text-gray-800">{v.description}</div>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                      {v.affected_date && <span>{v.affected_date}</span>}
                      {v.affected_time_block && <span>{v.affected_time_block}</span>}
                      {v.severity !== null && <span>重み: {v.severity}</span>}
                    </div>
                    {v.suggestion && (
                      <div className="mt-1 text-xs text-blue-600">{v.suggestion}</div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {violations.length === 0 && !checkLoading && (
        <div className="text-center text-gray-400 py-12">
          違反データがありません。「検証実行」を押してチェックしてください。
        </div>
      )}

      {/* Solution comparison */}
      <section className="mt-8">
        <div className="flex items-center gap-3 mb-4">
          <h3 className="font-medium text-gray-700">案の比較</h3>
          <button
            onClick={handleMultiSolve}
            disabled={solveLoading || !selectedId || selectedSchedule?.status === "confirmed"}
            className="bg-purple-600 text-white px-3 py-1.5 rounded text-sm hover:bg-purple-700 disabled:opacity-50"
          >
            {solveLoading ? "生成中..." : "A/B/C案を生成"}
          </button>
        </div>

        {solutions && solutions.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-4 py-2 font-medium"></th>
                  {solutions.map((sol) => (
                    <th key={sol.preset} className="text-center px-4 py-2 font-medium">
                      案{sol.preset} — {sol.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-2 text-gray-500">ステータス</td>
                  {solutions.map((sol) => (
                    <td key={sol.preset} className="text-center px-4 py-2">
                      <span className={
                        sol.status === "OPTIMAL" || sol.status === "FEASIBLE"
                          ? "text-green-600 font-medium"
                          : "text-red-600 font-medium"
                      }>
                        {sol.status === "OPTIMAL" ? "最適解" :
                         sol.status === "FEASIBLE" ? "実行可能解" :
                         sol.status === "INFEASIBLE" ? "解なし" : sol.status}
                      </span>
                    </td>
                  ))}
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-2 text-gray-500">割当数</td>
                  {solutions.map((sol) => (
                    <td key={sol.preset} className="text-center px-4 py-2">{sol.num_assignments}</td>
                  ))}
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-2 text-gray-500">イベント配置</td>
                  {solutions.map((sol) => (
                    <td key={sol.preset} className="text-center px-4 py-2">{sol.num_events_placed}</td>
                  ))}
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-2 text-gray-500">目的関数値</td>
                  {solutions.map((sol) => (
                    <td key={sol.preset} className="text-center px-4 py-2 font-mono text-xs">
                      {sol.objective_value?.toFixed(1) ?? "-"}
                    </td>
                  ))}
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-2 text-gray-500">計算時間</td>
                  {solutions.map((sol) => (
                    <td key={sol.preset} className="text-center px-4 py-2">
                      {sol.stats.wall_time?.toFixed(1) ?? "-"}秒
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="px-4 py-2"></td>
                  {solutions.map((sol) => {
                    const isFeasible = sol.status === "OPTIMAL" || sol.status === "FEASIBLE";
                    return (
                      <td key={sol.preset} className="text-center px-4 py-2">
                        <button
                          onClick={() => handleApply(sol.preset)}
                          disabled={!isFeasible || applyingPreset !== null}
                          className="bg-purple-600 text-white px-4 py-1.5 rounded text-sm hover:bg-purple-700 disabled:opacity-50"
                        >
                          {applyingPreset === sol.preset ? "適用中..." : `案${sol.preset}を採用`}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
