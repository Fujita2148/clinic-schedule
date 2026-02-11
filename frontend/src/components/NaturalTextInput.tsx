"use client";

import { useState } from "react";
import { parseEventFromText, createEvent } from "@/lib/api";
import type { NlpParsedEvent } from "@/lib/types";

const LOCATION_LABELS: Record<string, string> = {
  in_clinic: "院内",
  outing: "外出",
  visit: "訪問",
};

const PRIORITY_LABELS: Record<string, string> = {
  required: "必須",
  high: "高",
  medium: "中",
  low: "低",
};

const TC_TYPE_LABELS: Record<string, string> = {
  fixed: "日時確定",
  range: "範囲指定",
  candidates: "候補日時",
};

const WEEKDAY_LABELS = ["月", "火", "水", "木", "金", "土", "日"];
const PERIOD_LABELS: Record<string, string> = { am: "午前", pm: "午後" };

function formatTimeConstraint(tc: NlpParsedEvent["time_constraint"]): string {
  const { type, data } = tc;
  if (type === "fixed") {
    return `${data.date ?? "?"} ${data.start ?? "?"}時〜`;
  }
  if (type === "range") {
    const weekdays = (data.weekdays as number[] | undefined)
      ?.map((d) => WEEKDAY_LABELS[d] ?? d)
      .join("・");
    const period = PERIOD_LABELS[(data.period as string) ?? ""] ?? data.period ?? "";
    const month = data.month ?? "";
    return [month, weekdays, period].filter(Boolean).join(" ");
  }
  if (type === "candidates") {
    const slots = data.slots as Array<{ date?: string; start?: number }> | undefined;
    if (slots?.length) {
      return slots
        .slice(0, 3)
        .map((s) => `${s.date ?? "?"} ${s.start ?? "?"}時`)
        .join(", ");
    }
  }
  return JSON.stringify(data);
}

interface Props {
  scheduleId: string | null;
  onEventCreated: () => void;
  onClose: () => void;
}

export function NaturalTextInput({ scheduleId, onEventCreated, onClose }: Props) {
  const [text, setText] = useState("");
  const [parsing, setParsing] = useState(false);
  const [parsed, setParsed] = useState<NlpParsedEvent | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleParse() {
    if (!text.trim()) return;
    setParsing(true);
    setError(null);
    setParsed(null);
    try {
      const res = await parseEventFromText(text.trim(), scheduleId ?? undefined);
      setParsed(res.parsed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "パースエラー");
    } finally {
      setParsing(false);
    }
  }

  async function handleConfirm() {
    if (!parsed) return;
    setConfirming(true);
    setError(null);
    try {
      await createEvent({
        type_code: parsed.type_code,
        subject_name: parsed.subject_name,
        location_type: parsed.location_type,
        duration_hours: parsed.duration_hours,
        time_constraint_type: parsed.time_constraint.type,
        time_constraint_data: parsed.time_constraint.data,
        required_skills: parsed.required_skills,
        preferred_skills: parsed.preferred_skills,
        required_resources: parsed.required_resources,
        priority: parsed.priority,
        notes: parsed.notes,
        natural_text: text.trim(),
        schedule_id: scheduleId,
      });
      onEventCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "作成エラー");
    } finally {
      setConfirming(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleParse();
    }
  }

  return (
    <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center" onClick={onClose}>
      <div
        className="bg-white rounded-lg shadow-xl p-5 w-[36rem] max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-bold text-gray-800">自然文入力</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>

        <div className="flex gap-2 mb-3">
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="例: 山田さんの心理検査2回目を今月の木曜午後のどこかに入れる"
            className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            disabled={parsing}
          />
          <button
            onClick={handleParse}
            disabled={parsing || !text.trim()}
            className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {parsing ? "解析中..." : "送信"}
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm mb-3">
            {error}
          </div>
        )}

        {parsed && (
          <div className="border border-gray-200 rounded p-4 bg-gray-50">
            <h4 className="text-sm font-bold text-gray-600 mb-2">解析結果:</h4>
            <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
              {parsed.type_code && (
                <>
                  <dt className="text-gray-500">種別</dt>
                  <dd>{parsed.type_code}</dd>
                </>
              )}
              {parsed.subject_name && (
                <>
                  <dt className="text-gray-500">対象</dt>
                  <dd>{parsed.subject_name}</dd>
                </>
              )}
              <dt className="text-gray-500">場所</dt>
              <dd>{LOCATION_LABELS[parsed.location_type] ?? parsed.location_type}</dd>
              <dt className="text-gray-500">所要</dt>
              <dd>{parsed.duration_hours}h</dd>
              <dt className="text-gray-500">候補</dt>
              <dd>
                <span className="text-xs text-gray-400 mr-1">
                  [{TC_TYPE_LABELS[parsed.time_constraint.type] ?? parsed.time_constraint.type}]
                </span>
                {formatTimeConstraint(parsed.time_constraint)}
              </dd>
              {parsed.required_skills.length > 0 && (
                <>
                  <dt className="text-gray-500">必須スキル</dt>
                  <dd>{parsed.required_skills.join(", ")}</dd>
                </>
              )}
              {parsed.required_resources.length > 0 && (
                <>
                  <dt className="text-gray-500">リソース</dt>
                  <dd>{parsed.required_resources.join(", ")}</dd>
                </>
              )}
              <dt className="text-gray-500">優先度</dt>
              <dd>{PRIORITY_LABELS[parsed.priority] ?? parsed.priority}</dd>
              {parsed.notes && (
                <>
                  <dt className="text-gray-500">備考</dt>
                  <dd>{parsed.notes}</dd>
                </>
              )}
            </dl>

            <div className="flex gap-2 mt-4">
              <button
                onClick={handleConfirm}
                disabled={confirming}
                className="bg-green-600 text-white px-4 py-1.5 rounded text-sm hover:bg-green-700 disabled:opacity-50"
              >
                {confirming ? "作成中..." : "確定"}
              </button>
              <button
                onClick={() => setParsed(null)}
                className="border border-gray-300 px-4 py-1.5 rounded text-sm hover:bg-gray-50"
              >
                キャンセル
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
