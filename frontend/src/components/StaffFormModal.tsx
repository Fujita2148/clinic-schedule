"use client";

import { useEffect, useState } from "react";
import type { Staff, SkillMasterItem, StaffSkill } from "@/lib/types";
import { getStaffSkills, getSkillMaster } from "@/lib/api";

interface Props {
  staff: Staff | null; // null = create mode
  onSave: (data: Partial<Staff>, skills: { skill_code: string; level: string }[]) => void;
  onClose: () => void;
}

const JOB_CATEGORIES = ["看護師", "准看護師", "作業療法士", "精神保健福祉士", "事務", "その他"];
const EMPLOYMENT_TYPES = ["常勤", "非常勤", "パート"];

export function StaffFormModal({ staff, onSave, onClose }: Props) {
  const [name, setName] = useState(staff?.name || "");
  const [jobCategory, setJobCategory] = useState(staff?.job_category || JOB_CATEGORIES[0]);
  const [employmentType, setEmploymentType] = useState(staff?.employment_type || EMPLOYMENT_TYPES[0]);
  const [canDrive, setCanDrive] = useState(staff?.can_drive || false);
  const [canBicycle, setCanBicycle] = useState(staff?.can_bicycle ?? true);
  const [skillMaster, setSkillMaster] = useState<SkillMasterItem[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadSkills();
  }, []);

  async function loadSkills() {
    try {
      setLoading(true);
      const master = await getSkillMaster();
      setSkillMaster(master);
      if (staff) {
        const current = await getStaffSkills(staff.id);
        setSelectedSkills(new Set(current.map((s) => s.skill_code)));
      }
    } catch {
      // Skills loading is optional
    } finally {
      setLoading(false);
    }
  }

  function toggleSkill(code: string) {
    setSelectedSkills((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    onSave(
      {
        name: name.trim(),
        job_category: jobCategory,
        employment_type: employmentType,
        can_drive: canDrive,
        can_bicycle: canBicycle,
      },
      Array.from(selectedSkills).map((code) => ({ skill_code: code, level: "qualified" }))
    );
  }

  return (
    <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-xl p-5 w-96 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-base">
            {staff ? "職員編集" : "職員新規作成"}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg">
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">名前</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">職種</label>
            <select
              value={jobCategory}
              onChange={(e) => setJobCategory(e.target.value)}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
            >
              {JOB_CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">雇用形態</label>
            <select
              value={employmentType}
              onChange={(e) => setEmploymentType(e.target.value)}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
            >
              {EMPLOYMENT_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          <div className="flex gap-4">
            <label className="flex items-center gap-1.5 text-sm">
              <input
                type="checkbox"
                checked={canDrive}
                onChange={(e) => setCanDrive(e.target.checked)}
              />
              運転可
            </label>
            <label className="flex items-center gap-1.5 text-sm">
              <input
                type="checkbox"
                checked={canBicycle}
                onChange={(e) => setCanBicycle(e.target.checked)}
              />
              自転車可
            </label>
          </div>

          {!loading && skillMaster.length > 0 && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">スキル</label>
              <div className="border border-gray-200 rounded p-2 max-h-32 overflow-y-auto space-y-1">
                {skillMaster.map((skill) => (
                  <label key={skill.code} className="flex items-center gap-1.5 text-sm">
                    <input
                      type="checkbox"
                      checked={selectedSkills.has(skill.code)}
                      onChange={() => toggleSkill(skill.code)}
                    />
                    {skill.name}
                  </label>
                ))}
              </div>
            </div>
          )}

          <div className="flex gap-2 pt-2">
            <button
              type="submit"
              className="flex-1 bg-blue-600 text-white py-1.5 rounded text-sm hover:bg-blue-700"
            >
              保存
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-gray-300 py-1.5 rounded text-sm hover:bg-gray-50"
            >
              キャンセル
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
