"use client";

import { useEffect, useRef } from "react";

interface Props {
  x: number;
  y: number;
  isLocked: boolean;
  hasAssignment: boolean;
  onSetColor: (color: string | null) => void;
  onToggleLock: () => void;
  onClear: () => void;
  onClose: () => void;
}

const COLOR_OPTIONS = [
  { code: "off", label: "休み", color: "#FF0000" },
  { code: "pre_work", label: "出勤前", color: "#FFB6C1" },
  { code: "post_work", label: "退勤後", color: "#800080" },
  { code: "visit", label: "訪問", color: "#008000" },
  { code: null, label: "なし", color: null },
];

export function CellContextMenu({
  x,
  y,
  isLocked,
  hasAssignment,
  onSetColor,
  onToggleLock,
  onClear,
  onClose,
}: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [onClose]);

  // Adjust position to keep menu in viewport
  const style: React.CSSProperties = {
    position: "fixed",
    left: x,
    top: y,
    zIndex: 100,
  };

  return (
    <div ref={ref} style={style} className="bg-white border border-gray-300 rounded shadow-lg py-1 min-w-[140px]">
      <div className="px-3 py-1 text-[10px] text-gray-400 uppercase tracking-wide">状態色</div>
      {COLOR_OPTIONS.map((opt) => (
        <button
          key={opt.code ?? "none"}
          onClick={() => {
            onSetColor(opt.code);
            onClose();
          }}
          className="w-full text-left px-3 py-1.5 text-xs hover:bg-gray-100 flex items-center gap-2"
        >
          {opt.color ? (
            <span className="w-3 h-3 rounded-sm inline-block" style={{ backgroundColor: opt.color }} />
          ) : (
            <span className="w-3 h-3 rounded-sm inline-block border border-gray-300" />
          )}
          {opt.label}
        </button>
      ))}
      <div className="border-t border-gray-200 my-1" />
      {hasAssignment && (
        <>
          <button
            onClick={() => {
              onToggleLock();
              onClose();
            }}
            className="w-full text-left px-3 py-1.5 text-xs hover:bg-gray-100"
          >
            {isLocked ? "ロック解除" : "ロック"}
          </button>
          <button
            onClick={() => {
              onClear();
              onClose();
            }}
            className="w-full text-left px-3 py-1.5 text-xs hover:bg-gray-100 text-red-600"
          >
            クリア
          </button>
        </>
      )}
    </div>
  );
}
