import type {
  ColorLegendItem,
  GridData,
  Rule,
  Schedule,
  SkillMasterItem,
  Staff,
  StaffSkill,
  TaskType,
  TimeBlock,
  Violation,
} from "./types";

const API_BASE = "/api/v1";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

// Staff
export const getStaffs = () => fetchJson<Staff[]>("/staffs");
export const createStaff = (data: Partial<Staff>) =>
  fetchJson<Staff>("/staffs", { method: "POST", body: JSON.stringify(data) });
export const updateStaff = (staffId: string, data: Partial<Staff>) =>
  fetchJson<Staff>(`/staffs/${staffId}`, { method: "PUT", body: JSON.stringify(data) });
export const deleteStaff = (staffId: string) =>
  fetchJson<void>(`/staffs/${staffId}`, { method: "DELETE" });
export const getStaffSkills = (staffId: string) =>
  fetchJson<StaffSkill[]>(`/staffs/${staffId}/skills`);
export const replaceStaffSkills = (staffId: string, skills: { skill_code: string; level?: string }[]) =>
  fetchJson<StaffSkill[]>(`/staffs/${staffId}/skills`, { method: "PUT", body: JSON.stringify(skills) });
export const getSkillMaster = () => fetchJson<SkillMasterItem[]>("/staffs/skills");

// Task Types
export const getTaskTypes = () => fetchJson<TaskType[]>("/task-types");
export const createTaskType = (data: Partial<TaskType>) =>
  fetchJson<TaskType>("/task-types", { method: "POST", body: JSON.stringify(data) });
export const updateTaskType = (code: string, data: Partial<TaskType>) =>
  fetchJson<TaskType>(`/task-types/${code}`, { method: "PUT", body: JSON.stringify(data) });
export const deleteTaskType = (code: string) =>
  fetchJson<void>(`/task-types/${code}`, { method: "DELETE" });

// Time Blocks
export const getTimeBlocks = () => fetchJson<TimeBlock[]>("/time-blocks");

// Color Legend
export const getColorLegend = () => fetchJson<ColorLegendItem[]>("/color-legend");

// Schedules
export const getSchedules = () => fetchJson<Schedule[]>("/schedules");
export const createSchedule = (year_month: string) =>
  fetchJson<Schedule>("/schedules", {
    method: "POST",
    body: JSON.stringify({ year_month }),
  });
export const updateScheduleStatus = (scheduleId: string, status: string) =>
  fetchJson<Schedule>(`/schedules/${scheduleId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });

// Grid
export const getGrid = (scheduleId: string) =>
  fetchJson<GridData>(`/schedules/${scheduleId}/grid`);

// Assignments
export const upsertAssignment = (
  scheduleId: string,
  data: {
    staff_id: string;
    date: string;
    time_block: string;
    task_type_code?: string;
    display_text?: string;
    status_color?: string;
  }
) =>
  fetchJson(`/schedules/${scheduleId}/assignments`, {
    method: "PUT",
    body: JSON.stringify(data),
  });

export const deleteAssignment = (scheduleId: string, assignmentId: string) =>
  fetch(`${API_BASE}/schedules/${scheduleId}/assignments/${assignmentId}`, {
    method: "DELETE",
  });

export const toggleAssignmentLock = (scheduleId: string, assignmentId: string) =>
  fetchJson(`/schedules/${scheduleId}/assignments/${assignmentId}/lock`, {
    method: "PATCH",
  });

// Violations
export const getViolations = (scheduleId: string) =>
  fetchJson<Violation[]>(`/schedules/${scheduleId}/violations`);
export const checkViolations = (scheduleId: string) =>
  fetchJson<Violation[]>(`/schedules/${scheduleId}/violations/check`, { method: "POST" });

// Day Programs
export const upsertDayProgram = (
  scheduleId: string,
  data: { date: string; time_block: string; program_title?: string; is_nightcare?: boolean; summary_text?: string }
) =>
  fetchJson(`/schedules/${scheduleId}/day-programs`, {
    method: "PUT",
    body: JSON.stringify(data),
  });

// Rules
export const getRules = (params?: { is_active?: boolean; template_type?: string; hard_or_soft?: string }) => {
  const searchParams = new URLSearchParams();
  if (params?.is_active !== undefined) searchParams.set("is_active", String(params.is_active));
  if (params?.template_type) searchParams.set("template_type", params.template_type);
  if (params?.hard_or_soft) searchParams.set("hard_or_soft", params.hard_or_soft);
  const qs = searchParams.toString();
  return fetchJson<Rule[]>(`/rules${qs ? `?${qs}` : ""}`);
};
export const createRule = (data: Partial<Rule>) =>
  fetchJson<Rule>("/rules", { method: "POST", body: JSON.stringify(data) });
export const updateRule = (ruleId: string, data: Partial<Rule>) =>
  fetchJson<Rule>(`/rules/${ruleId}`, { method: "PUT", body: JSON.stringify(data) });
export const toggleRule = (ruleId: string) =>
  fetchJson<Rule>(`/rules/${ruleId}/toggle`, { method: "PATCH" });
export const deleteRule = (ruleId: string) =>
  fetch(`${API_BASE}/rules/${ruleId}`, { method: "DELETE" });

// Export
export const getExportCsvUrl = (scheduleId: string) =>
  `${API_BASE}/schedules/${scheduleId}/export/csv`;
