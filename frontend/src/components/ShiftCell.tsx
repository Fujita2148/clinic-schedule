"use client";

import type { GridCell, ColorLegendItem } from "@/lib/types";

interface Props {
  cell: GridCell | undefined;
  colorLegend: ColorLegendItem[];
  onClick: () => void;
}

export function ShiftCell({ cell, colorLegend, onClick }: Props) {
  if (!cell) {
    return <td className="grid-cell" onClick={onClick} />;
  }

  const legend = cell.status_color
    ? colorLegend.find((c) => c.code === cell.status_color)
    : null;

  const bgStyle = legend
    ? { backgroundColor: legend.bg_color, color: legend.text_color }
    : {};

  const isHatched = legend?.hatch_pattern === "diagonal";

  return (
    <td
      className={`grid-cell ${isHatched ? "hatch-diagonal" : ""} ${
        cell.is_locked ? "locked" : ""
      }`}
      style={bgStyle}
      onClick={onClick}
    >
      {cell.is_locked && (
        <span className="absolute top-0 right-0 text-[8px]" title="ロック中">
          🔒
        </span>
      )}
      {legend?.icon && <span className="text-[10px]">{legend.icon}</span>}
      <div className="leading-tight">
        {cell.task_type_code && (
          <span className="font-medium">{cell.task_type_code}</span>
        )}
        {cell.display_text && (
          <div className="text-[10px] leading-tight whitespace-pre-wrap">
            {cell.display_text}
          </div>
        )}
      </div>
    </td>
  );
}
