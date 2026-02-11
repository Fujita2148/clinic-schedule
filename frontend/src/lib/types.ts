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
  display_text: string | null;
  status_color: string | null;
  is_locked: boolean;
  source: string;
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
