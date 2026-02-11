"use client";

import { useState, useEffect } from "react";
import { createRule, updateRule, getTaskTypes } from "@/lib/api";
import type { Rule, TaskType } from "@/lib/types";

const TEMPLATE_TYPES = [
  { value: "headcount", label: "人員配置" },
  { value: "availability", label: "勤務制限" },
  { value: "skill_req", label: "スキル要件" },
  { value: "resource_req", label: "リソース要件" },
  { value: "preference", label: "優先配置" },
  { value: "recurring", label: "定期予定" },
  { value: "specific_date", label: "特定日" },
];

const WEEKDAYS = [
  { value: 0, label: "月" },
  { value: 1, label: "火" },
  { value: 2, label: "水" },
  { value: 3, label: "木" },
  { value: 4, label: "金" },
  { value: 5, label: "土" },
  { value: 6, label: "日" },
];

const TIME_BLOCKS = ["am", "lunch", "pm", "15", "16", "17", "18plus"];

interface Props {
  rule: Rule | null;
  onSave: () => void;
  onClose: () => void;
}

export function RuleFormModal({ rule, onSave, onClose }: Props) {
  const [naturalText, setNaturalText] = useState(rule?.natural_text || "");
  const [templateType, setTemplateType] = useState(rule?.template_type || "headcount");
  const [hardOrSoft, setHardOrSoft] = useState<"hard" | "soft">(rule?.hard_or_soft || "soft");
  const [weight, setWeight] = useState(rule?.weight || 100);
  const [tags, setTags] = useState(rule?.tags.join(", ") || "");

  // Body fields — headcount
  const [taskTypeCode, setTaskTypeCode] = useState<string>((rule?.body?.task_type_code as string) || (rule?.body?.event_code as string) || "");
  const [minStaff, setMinStaff] = useState<number>((rule?.body?.min_staff as number) || 1);
  const [maxStaff, setMaxStaff] = useState<string>(String((rule?.body?.max_staff as number) || ""));

  // Body fields — availability
  const [staffName, setStaffName] = useState<string>((rule?.body?.staff_name as string) || "");
  const [blockedWeekdays, setBlockedWeekdays] = useState<number[]>((rule?.body?.blocked_weekdays as number[]) || []);
  const [blockedBlocks, setBlockedBlocks] = useState<string[]>((rule?.body?.blocked_blocks as string[]) || []);

  // Body fields — preference
  const [preferredStaffName, setPreferredStaffName] = useState<string>((rule?.body?.preferred_staff_name as string) || "");
  const [prefWeekday, setPrefWeekday] = useState<string>(
    rule?.body?.weekday !== undefined && rule?.body?.weekday !== null ? String(rule.body.weekday) : ""
  );

  // Body fields — generic (JSON)
  const [bodyJson, setBodyJson] = useState<string>(
    rule?.body ? JSON.stringify(rule.body, null, 2) : "{}"
  );

  const [taskTypes, setTaskTypes] = useState<TaskType[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getTaskTypes().then(setTaskTypes).catch(() => {});
  }, []);

  function buildBody(): Record<string, unknown> {
    if (templateType === "headcount") {
      const body: Record<string, unknown> = { task_type_code: taskTypeCode, min_staff: minStaff };
      if (maxStaff) body.max_staff = Number(maxStaff);
      return body;
    }
    if (templateType === "availability") {
      return { staff_name: staffName, blocked_weekdays: blockedWeekdays, blocked_blocks: blockedBlocks };
    }
    if (templateType === "preference") {
      const body: Record<string, unknown> = { preferred_staff_name: preferredStaffName, task_type_code: taskTypeCode };
      if (prefWeekday !== "") body.weekday = Number(prefWeekday);
      return body;
    }
    // Generic
    try {
      return JSON.parse(bodyJson);
    } catch {
      return {};
    }
  }

  function buildScope(): Record<string, unknown> {
    if (templateType === "headcount" || templateType === "skill_req" || templateType === "resource_req") {
      return { type: "task_type" };
    }
    if (templateType === "availability") {
      return { type: "weekly" };
    }
    if (templateType === "preference") {
      return { type: "preference" };
    }
    return {};
  }

  async function handleSubmit() {
    if (!naturalText.trim()) return;
    setSaving(true);
    try {
      const data: Partial<Rule> = {
        natural_text: naturalText.trim(),
        template_type: templateType,
        hard_or_soft: hardOrSoft,
        weight: hardOrSoft === "hard" ? 1000 : weight,
        tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
        body: buildBody(),
        scope: buildScope(),
        applies_to: taskTypeCode ? { task_type: taskTypeCode } : {},
      };

      if (rule) {
        await updateRule(rule.id, data);
      } else {
        await createRule(data);
      }
      onSave();
    } catch (err) {
      alert(err instanceof Error ? err.message : "保存エラー");
    } finally {
      setSaving(false);
    }
  }

  const isGenericTemplate = !["headcount", "availability", "preference"].includes(templateType);

  return (
    <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center" onClick={onClose}>
      <div
        className="bg-white rounded-lg shadow-xl p-5 w-[28rem] max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold">{rule ? "ルール編集" : "ルール新規作成"}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg">
            ×
          </button>
        </div>

        <div className="space-y-3">
          {/* 自然文 */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">ルール説明（自然文）</label>
            <textarea
              value={naturalText}
              onChange={(e) => setNaturalText(e.target.value)}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
              rows={2}
              placeholder="例: 外出プログラムの時は職員3人つくこと"
            />
          </div>

          {/* テンプレート種別 */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">種別</label>
            <select
              value={templateType}
              onChange={(e) => setTemplateType(e.target.value)}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
            >
              {TEMPLATE_TYPES.map((tt) => (
                <option key={tt.value} value={tt.value}>
                  {tt.label}
                </option>
              ))}
            </select>
          </div>

          {/* hard/soft */}
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">制約タイプ</label>
              <select
                value={hardOrSoft}
                onChange={(e) => setHardOrSoft(e.target.value as "hard" | "soft")}
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
              >
                <option value="hard">必須 (hard)</option>
                <option value="soft">推奨 (soft)</option>
              </select>
            </div>
            {hardOrSoft === "soft" && (
              <div className="w-28">
                <label className="block text-xs font-medium text-gray-600 mb-1">重み (1-1000)</label>
                <input
                  type="number"
                  min={1}
                  max={1000}
                  value={weight}
                  onChange={(e) => setWeight(Number(e.target.value))}
                  className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
                />
              </div>
            )}
          </div>

          {/* タグ */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">タグ（カンマ区切り）</label>
            <input
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
              placeholder="例: 外出, 人員配置"
            />
          </div>

          <hr className="border-gray-200" />

          {/* === Body fields by template type === */}

          {templateType === "headcount" && (
            <>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">業務コード</label>
                <select
                  value={taskTypeCode}
                  onChange={(e) => setTaskTypeCode(e.target.value)}
                  className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
                >
                  <option value="">選択...</option>
                  {taskTypes.filter((t) => t.is_active).map((t) => (
                    <option key={t.code} value={t.code}>
                      {t.display_name} ({t.code})
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="block text-xs font-medium text-gray-600 mb-1">最低人数</label>
                  <input
                    type="number"
                    min={1}
                    value={minStaff}
                    onChange={(e) => setMinStaff(Number(e.target.value))}
                    className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
                  />
                </div>
                <div className="flex-1">
                  <label className="block text-xs font-medium text-gray-600 mb-1">最大人数（任意）</label>
                  <input
                    type="number"
                    min={1}
                    value={maxStaff}
                    onChange={(e) => setMaxStaff(e.target.value)}
                    className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
                    placeholder="未設定"
                  />
                </div>
              </div>
            </>
          )}

          {templateType === "availability" && (
            <>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">対象職員名</label>
                <input
                  value={staffName}
                  onChange={(e) => setStaffName(e.target.value)}
                  className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
                  placeholder="例: 八木"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">制限曜日</label>
                <div className="flex gap-2 flex-wrap">
                  {WEEKDAYS.map((wd) => (
                    <label key={wd.value} className="flex items-center gap-1 text-sm">
                      <input
                        type="checkbox"
                        checked={blockedWeekdays.includes(wd.value)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setBlockedWeekdays([...blockedWeekdays, wd.value]);
                          } else {
                            setBlockedWeekdays(blockedWeekdays.filter((v) => v !== wd.value));
                          }
                        }}
                      />
                      {wd.label}
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">制限ブロック（空=全ブロック）</label>
                <div className="flex gap-2 flex-wrap">
                  {TIME_BLOCKS.map((tb) => (
                    <label key={tb} className="flex items-center gap-1 text-sm">
                      <input
                        type="checkbox"
                        checked={blockedBlocks.includes(tb)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setBlockedBlocks([...blockedBlocks, tb]);
                          } else {
                            setBlockedBlocks(blockedBlocks.filter((v) => v !== tb));
                          }
                        }}
                      />
                      {tb}
                    </label>
                  ))}
                </div>
              </div>
            </>
          )}

          {templateType === "preference" && (
            <>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">優先職員名</label>
                <input
                  value={preferredStaffName}
                  onChange={(e) => setPreferredStaffName(e.target.value)}
                  className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
                  placeholder="例: 藤田"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">業務コード</label>
                <select
                  value={taskTypeCode}
                  onChange={(e) => setTaskTypeCode(e.target.value)}
                  className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
                >
                  <option value="">選択...</option>
                  {taskTypes.filter((t) => t.is_active).map((t) => (
                    <option key={t.code} value={t.code}>
                      {t.display_name} ({t.code})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">曜日（任意）</label>
                <select
                  value={prefWeekday}
                  onChange={(e) => setPrefWeekday(e.target.value)}
                  className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
                >
                  <option value="">指定なし</option>
                  {WEEKDAYS.map((wd) => (
                    <option key={wd.value} value={wd.value}>
                      {wd.label}曜日
                    </option>
                  ))}
                </select>
              </div>
            </>
          )}

          {isGenericTemplate && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">ルール本体（JSON）</label>
              <textarea
                value={bodyJson}
                onChange={(e) => setBodyJson(e.target.value)}
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm font-mono"
                rows={5}
                placeholder='{"key": "value"}'
              />
            </div>
          )}
        </div>

        <div className="flex gap-2 pt-4">
          <button
            onClick={handleSubmit}
            disabled={saving || !naturalText.trim()}
            className="flex-1 bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? "保存中..." : "保存"}
          </button>
          <button
            onClick={onClose}
            className="flex-1 border border-gray-300 px-3 py-1.5 rounded text-sm hover:bg-gray-50"
          >
            キャンセル
          </button>
        </div>
      </div>
    </div>
  );
}
