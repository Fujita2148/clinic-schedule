"use client";

import type { ColorLegendItem } from "@/lib/types";

interface Props {
  items: ColorLegendItem[];
}

export function ColorLegend({ items }: Props) {
  return (
    <footer className="bg-gray-50 border-t border-gray-200 px-4 py-2 flex items-center gap-4 flex-wrap text-sm">
      <span className="font-semibold text-gray-600">凡例:</span>
      {items.map((item) => (
        <div key={item.code} className="flex items-center gap-1">
          <span
            className={`inline-block w-4 h-4 rounded-sm border border-gray-300 ${
              item.hatch_pattern === "diagonal" ? "hatch-diagonal" : ""
            }`}
            style={{ backgroundColor: item.bg_color }}
          />
          <span>
            {item.icon && <span className="mr-0.5">{item.icon}</span>}
            {item.display_name}
          </span>
        </div>
      ))}
    </footer>
  );
}
