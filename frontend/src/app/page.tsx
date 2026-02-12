"use client";

import { useEffect, useState } from "react";
import { ShiftGrid } from "@/components/ShiftGrid";
import { GridToolbar } from "@/components/GridToolbar";
import { ColorLegend } from "@/components/ColorLegend";
import { ViolationsPanel } from "@/components/ViolationsPanel";
import { SolutionCompare } from "@/components/SolutionCompare";
import {
  getSchedules,
  createSchedule,
  getGrid,
  getColorLegend,
  getTaskTypes,
  getViolations,
  checkViolations,
  updateScheduleStatus,
  runSolver,
  runMultiSolve,
} from "@/lib/api";
import type {
  Schedule,
  GridData,
  ColorLegendItem,
  TaskType,
  Violation,
  SolutionSummary,
} from "@/lib/types";

export default function Home() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [currentSchedule, setCurrentSchedule] = useState<Schedule | null>(null);
  const [gridData, setGridData] = useState<GridData | null>(null);
  const [colorLegend, setColorLegend] = useState<ColorLegendItem[]>([]);
  const [taskTypes, setTaskTypes] = useState<TaskType[]>([]);
  const [violations, setViolations] = useState<Violation[]>([]);
  const [loading, setLoading] = useState(true);
  const [violationLoading, setViolationLoading] = useState(false);
  const [solving, setSolving] = useState(false);
  const [multiSolving, setMultiSolving] = useState(false);
  const [solutions, setSolutions] = useState<SolutionSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Get current year-month
  const now = new Date();
  const currentYearMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;

  useEffect(() => {
    loadInitialData();
  }, []);

  async function loadInitialData() {
    try {
      setLoading(true);
      const [scheds, colors, types] = await Promise.all([
        getSchedules(),
        getColorLegend(),
        getTaskTypes(),
      ]);
      setColorLegend(colors);
      setTaskTypes(types);
      setSchedules(scheds);

      if (scheds.length > 0) {
        await selectSchedule(scheds[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "読み込みエラー");
    } finally {
      setLoading(false);
    }
  }

  async function selectSchedule(schedule: Schedule) {
    setCurrentSchedule(schedule);
    const [grid, viols] = await Promise.all([
      getGrid(schedule.id),
      getViolations(schedule.id).catch(() => [] as Violation[]),
    ]);
    setGridData(grid);
    setViolations(viols);
  }

  async function handleCreateSchedule() {
    try {
      const yearMonth = prompt("年月を入力 (例: 2025-02)", currentYearMonth);
      if (!yearMonth) return;
      const schedule = await createSchedule(yearMonth);
      setSchedules((prev) => [schedule, ...prev]);
      await selectSchedule(schedule);
    } catch (err) {
      setError(err instanceof Error ? err.message : "作成エラー");
    }
  }

  async function refreshGrid() {
    if (currentSchedule) {
      const [grid, viols] = await Promise.all([
        getGrid(currentSchedule.id),
        getViolations(currentSchedule.id).catch(() => [] as Violation[]),
      ]);
      setGridData(grid);
      setViolations(viols);
    }
  }

  async function handleCheckViolations() {
    if (!currentSchedule) return;
    try {
      setViolationLoading(true);
      const viols = await checkViolations(currentSchedule.id);
      setViolations(viols);
    } catch (err) {
      setError(err instanceof Error ? err.message : "検証エラー");
    } finally {
      setViolationLoading(false);
    }
  }

  async function handleSolve() {
    if (!currentSchedule) return;
    try {
      setSolving(true);
      const result = await runSolver(currentSchedule.id);
      await refreshGrid();
      alert(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "案生成エラー");
    } finally {
      setSolving(false);
    }
  }

  async function handleMultiSolve() {
    if (!currentSchedule) return;
    try {
      setMultiSolving(true);
      const result = await runMultiSolve(currentSchedule.id);
      setSolutions(result.solutions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "複数案生成エラー");
    } finally {
      setMultiSolving(false);
    }
  }

  async function handleSolutionApplied() {
    setSolutions(null);
    await refreshGrid();
  }

  async function handleUpdateStatus(newStatus: string) {
    if (!currentSchedule) return;
    if (newStatus === "confirmed" && !confirm("スケジュールを確定しますか？確定後は編集できません。")) return;
    try {
      const updated = await updateScheduleStatus(currentSchedule.id, newStatus);
      setCurrentSchedule(updated);
      // Update in schedules list too
      setSchedules((prev) =>
        prev.map((s) => (s.id === updated.id ? updated : s))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "ステータス更新エラー");
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg text-gray-500">読み込み中...</div>
      </div>
    );
  }

  return (
    <main className="flex flex-col flex-1 min-h-0">
      <GridToolbar
        schedules={schedules}
        currentSchedule={currentSchedule}
        onSelectSchedule={selectSchedule}
        onCreateSchedule={handleCreateSchedule}
        onRefresh={refreshGrid}
        onUpdateStatus={handleUpdateStatus}
        onSolve={handleSolve}
        solving={solving}
        onMultiSolve={handleMultiSolve}
        multiSolving={multiSolving}
      />

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 mx-4 mt-2 rounded">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-2 underline text-sm"
          >
            閉じる
          </button>
        </div>
      )}

      <div className="flex-1 overflow-auto">
        {gridData ? (
          <ShiftGrid
            gridData={gridData}
            taskTypes={taskTypes}
            colorLegend={colorLegend}
            violations={violations}
            scheduleStatus={currentSchedule?.status}
            onRefresh={refreshGrid}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="text-center">
              <p className="text-lg mb-4">スケジュールがありません</p>
              <button
                onClick={handleCreateSchedule}
                className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
              >
                新規作成
              </button>
            </div>
          </div>
        )}
      </div>

      {currentSchedule && (
        <ViolationsPanel
          violations={violations}
          onCheck={handleCheckViolations}
          loading={violationLoading}
          scheduleId={currentSchedule.id}
        />
      )}

      <ColorLegend items={colorLegend} />

      {/* Solution compare modal */}
      {solutions && currentSchedule && (
        <SolutionCompare
          scheduleId={currentSchedule.id}
          solutions={solutions}
          onApplied={handleSolutionApplied}
          onClose={() => setSolutions(null)}
        />
      )}
    </main>
  );
}
