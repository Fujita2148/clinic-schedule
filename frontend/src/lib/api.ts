import type {
  ColorLegendItem,
  GridData,
  Schedule,
  Staff,
  TaskType,
  TimeBlock,
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

// Task Types
export const getTaskTypes = () => fetchJson<TaskType[]>("/task-types");

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

// Export
export const getExportCsvUrl = (scheduleId: string) =>
  `${API_BASE}/schedules/${scheduleId}/export/csv`;
