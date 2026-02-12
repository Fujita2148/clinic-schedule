"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ShiftCell } from "@/components/ShiftCell";
import { CellEditor } from "@/components/CellEditor";
import { CellContextMenu } from "@/components/CellContextMenu";
import type {
  GridData,
  GridRow,
  TaskType,
  ColorLegendItem,
  Violation,
} from "@/lib/types";
import {
  upsertAssignment,
  deleteAssignment,
  toggleAssignmentLock,
  upsertDayProgram,
} from "@/lib/api";

interface Props {
  gridData: GridData;
  taskTypes: TaskType[];
  colorLegend: ColorLegendItem[];
  violations?: Violation[];
  scheduleStatus?: string;
  onRefresh: () => void;
}

const WEEKDAYS_JP = ["日", "月", "火", "水", "木", "金", "土"];
const TIME_BLOCKS_PER_DAY = 7;

interface EditingCell {
  scheduleId: string;
  staffId: string;
  date: string;
  timeBlock: string;
  currentTaskCode: string | null;
  currentDisplayText: string | null;
  currentStatusColor: string | null;
}

interface ContextMenuState {
  x: number;
  y: number;
  scheduleId: string;
  staffId: string;
  date: string;
  timeBlock: string;
  assignmentId: string | null;
  isLocked: boolean;
}

interface DncEditState {
  date: string;
  timeBlock: string;
  value: string;
}

export function ShiftGrid({
  gridData,
  taskTypes,
  colorLegend,
  violations = [],
  scheduleStatus = "draft",
  onRefresh,
}: Props) {
  const [editing, setEditing] = useState<EditingCell | null>(null);
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);
  const [dncEdit, setDncEdit] = useState<DncEditState | null>(null);

  const isConfirmed = scheduleStatus === "confirmed";

  // Build violation index: key = "date|time_block|staff_id" -> violation type
  const violationIndex = useMemo(() => {
    const index: Record<string, "hard" | "soft"> = {};
    for (const v of violations) {
      if (!v.affected_date || !v.affected_time_block) continue;
      for (const staffId of v.affected_staff) {
        const key = `${v.affected_date}|${v.affected_time_block}|${staffId}`;
        // hard takes precedence over soft
        if (index[key] !== "hard") {
          index[key] = v.violation_type;
        }
      }
    }
    return index;
  }, [violations]);

  // Group rows by date for week boundary detection
  const dateGroups = useMemo(() => {
    const groups: { date: string; weekday: number; rows: GridRow[] }[] = [];
    for (let i = 0; i < gridData.rows.length; i += TIME_BLOCKS_PER_DAY) {
      const dayRows = gridData.rows.slice(i, i + TIME_BLOCKS_PER_DAY);
      if (dayRows.length === 0) continue;
      const d = new Date(dayRows[0].date);
      groups.push({
        date: dayRows[0].date,
        weekday: d.getDay(),
        rows: dayRows,
      });
    }
    return groups;
  }, [gridData.rows]);

  // Keyboard shortcut: Delete key clears focused cell
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Delete" && contextMenu && contextMenu.assignmentId && !isConfirmed) {
        e.preventDefault();
        deleteAssignment(contextMenu.scheduleId, contextMenu.assignmentId).then(() => {
          setContextMenu(null);
          onRefresh();
        });
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [contextMenu, isConfirmed, onRefresh]);

  function handleCellClick(staffId: string, row: GridRow) {
    if (isConfirmed) return;
    const cell = row.cells[staffId];
    setEditing({
      scheduleId: gridData.schedule_id,
      staffId,
      date: row.date,
      timeBlock: row.time_block,
      currentTaskCode: cell?.task_type_code || null,
      currentDisplayText: cell?.display_text || null,
      currentStatusColor: cell?.status_color || null,
    });
  }

  function handleContextMenu(e: React.MouseEvent, staffId: string, row: GridRow) {
    if (isConfirmed) return;
    e.preventDefault();
    const cell = row.cells[staffId];
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      scheduleId: gridData.schedule_id,
      staffId,
      date: row.date,
      timeBlock: row.time_block,
      assignmentId: cell?.assignment_id || null,
      isLocked: cell?.is_locked || false,
    });
  }

  async function handleContextSetColor(color: string | null) {
    if (!contextMenu) return;
    try {
      await upsertAssignment(contextMenu.scheduleId, {
        staff_id: contextMenu.staffId,
        date: contextMenu.date,
        time_block: contextMenu.timeBlock,
        status_color: color || undefined,
      });
      onRefresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "エラー");
    }
  }

  async function handleContextToggleLock() {
    if (!contextMenu?.assignmentId) return;
    try {
      await toggleAssignmentLock(contextMenu.scheduleId, contextMenu.assignmentId);
      onRefresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "エラー");
    }
  }

  async function handleContextClear() {
    if (!contextMenu?.assignmentId) return;
    try {
      await deleteAssignment(contextMenu.scheduleId, contextMenu.assignmentId);
      onRefresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "エラー");
    }
  }

  async function handleSave(
    taskCode: string | null,
    displayText: string | null,
    statusColor: string | null
  ) {
    if (!editing) return;
    try {
      await upsertAssignment(editing.scheduleId, {
        staff_id: editing.staffId,
        date: editing.date,
        time_block: editing.timeBlock,
        task_type_code: taskCode || undefined,
        display_text: displayText || undefined,
        status_color: statusColor || undefined,
      });
      setEditing(null);
      onRefresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "保存エラー");
    }
  }

  function handleDncClick(row: GridRow) {
    if (isConfirmed) return;
    setDncEdit({
      date: row.date,
      timeBlock: row.time_block,
      value: row.program_title || "",
    });
  }

  const handleDncSave = useCallback(async (date: string, timeBlock: string, value: string) => {
    try {
      await upsertDayProgram(gridData.schedule_id, {
        date,
        time_block: timeBlock,
        program_title: value || undefined,
      });
      setDncEdit(null);
      onRefresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "保存エラー");
    }
  }, [gridData.schedule_id, onRefresh]);

  function formatDate(dateStr: string): string {
    const d = new Date(dateStr);
    return `${d.getMonth() + 1}/${d.getDate()} (${WEEKDAYS_JP[d.getDay()]})`;
  }

  function isWeekBoundary(index: number): boolean {
    if (index === 0) return false;
    const prevWeekday = dateGroups[index - 1].weekday;
    const currWeekday = dateGroups[index].weekday;
    return currWeekday < prevWeekday;
  }

  return (
    <div className="relative">
      {editing && (
        <CellEditor
          editing={editing}
          taskTypes={taskTypes}
          colorLegend={colorLegend}
          onSave={handleSave}
          onClose={() => setEditing(null)}
        />
      )}

      {contextMenu && (
        <CellContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          isLocked={contextMenu.isLocked}
          hasAssignment={!!contextMenu.assignmentId}
          onSetColor={handleContextSetColor}
          onToggleLock={handleContextToggleLock}
          onClear={handleContextClear}
          onClose={() => setContextMenu(null)}
        />
      )}

      <div className="overflow-auto max-h-[calc(100vh-8rem)]">
        <table className="border-collapse text-xs">
          <thead className="sticky top-0 z-20">
            <tr className="bg-gray-100">
              <th className="grid-header sticky left-0 z-30 min-w-[5rem]">
                日付
              </th>
              <th className="grid-header sticky left-[5rem] z-30 min-w-[3rem]">
                時間
              </th>
              <th className="grid-header sticky left-[8rem] z-30 min-w-[6rem]">
                DNC
              </th>
              <th className="grid-header sticky left-[14rem] z-30 min-w-[5rem]">
                予定
              </th>
              {gridData.staff_list.map((staff) => (
                <th
                  key={staff.id}
                  className="grid-header min-w-[5rem] text-center"
                >
                  <div>{staff.name}</div>
                  <div className="text-[10px] font-normal text-gray-500">
                    {staff.job_category}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dateGroups.map((group, groupIdx) => {
              const weekBoundary = isWeekBoundary(groupIdx);
              const isWeekend =
                group.weekday === 0 || group.weekday === 6;

              return group.rows.map((row, rowIdx) => {
                const isFirstRow = rowIdx === 0;
                const isDncEditing =
                  dncEdit?.date === row.date && dncEdit?.timeBlock === row.time_block;

                return (
                  <tr
                    key={`${row.date}-${row.time_block}`}
                    className={`
                      ${weekBoundary && isFirstRow ? "week-boundary" : ""}
                      ${isWeekend ? "weekend" : ""}
                    `}
                  >
                    {isFirstRow && (
                      <td
                        className={`date-cell ${
                          group.weekday === 0 ? "text-red-600" : ""
                        } ${group.weekday === 6 ? "text-blue-600" : ""}`}
                        rowSpan={TIME_BLOCKS_PER_DAY}
                      >
                        {formatDate(row.date)}
                      </td>
                    )}
                    <td className="time-block-cell">
                      {row.time_block_display}
                    </td>
                    <td
                      className="border border-gray-200 px-1 py-0.5 sticky left-[8rem] z-[5] bg-white min-w-[6rem] cursor-pointer hover:bg-blue-50"
                      onClick={() => handleDncClick(row)}
                    >
                      {isDncEditing ? (
                        <input
                          autoFocus
                          className="w-full text-xs border border-blue-400 rounded px-1 py-0.5"
                          value={dncEdit.value}
                          onChange={(e) =>
                            setDncEdit({ ...dncEdit, value: e.target.value })
                          }
                          onBlur={() =>
                            handleDncSave(dncEdit.date, dncEdit.timeBlock, dncEdit.value)
                          }
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              handleDncSave(dncEdit.date, dncEdit.timeBlock, dncEdit.value);
                            } else if (e.key === "Escape") {
                              setDncEdit(null);
                            }
                          }}
                        />
                      ) : (
                        <div className="text-xs">
                          {row.is_nightcare && (
                            <span className="text-purple-700 font-semibold">
                              ナイトケア
                            </span>
                          )}
                          {!row.is_nightcare && row.program_title && (
                            <span>{row.program_title}</span>
                          )}
                        </div>
                      )}
                    </td>
                    <td className="border border-gray-200 px-1 py-0.5 sticky left-[14rem] z-[5] bg-white min-w-[5rem]">
                      <div className="text-xs text-gray-600 truncate">
                        {row.summary_text}
                      </div>
                    </td>
                    {gridData.staff_list.map((staff) => {
                      const vKey = `${row.date}|${row.time_block}|${staff.id}`;
                      return (
                        <ShiftCell
                          key={staff.id}
                          cell={row.cells[staff.id]}
                          colorLegend={colorLegend}
                          violation={violationIndex[vKey] || null}
                          disabled={isConfirmed}
                          onClick={() => handleCellClick(staff.id, row)}
                          onContextMenu={(e) => handleContextMenu(e, staff.id, row)}
                        />
                      );
                    })}
                  </tr>
                );
              });
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
