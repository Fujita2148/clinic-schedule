export interface Staff {
  id: string;
  name: string;
  employment_type: string;
  job_category: string;
  can_drive: boolean;
  can_bicycle: boolean;
  is_active: boolean;
}

export interface TimeBlock {
  code: string;
  display_name: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  sort_order: number;
}

export interface ColorLegendItem {
  code: string;
  display_name: string;
  bg_color: string;
  text_color: string;
  hatch_pattern: string | null;
  icon: string | null;
  sort_order: number;
  is_system: boolean;
  is_active: boolean;
}

export interface TaskType {
  code: string;
  display_name: string;
  default_blocks: string[];
  required_skills: string[];
  tags: string[];
  location_type: string;
  is_active: boolean;
}

export interface Schedule {
  id: string;
  year_month: string;
  status: string;
}

export interface GridCell {
  assignment_id: string | null;
  task_type_code: string | null;
  task_type_display_name: string | null;
  display_text: string | null;
  status_color: string | null;
  is_locked: boolean;
  source: string;
}

export interface StaffSkill {
  staff_id: string;
  skill_code: string;
  level: string;
}

export interface SkillMasterItem {
  code: string;
  name: string;
  description: string | null;
}

export interface Violation {
  id: string;
  violation_type: "hard" | "soft";
  severity: number | null;
  description: string;
  affected_date: string | null;
  affected_time_block: string | null;
  affected_staff: string[];
  suggestion: string | null;
  is_resolved: boolean;
}

export interface Rule {
  id: string;
  natural_text: string;
  template_type: string;
  scope: Record<string, unknown>;
  hard_or_soft: "hard" | "soft";
  weight: number;
  body: Record<string, unknown>;
  exceptions: unknown[];
  tags: string[];
  applies_to: Record<string, unknown>;
  is_active: boolean;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface GridRow {
  date: string;
  time_block: string;
  time_block_display: string;
  program_title: string | null;
  is_nightcare: boolean;
  summary_text: string | null;
  cells: Record<string, GridCell>;
}

export interface GridData {
  schedule_id: string;
  year_month: string;
  staff_list: { id: string; name: string; job_category: string }[];
  rows: GridRow[];
}
