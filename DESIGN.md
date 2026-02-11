# 多層条件・自然文対応 職員シフト作成システム — システム設計書

## 1. 技術スタック

| レイヤ | 技術 | 選定理由 |
|--------|------|----------|
| フロントエンド | **Next.js 14 (App Router) + React 18 + TypeScript** | SSR/SSG対応、グリッドUIライブラリ豊富、型安全 |
| UIコンポーネント | **shadcn/ui + Tailwind CSS** | 軽量・カスタマイズ性が高い、日本語対応容易 |
| グリッド表示 | **TanStack Table (React Table v8)** | 大規模テーブル・仮想スクロール・列固定対応 |
| バックエンド | **Python 3.12 + FastAPI** | OR-Tools との親和性、Claude API SDK対応、非同期処理 |
| 制約ソルバ | **Google OR-Tools CP-SAT** | 制約充足+ソフト制約最適化、Python ネイティブ |
| LLM | **Claude API (Anthropic)** | Tool Use (Function Calling) 対応、日本語高精度 |
| データベース | **PostgreSQL 16** | JSONB（拡張レイヤ）、全文検索、堅牢性 |
| ORM | **SQLAlchemy 2.0 + Alembic** | 型ヒント対応、マイグレーション管理 |
| 検索 | **pgvector + PostgreSQL全文検索** | ルール辞書のRAG用埋め込み検索 |
| キャッシュ | **Redis** | ソルバ結果キャッシュ、セッション管理 |
| コンテナ | **Docker + Docker Compose** | ローカル/院内LAN運用対応 |

---

## 2. システムアーキテクチャ

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐  │
│  │月間シフト │ │イベント  │ │ルール  │ │違反/未充 │  │
│  │表 (Grid) │ │一覧      │ │辞書    │ │足レポート│  │
│  └────┬─────┘ └────┬─────┘ └───┬────┘ └────┬─────┘  │
│       └─────────────┴───────────┴────────────┘       │
│                         │ REST API / WebSocket       │
└─────────────────────────┼───────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────┐
│                  Backend (FastAPI)                    │
│                         │                            │
│  ┌──────────────────────┼──────────────────────┐     │
│  │              API Gateway Layer               │     │
│  └──────┬───────────┬───────────┬──────────────┘     │
│         │           │           │                     │
│  ┌──────▼─────┐ ┌───▼────┐ ┌───▼──────────┐         │
│  │ NLP Service │ │ Solver │ │ Shift/Event  │         │
│  │ (Claude API)│ │Service │ │ CRUD Service │         │
│  └──────┬─────┘ └───┬────┘ └───┬──────────┘         │
│         │           │           │                     │
│  ┌──────▼───────────▼───────────▼──────────┐         │
│  │           Domain Layer                    │         │
│  │  (Staff, Event, Rule, Schedule models)    │         │
│  └──────────────────┬───────────────────────┘         │
│                     │                                 │
│  ┌──────────────────▼───────────────────────┐         │
│  │         Data Access Layer                 │         │
│  │    (SQLAlchemy + Repository Pattern)      │         │
│  └──────────────────┬───────────────────────┘         │
└─────────────────────┼───────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
   ┌────▼────┐  ┌─────▼────┐  ┌────▼────┐
   │PostgreSQL│  │  Redis   │  │pgvector │
   │  (main)  │  │ (cache)  │  │ (embed) │
   └─────────┘  └──────────┘  └─────────┘
```

---

## 3. データベース設計（ERモデル）

### 3.1 テーブル一覧

```
staffs                  -- 職員マスタ
staff_skills            -- 職員スキル（多対多）
skill_master            -- スキル・資格マスタ
task_types              -- 業務コード辞書
events                  -- イベント（予定・案件）
event_candidates        -- イベント候補時間
rules                   -- ルール（制約）
rule_exceptions         -- ルール例外
schedules               -- 月間スケジュール（ヘッダ）
schedule_assignments    -- シフト割当（セル単位）
resources               -- 資源マスタ（車、自転車、部屋）
resource_bookings       -- 資源予約
violations              -- 違反/未充足レコード
audit_logs              -- 変更履歴
time_block_master       -- 時間ブロック定義（7ブロック）
color_legend            -- 色凡例（状態色）マスタ
day_programs            -- 日別プログラム（DNC列）
recurring_references    -- 定期予定参照データ
```

### 3.2 主要テーブル定義

#### staffs（職員）
```sql
CREATE TABLE staffs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    employment_type VARCHAR(20) NOT NULL,        -- 'full_time' | 'part_time'
    job_category    VARCHAR(50) NOT NULL,         -- '医師' | '事務' | 'PSW' | 'CP' | '看護師'
    can_drive       BOOLEAN DEFAULT FALSE,
    can_bicycle     BOOLEAN DEFAULT FALSE,
    work_hours_default JSONB,                     -- {"mon": {"start": 9, "end": 17}, ...}
    attributes      JSONB DEFAULT '{}',           -- 拡張レイヤ
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
```

#### staff_skills（職員スキル）
```sql
CREATE TABLE staff_skills (
    staff_id    UUID REFERENCES staffs(id),
    skill_code  VARCHAR(50) REFERENCES skill_master(code),
    level       VARCHAR(20) DEFAULT 'qualified',  -- 'qualified' | 'preferred' | 'learning'
    PRIMARY KEY (staff_id, skill_code)
);
```

#### skill_master（スキル・資格マスタ）
```sql
CREATE TABLE skill_master (
    code        VARCHAR(50) PRIMARY KEY,          -- 'PSW', 'CP', 'NURSE', 'DRIVER' 等
    name        VARCHAR(100) NOT NULL,
    description TEXT
);
```

#### task_types（業務コード辞書）
```sql
CREATE TABLE task_types (
    code                VARCHAR(50) PRIMARY KEY,  -- 'daycare', 'nightcare', 'visit_nurse' 等
    display_name        VARCHAR(100) NOT NULL,
    default_blocks      JSONB DEFAULT '["am"]',    -- デフォルト占有ブロック ["am","pm"] 等
    required_skills     JSONB DEFAULT '[]',       -- ["CP"]
    preferred_skills    JSONB DEFAULT '[]',
    required_resources  JSONB DEFAULT '[]',       -- ["car"] | ["room"]
    min_staff           INTEGER DEFAULT 1,
    max_staff           INTEGER,
    tags                JSONB DEFAULT '[]',       -- ["デイケア", "訪問"] 等
    location_type       VARCHAR(20) DEFAULT 'in_clinic', -- 'in_clinic' | 'outing' | 'visit'
    attributes          JSONB DEFAULT '{}',
    is_active           BOOLEAN DEFAULT TRUE
);
```

#### events（イベント）
```sql
CREATE TABLE events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type_code           VARCHAR(50) REFERENCES task_types(code),
    subject_name        VARCHAR(200),             -- 患者名/プログラム名
    subject_anonymous_id VARCHAR(50),             -- 匿名ID（LLM送信用）
    location_type       VARCHAR(20) NOT NULL,     -- 'in_clinic' | 'outing' | 'visit'
    duration_hours      INTEGER DEFAULT 1,
    time_constraint_type VARCHAR(20) NOT NULL,    -- 'fixed' | 'range' | 'candidates'
    time_constraint_data JSONB NOT NULL,          -- 固定: {"date":"2025-05-06","start":9}
                                                  -- 範囲: {"weekdays":[3],"period":"pm","month":"2025-05"}
                                                  -- 候補: {"slots":[{"date":"...","start":13},..]}
    required_skills     JSONB DEFAULT '[]',
    preferred_skills    JSONB DEFAULT '[]',
    required_resources  JSONB DEFAULT '[]',
    assigned_staff_ids  JSONB DEFAULT '[]',       -- 担当条件（必須/優先/可）
    priority            VARCHAR(20) DEFAULT 'required', -- 'required'|'high'|'medium'|'low'
    deadline            DATE,
    status              VARCHAR(20) DEFAULT 'unassigned', -- 'unassigned'|'assigned'|'hold'|'done'
    notes               TEXT,
    natural_text        TEXT,                     -- 元の自然文入力
    attributes          JSONB DEFAULT '{}',       -- 拡張レイヤ
    links               JSONB DEFAULT '[]',       -- 外部参照
    provisional_constraints JSONB DEFAULT '[]',   -- 仮ルール
    schedule_id         UUID REFERENCES schedules(id),
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);
```

#### rules（ルール/制約）
```sql
CREATE TABLE rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    natural_text    TEXT NOT NULL,                 -- 自然文（原文）
    template_type   VARCHAR(50) NOT NULL,          -- 'recurring'|'specific_date'|'headcount'
                                                   -- |'skill_req'|'resource_req'|'preference'|'availability'
    scope           JSONB NOT NULL,                -- {"type":"weekly","weekday":2,"week_of_month":3,"period":"am"}
    hard_or_soft    VARCHAR(10) NOT NULL,           -- 'hard' | 'soft'
    weight          INTEGER DEFAULT 100,            -- ソフト制約の重み (1-1000)
    body            JSONB NOT NULL,                 -- テンプレ種別に応じた制約本体
    exceptions      JSONB DEFAULT '[]',
    tags            JSONB DEFAULT '[]',
    applies_to      JSONB DEFAULT '{}',             -- 対象イベントタイプ/プログラム等
    is_active       BOOLEAN DEFAULT TRUE,
    created_by      VARCHAR(100),
    updated_by      VARCHAR(100),
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    embedding       vector(1024)                    -- pgvector: ルール検索用
);
```

#### schedules（月間スケジュール ヘッダ）
```sql
CREATE TABLE schedules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    year_month      VARCHAR(7) NOT NULL UNIQUE,    -- '2025-05'
    status          VARCHAR(20) DEFAULT 'draft',    -- 'draft'|'reviewing'|'confirmed'
    solver_result   JSONB,                          -- ソルバ実行結果メタ
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
```

#### schedule_assignments（シフト割当セル）
```sql
CREATE TABLE schedule_assignments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id     UUID REFERENCES schedules(id) NOT NULL,
    staff_id        UUID REFERENCES staffs(id) NOT NULL,
    date            DATE NOT NULL,
    time_block      VARCHAR(10) NOT NULL CHECK (time_block IN
                        ('am','lunch','pm','15','16','17','18plus')),
    -- time_block 対応表:
    --   'am'      = 9:00-12:00 (3時間一括：午前デイケア等)
    --   'lunch'   = 12:00-13:00 (昼休み)
    --   'pm'      = 13:00-15:00 (2時間一括：午後デイケア等)
    --   '15'      = 15:00-16:00
    --   '16'      = 16:00-17:00
    --   '17'      = 17:00-18:00
    --   '18plus'  = 18:00以降 (ナイトケア等)
    task_type_code  VARCHAR(50) REFERENCES task_types(code),
    event_id        UUID REFERENCES events(id),
    display_text    TEXT,                           -- セル表示テキスト（患者名・メモ等）
    status_color    VARCHAR(20),                    -- 'off'|'pre_work'|'post_work'|'visit'|カスタム
    is_locked       BOOLEAN DEFAULT FALSE,         -- 手動ロック（ソルバ変更不可）
    source          VARCHAR(20) DEFAULT 'manual',   -- 'manual'|'solver'|'imported'
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (schedule_id, staff_id, date, time_block)
);
```

#### resources（資源マスタ）
```sql
CREATE TABLE resources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type            VARCHAR(50) NOT NULL,           -- 'car'|'bicycle'|'room'
    name            VARCHAR(100) NOT NULL,
    capacity        INTEGER DEFAULT 1,              -- 同時利用可能数
    priority_for    JSONB DEFAULT '[]',             -- 優先利用者/業務 ["医師"]
    is_active       BOOLEAN DEFAULT TRUE
);
```

#### violations（違反/未充足）
```sql
CREATE TABLE violations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id     UUID REFERENCES schedules(id) NOT NULL,
    rule_id         UUID REFERENCES rules(id),
    violation_type  VARCHAR(20) NOT NULL,           -- 'hard'|'soft'
    severity        INTEGER,                         -- ペナルティスコア
    description     TEXT NOT NULL,
    affected_date   DATE,
    affected_time_block VARCHAR(10),               -- 'am'|'lunch'|'pm'|'15'|'16'|'17'|'18plus'
    affected_staff  JSONB DEFAULT '[]',
    suggestion      TEXT,                            -- 代替案（LLM生成）
    is_resolved     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

#### time_block_master（時間ブロック定義）
```sql
CREATE TABLE time_block_master (
    code            VARCHAR(10) PRIMARY KEY,       -- 'am','lunch','pm','15','16','17','18plus'
    display_name    VARCHAR(20) NOT NULL,           -- 'AM','昼','PM','15時','16時','17時','18-'
    start_time      TIME NOT NULL,
    end_time        TIME NOT NULL,
    duration_minutes INTEGER NOT NULL,
    sort_order      INTEGER NOT NULL
);
-- 初期データ:
-- ('am','AM','09:00','12:00',180,1)
-- ('lunch','昼','12:00','13:00',60,2)
-- ('pm','PM','13:00','15:00',120,3)
-- ('15','15時','15:00','16:00',60,4)
-- ('16','16時','16:00','17:00',60,5)
-- ('17','17時','17:00','18:00',60,6)
-- ('18plus','18-','18:00','20:00',120,7)
```

#### color_legend（色凡例マスタ）
```sql
CREATE TABLE color_legend (
    code            VARCHAR(20) PRIMARY KEY,       -- 'off','pre_work','post_work','visit' + カスタム
    display_name    VARCHAR(50) NOT NULL,           -- '休み','出勤前','退勤後','訪問'
    bg_color        VARCHAR(7) NOT NULL,            -- '#FF0000' hex
    text_color      VARCHAR(7) DEFAULT '#000000',
    hatch_pattern   VARCHAR(20),                    -- 'diagonal','none' (アクセシビリティ用)
    icon            VARCHAR(10),                    -- '🚲','🚗' 等
    sort_order      INTEGER NOT NULL,
    is_system       BOOLEAN DEFAULT FALSE,          -- true=4色固定, false=カスタム追加
    is_active       BOOLEAN DEFAULT TRUE
);
-- 初期データ（システム固定4色）:
-- ('off','休み','#FF0000','#FFFFFF','diagonal',NULL,1,true,true)
-- ('pre_work','出勤前','#FFB6C1','#000000',NULL,NULL,2,true,true)
-- ('post_work','退勤後','#800080','#FFFFFF',NULL,NULL,3,true,true)
-- ('visit','訪問','#008000','#FFFFFF',NULL,'🚲',4,true,true)
```

#### day_programs（日別プログラム / DNC列）
```sql
CREATE TABLE day_programs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id     UUID REFERENCES schedules(id) NOT NULL,
    date            DATE NOT NULL,
    time_block      VARCHAR(10) NOT NULL CHECK (time_block IN
                        ('am','lunch','pm','15','16','17','18plus')),
    program_title   VARCHAR(200),                   -- 'ヨガ','料理','マインドフルネス' 等
    is_nightcare    BOOLEAN DEFAULT FALSE,          -- ナイトケア帯（テキスト「ナイトケア」表示用）
    summary_text    TEXT,                            -- 予定欄のテキスト（面接日情報等）
    UNIQUE (schedule_id, date, time_block)
);
```

#### recurring_references（定期予定参照データ）
```sql
CREATE TABLE recurring_references (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category        VARCHAR(50) NOT NULL,            -- 'program','external','visit_nurse','meeting'
    name            VARCHAR(100) NOT NULL,            -- 'パソコン教室','大野','支援部会議' 等
    description     TEXT NOT NULL,                    -- '第2・第4水曜','週1（火木金）' 等
    recurrence_rule JSONB,                            -- {"weekdays":[2,4],"week_of_month":[2,4]}
    constraints     JSONB DEFAULT '{}',              -- {"exclude_weekdays":[1,2]} 等
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

### 3.3 ER図（概念）

```
staffs ──< staff_skills >── skill_master
  │
  │        task_types ──────── time_block_master (参照)
  │            │
  ├────< schedule_assignments >──── schedules
  │       (time_block)              │
  │            │                    ├── day_programs (DNC列・予定)
  │            ├── events ─────────┤
  │            │      │            │
  │            │      ├── event_candidates
  │            │      │
  │            │      └── provisional_constraints (JSONB)
  │            │
  │            └── resources ──< resource_bookings
  │
  │        rules ──< rule_exceptions
  │            │
  │            └── violations ──── schedules
  │                (time_block)
  │
  ├── audit_logs
  │
  color_legend (独立マスタ)
  recurring_references (独立マスタ → rules生成元)
```

---

## 4. API設計

### 4.1 エンドポイント一覧

#### 職員管理
| Method | Path | 説明 |
|--------|------|------|
| GET | `/api/v1/staffs` | 職員一覧（フィルタ対応） |
| POST | `/api/v1/staffs` | 職員登録 |
| GET | `/api/v1/staffs/{id}` | 職員詳細 |
| PUT | `/api/v1/staffs/{id}` | 職員更新 |

#### 業務コード辞書
| Method | Path | 説明 |
|--------|------|------|
| GET | `/api/v1/task-types` | 業務コード一覧 |
| POST | `/api/v1/task-types` | 業務コード追加 |
| PUT | `/api/v1/task-types/{code}` | 業務コード更新 |

#### イベント管理
| Method | Path | 説明 |
|--------|------|------|
| GET | `/api/v1/events` | イベント一覧（ステータス/月/タイプでフィルタ） |
| POST | `/api/v1/events` | イベント作成（フォーム） |
| POST | `/api/v1/events/from-text` | **自然文→イベント作成（Claude API経由）** |
| GET | `/api/v1/events/{id}` | イベント詳細 |
| PUT | `/api/v1/events/{id}` | イベント更新 |
| DELETE | `/api/v1/events/{id}` | イベント削除 |

#### ルール管理
| Method | Path | 説明 |
|--------|------|------|
| GET | `/api/v1/rules` | ルール一覧（検索/タグ/優先度フィルタ） |
| POST | `/api/v1/rules` | ルール作成（フォーム） |
| POST | `/api/v1/rules/from-text` | **自然文→ルール作成（Claude API経由）** |
| GET | `/api/v1/rules/{id}` | ルール詳細（自然文+式化） |
| PUT | `/api/v1/rules/{id}` | ルール更新 |
| PATCH | `/api/v1/rules/{id}/toggle` | ルールON/OFF切替 |
| GET | `/api/v1/rules/search` | **ルール検索（全文+ベクトル検索）** |
| POST | `/api/v1/rules/suggest-promotion` | 仮ルールのテンプレ昇格候補提示 |

#### スケジュール管理
| Method | Path | 説明 |
|--------|------|------|
| GET | `/api/v1/schedules` | スケジュール一覧 |
| POST | `/api/v1/schedules` | 月間スケジュール作成 |
| GET | `/api/v1/schedules/{id}` | スケジュール詳細（全割当含む） |
| GET | `/api/v1/schedules/{id}/grid` | **グリッド表示用データ（日付×職員 + 時間ブロック）** |

#### シフト割当
| Method | Path | 説明 |
|--------|------|------|
| PUT | `/api/v1/schedules/{id}/assignments` | 手動割当（セル編集） |
| PATCH | `/api/v1/schedules/{id}/assignments/{aid}/lock` | セルロック切替 |
| POST | `/api/v1/schedules/{id}/validate` | **即時検証（違反チェック）** |

#### ソルバ（案生成）
| Method | Path | 説明 |
|--------|------|------|
| POST | `/api/v1/schedules/{id}/solve` | **叩き台生成（ソルバ実行）** |
| GET | `/api/v1/schedules/{id}/solve/status` | ソルバ実行状態 |
| GET | `/api/v1/schedules/{id}/solutions` | **複数案一覧（A/B/C）** |
| POST | `/api/v1/schedules/{id}/solve/incremental` | **差分再調整（欠勤対応等）** |

#### 違反/レポート
| Method | Path | 説明 |
|--------|------|------|
| GET | `/api/v1/schedules/{id}/violations` | 違反/未充足一覧 |
| POST | `/api/v1/schedules/{id}/violations/explain` | **違反の自然文説明（Claude API経由）** |
| POST | `/api/v1/schedules/{id}/suggest-alternatives` | **代替案提示（Claude API経由）** |

#### 凡例・表示設定
| Method | Path | 説明 |
|--------|------|------|
| GET | `/api/v1/color-legend` | 色凡例一覧 |
| PUT | `/api/v1/color-legend/{code}` | 色凡例更新（管理者） |
| GET | `/api/v1/time-blocks` | 時間ブロック定義一覧 |

#### 日別プログラム（DNC列）
| Method | Path | 説明 |
|--------|------|------|
| GET | `/api/v1/schedules/{id}/day-programs` | DNC列データ取得 |
| PUT | `/api/v1/schedules/{id}/day-programs/{date}` | DNC列データ更新 |

#### 定期予定参照
| Method | Path | 説明 |
|--------|------|------|
| GET | `/api/v1/recurring-references` | 定期予定参照データ一覧 |
| POST | `/api/v1/recurring-references` | 定期予定参照データ追加 |

#### インポート/エクスポート
| Method | Path | 説明 |
|--------|------|------|
| POST | `/api/v1/import/excel` | Excelインポート |
| GET | `/api/v1/schedules/{id}/export/csv` | CSV出力 |
| GET | `/api/v1/schedules/{id}/export/pdf` | PDF出力 |

### 4.2 WebSocket
| Path | 用途 |
|------|------|
| `ws://api/v1/ws/schedule/{id}` | ソルバ進捗のリアルタイム通知 |
| `ws://api/v1/ws/chat` | 自然文入力のストリーミング応答 |

---

## 5. サービス層設計

### 5.1 NLP Service（Claude API連携）

```
NLPService
├── parse_event_from_text(text) → EventSchema
│   └── Claude Tool Use: create_event({type_code, subject, duration, ...})
├── parse_rule_from_text(text) → RuleSchema
│   └── Claude Tool Use: create_rule({template_type, scope, body, ...})
├── explain_violations(violations[]) → str
│   └── 違反リストを自然文で説明
├── suggest_alternatives(schedule, violations) → Suggestion[]
│   └── 代替案の方向性を提案
├── search_related_rules(query) → Rule[]
│   └── 埋め込み検索 + 全文検索
└── suggest_rule_promotion(provisional[]) → PromotionCandidate[]
```

**Claude API Tool定義（イベント作成用）:**
```json
{
  "name": "create_event",
  "description": "自然文からイベント(予定・案件)を構造化して作成する",
  "input_schema": {
    "type": "object",
    "properties": {
      "type_code": {
        "type": "string",
        "enum": ["daycare", "nightcare", "visit_nurse", "interview",
                 "psych_test", "pension_support", "meeting", "office_work"],
        "description": "業務コード"
      },
      "subject_name": {
        "type": "string",
        "description": "患者名/プログラム名"
      },
      "location_type": {
        "type": "string",
        "enum": ["in_clinic", "outing", "visit"]
      },
      "duration_hours": {
        "type": "integer",
        "minimum": 1
      },
      "time_constraint": {
        "type": "object",
        "properties": {
          "type": { "type": "string", "enum": ["fixed", "range", "candidates"] },
          "data": { "type": "object" }
        }
      },
      "required_skills": { "type": "array", "items": { "type": "string" } },
      "preferred_skills": { "type": "array", "items": { "type": "string" } },
      "required_resources": { "type": "array", "items": { "type": "string" } },
      "priority": {
        "type": "string",
        "enum": ["required", "high", "medium", "low"]
      },
      "deadline": { "type": "string", "format": "date" },
      "notes": { "type": "string" }
    },
    "required": ["type_code", "location_type", "duration_hours", "time_constraint"]
  }
}
```

### 5.2 Solver Service（OR-Tools CP-SAT）

```
SolverService
├── generate_initial(schedule_id, options) → Solution[]
│   ├── 1. 固定枠をロック
│   ├── 2. ハード制約を定義
│   ├── 3. ソフト制約を重み付きで定義
│   ├── 4. 難しい枠（訪問・運転・外出）から優先
│   └── 5. 複数解（重み違い A/B/C）を返却
├── validate(schedule_id) → Violation[]
│   └── 現在の割当に対する全制約チェック
├── solve_incremental(schedule_id, changes) → Solution
│   ├── 既存解を初期解として設定
│   └── 差分ペナルティ追加で再探索
└── find_unsat_core(schedule_id) → UnsatExplanation
    └── CP-SAT assumptions で不充足原因特定
```

**ソルバ変数モデル:**
```python
# 主要変数
x[s, d, b] = model.NewIntVar(0, num_tasks, f'x_{s}_{d}_{b}')
# s=staff, d=date, b=time_block ('am'|'lunch'|'pm'|'15'|'16'|'17'|'18plus')
# → 割り当てタスク種別

# イベント割当変数
y[e, b, s] = model.NewBoolVar(f'y_{e}_{b}_{s}')
# e=event, b=time_block候補, s=staff → そのイベントをその時間ブロックにその職員で割り当て

# 資源使用変数
r[res, d, b] = model.NewIntVar(0, capacity, f'r_{res}_{d}_{b}')
# 時間ブロックごとの資源使用量
```

### 5.3 Schedule Service（CRUD + ビジネスロジック）

```
ScheduleService
├── create_monthly(year_month) → Schedule
│   └── 定期イベント自動生成含む
├── get_grid_data(schedule_id, filters) → GridData
│   └── 日付×時間ブロック×職員のグリッド形式に整形（左: 日付/DNC固定、上: 職員固定）
├── assign_cell(schedule_id, staff_id, date, time_block, task) → Assignment
│   └── 即時検証付き
├── bulk_assign(schedule_id, assignments[]) → Result
├── lock_cell / unlock_cell
├── import_from_excel(file) → Schedule
└── export_to_csv / export_to_pdf
```

---

## 6. 画面設計

### 6.1 月間シフト表（メイン画面）

現行のExcelシート（横=職員、縦=日付×時間ブロック）をそのまま踏襲したグリッドUI。

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ [<前月] R7年5月 シフト表 [次月>]  [案生成▼] [検証] [出力▼]                    │
│ 自然文入力: [______________________________________________] [送信]          │
│ フィルタ: [全職種▼] [運転可□] [担当案件▼]   モード: [●作成 ○閲覧 ○印刷]    │
├──────┬─────┬──────────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬─────┤
│ 日付 │時間 │DNC       │予定  │藤田  │小石  │三田村│高松  │岩野  │森井  │→横  │
│      │ﾌﾞﾛｯｸ│(ﾌﾟﾛｸﾞﾗﾑ) │(日概要)│     │      │      │      │      │      │scroll│
╞══════╪═════╪══════════╪══════╪══════╪══════╪══════╪══════╪══════╪══════╪═════╡
│ 2/2  │ AM  │面接      │節分  │      │ DC   │ DC   │      │      │      │     │
│ (月) │     │          │準備  │      │沼田  │三田村│      │      │      │     │
│      │     │          │      │      │中村春│佐々木│      │      │      │     │
│      │ 昼  │          │      │      │      │      │      │      │      │     │
│      │ PM  │面接      │フリー│      │ DC   │ DC   │      │      │      │     │
│      │     │          │      │      │沼田  │青山  │      │      │      │     │
│      │     │          │      │      │佐々木│      │      │      │      │     │
│      │15時 │          │      │      │      │      │      │      │      │     │
│      │16時 │          │      │      │松崎  │16時  │      │      │      │     │
│      │     │          │      │      │検査  │中村春│      │      │      │     │
│      │17時 │          │      │      │      │      │      │      │      │     │
│      │18-  │          │      │佐久間│      │      │      │      │      │     │
├──────┼─────┼──────────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼─────┤
│ 2/3  │ AM  │節分      │恵方巻│      │ DC   │ DC   │      │      │      │     │
│ (火) │ 昼  │          │      │      │      │      │      │      │      │     │
│      │ PM  │節分      │豆つか│      │ DC   │ DC   │      │      │      │     │
│      │     │          │みゲーム│    │      │      │      │      │      │     │
│      │15時 │          │      │      │      │      │      │      │      │     │
│      │16時 │          │      │      │あゆみ│16時  │      │      │      │     │
│      │     │          │      │      │会    │上野光│      │      │      │     │
│      │17時 │          │      │      │      │      │      │      │      │     │
│      │18-  │          │      │      │18事務│      │      │      │      │     │
│      │     │          │      │      │局    │      │      │      │      │     │
╞══════╪═════╪══════════╪══════╪══════╪══════╪══════╪══════╪══════╪══════╪═════╡ ← 週境界(太線)
│ 2/6  │ AM  │料理      │      │      │ DC   │      │      │      │      │     │
│ (金) │ 昼  │          │      │      │      │      │      │      │      │     │
│      │ PM  │料理      │      │      │ DC   │      │      │      │      │     │
│      │15時 │ ナイトケア│      │      │NC準備│      │      │      │      │     │
│      │     │          │      │      │ﾒﾆｭｰ │      │      │      │      │     │
│      │16時 │ ナイトケア│      │      │      │      │      │      │      │     │
│      │17時 │ ナイトケア│      │      │  NC  │      │      │      │      │     │
│      │18-  │ ナイトケア│      │      │  NC  │      │      │      │      │     │
└──────┴─────┴──────────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴─────┘
 ← 左固定列(日付/時間/DNC/予定) →│← 職員列 (横スクロール) →

[凡例] ■赤:休み(斜線) ■ﾋﾟﾝｸ:出勤前 ■紫:退勤後 ■緑:訪問(🚲/🚗) ■振休  [凡例編集...]
[違反: 2件 ⚠] 車の同時使用超過(2/3 PM) | 部屋枠超過(2/5 AM)
```

#### セル内容の意味（重要な区別）

セル内の名前リストは、文脈により異なる意味を持つ：

1. **面接日**（DNC列のプログラムに「面接」を含む日）:
   AM/PM各職員セルに記載される名前は、その職員の**面接候補患者名**。
   - 例: 小石列に「沼田 中村春 佐々木」→ 小石がこれらの患者の面接を担当する可能性がある
   - デイケア参加者リストではない

2. **非面接日**（プログラムが「節分」「料理」等）:
   セルに記載される内容は**業務割当**。
   - `DC` = デイケア担当勤務
   - `訪問` + 患者名 = 訪問看護（緑背景）
   - `検査` + 患者名 = 心理検査（例: `松崎検査`）
   - `NC` = ナイトケア担当（金曜16-20時）

3. **複合セル内容の例**:
   - `16時 中村春` → 16時に中村春の個別予定（面接/検査等）
   - `支援部会議 スケジュール 藤田先生` → 会議参加
   - `NC準備 メニュー担当` → ナイトケア準備の役割担当
   - `振休` → 振替休日（赤背景）

#### DNC列（プログラム列）の仕様

- 左固定列のひとつ。日付列の右、予定列の左に配置
- 各時間ブロックにその時間帯のデイケアプログラムタイトルを表示
  - 例: AM=「ヨガ」「料理」「マインドフルネス」「カラオケ」「フリー」等
  - 昼/PM にも別のプログラムが入る場合あり（例: AM=面接, PM=フリー）
- **ナイトケア帯の表示**: 金曜16時以降のNC実施時間帯では、
  「ナイトケア」テキストラベルを表示する
  （現行PDFではピンクセルだが、出勤前ピンクとの混同を避けるためテキスト方式を採用）

**セル操作:**
- クリック → 業務コード選択（候補リスト: DC/NC/訪問/面接/検査/会議/記録/振休 等）
- ダブルクリック → 詳細編集（対象患者名、場所、メモ、資源、イベント紐付け）
- ドラッグ → 時間ブロック方向に延長（例: AM→PM に跨る予定）
- コピー/ペースト → Excel的に複数セルへ貼り付け（Ctrl+C/V）
- 右クリック → 状態色変更（休み/出勤前/退勤後/訪問/カスタム色）、ロック/解除

**セル表示の色レイヤ（2層分離）:**
- **状態色**（背景）: 赤=休み, ピンク=出勤前, 紫=退勤後, 緑=訪問, カスタム
  - 色だけに依存しない: 休み=斜線ハッチ, 訪問=🚲/🚗アイコン併用（色弱対応）
- **違反表示**（枠線/バッジ）: 赤枠=ハード違反, 黄枠=ソフト違反, ⚠バッジ
  - 状態色とは独立したレイヤで重畳表示
  - クリックで理由ポップオーバー（例: 部屋枠超過、車不足、資格不足）
- **ロック**: グレー半透明オーバーレイ + 🔒アイコン

### 6.1.1 色システムと凡例

#### デフォルト4色（システム固定）
| コード | 色 | 意味 | アクセシビリティ補助 |
|--------|------|--------|------|
| off | 赤 | 休み | 斜線ハッチ |
| pre_work | ピンク | 出勤前 | テキスト「出勤前」表示 |
| post_work | 紫 | 退勤後 | テキスト「退勤後」表示 |
| visit | 緑 | 訪問 | 🚲/🚗 アイコン |

#### カスタム色（管理者追加可能）
- 黄色、水色等を管理画面から追加・意味定義可能
- 例: 黄色=研修、水色=外部講師

#### 凡例の常時表示
- グリッド下部に凡例バーを常時表示
- 印刷時も凡例を出力
- 管理者が凡例の色・意味を編集可能（`/api/v1/color-legend`）

### 6.1.2 ヘッダ固定とスクロール

- **上部固定**: 職員名ヘッダ行（職種表示付き）を横スクロール時も固定
- **左側固定**: 日付・曜日・DNC・予定 の4列を縦スクロール時も固定
- **週区切り**: 週の境界に太線（現行PDF踏襲）
- **祝日表示**: 日付セルに赤背景 + 祝日名ラベル（例: 「建国記念日」「天皇誕生日」）
- **日単位スナップ**: 縦スクロール時、1日分（7ブロック）単位でスナップ停止すると見やすい

### 6.1.3 表示モード

| モード | 説明 |
|--------|------|
| 作成モード | 編集可能、違反/未充足を常時表示、右パネルにイベント一覧（未割当→割当済） |
| 閲覧モード | 編集不可、印刷レイアウト最適化、詳細はクリックで展開 |
| 印刷/PDF | 1か月1シート感を維持、ページ分割（週/半月）選択可、凡例必須出力 |

### 6.1.4 即時検証レイヤ

- 状態色（休み/出勤前等）とは**別レイヤ**で違反を表示
- 表示方法:
  - ハード違反: 赤枠線 + ⛔ バッジ
  - ソフト違反: 黄枠線 + ⚠ バッジ
  - クリックで理由ポップオーバー（例: 「部屋枠超過」「車不足」「資格不足」）
- 仮ルール（テンプレ未定義）由来の配置: 📝 バッジ（暗黙知保護）
  - 月末に「未検証ルール一覧」を自動生成

### 6.1.5 自然文入力バー

- 画面上部（グリッドツールバー内）に常時表示
- 入力例: 「山田さんの心理検査2回目を今月木曜午後のどこか」
- 入力後の動作:
  1. イベントが作成される（未割当状態）
  2. グリッド上の候補枠がハイライト表示
  3. 推奨スロット・担当候補が提示される
  4. 確認→確定で割当

### 6.2 イベント一覧画面

```
┌─────────────────────────────────────────────────────────────┐
│ イベント一覧 [2025年5月▼]                                    │
│ [+ フォーム入力] [💬 自然文入力]                              │
│ ステータス: [全て▼]  種別: [全て▼]  検索: [________]         │
├──────┬──────┬────────┬──────┬────────┬──────┬───────────────┤
│状態  │種別  │対象    │時間  │担当    │優先度│メモ           │
├──────┼──────┼────────┼──────┼────────┼──────┼───────────────┤
│■割当 │検査  │山田様  │5/8PM │佐藤(CP)│必須  │2回目          │
│□未割 │面接  │鈴木様  │木曜PM│—       │高    │               │
│◆保留 │訪問  │高橋様  │5/15  │—       │必須  │車必要         │
└──────┴──────┴────────┴──────┴────────┴──────┴───────────────┘

┌─ 自然文入力 ────────────────────────────────────────────────┐
│ > 山田さんの心理検査2回目を今月の木曜午後のどこかに入れる     │
│                                                              │
│ → 解析結果:                                                  │
│   種別: 心理検査  対象: 山田  所要: 2h  候補: 木曜13-17時    │
│   必須スキル: CP  部屋: 必要                                 │
│   [確定] [修正] [キャンセル]                                 │
└──────────────────────────────────────────────────────────────┘
```

### 6.3 ルール辞書画面

```
┌─────────────────────────────────────────────────────────────┐
│ ルール辞書 [+ 追加] [💬 自然文入力]                          │
│ タグ: [全て▼]  優先度: [全て▼]  検索: [________]            │
├──┬────────────────────────┬──────────────────┬──────┬──────┤
│ON│自然文                  │式化              │優先度│重み  │
├──┼────────────────────────┼──────────────────┼──────┼──────┤
│✓ │外出プログラムの時は    │headcount:        │必須  │ —    │
│  │職員3人つくこと        │  event=outing    │(hard)│      │
│  │                        │  min_staff=3     │      │      │
├──┼────────────────────────┼──────────────────┼──────┼──────┤
│✓ │ヨガは第3水曜の午前中  │recurring:        │高    │ 800  │
│  │                        │  program=yoga    │      │      │
│  │                        │  week=3,dow=wed  │      │      │
│  │                        │  period=am       │      │      │
├──┼────────────────────────┼──────────────────┼──────┼──────┤
│✗ │（無効）○○さんは      │availability:     │中    │ 500  │
│  │金曜午後不可            │  staff=XX        │      │      │
│  │                        │  dow=fri,pm=no   │      │      │
└──┴────────────────────────┴──────────────────┴──────┴──────┘
```

### 6.4 違反/未充足レポート画面

```
┌─────────────────────────────────────────────────────────────┐
│ 違反/未充足レポート [2025年5月▼] [案A▼]                      │
│                                                              │
│ ■ ハード違反: 1件                                            │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ ⛔ 5/12(月) 14:00 — 車の同時使用超過                      │ │
│ │    訪問(鈴木) と 訪問(田中) が同時に車を要求              │ │
│ │    [→ シフト表で確認] [代替案を見る]                      │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ■ ソフト違反: 3件 (合計ペナルティ: 1,300)                    │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ ⚠ 5/7(水) — ヨガが第1水曜に配置（第3水曜希望）          │ │
│ │   重み: 800  ルール: #R-003                               │ │
│ │   💬 「第3水曜に空きがありません。第1水曜または第4水曜が  │ │
│ │      代替候補です。第4水曜なら佐藤さんも対応可能です。」  │ │
│ │   [→ ルールを確認] [日程変更を試す]                      │ │
│ ├──────────────────────────────────────────────────────────┤ │
│ │ ⚠ 5/15(木) — 佐藤(CP)の優先配置未達                     │ │
│ │   重み: 300  ルール: #R-007                               │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ■ 案の比較                                                   │
│ ┌────────┬──────────┬──────────┬──────────┐                  │
│ │        │ 案A      │ 案B      │ 案C      │                  │
│ │ハード  │ 1件      │ 0件      │ 0件      │                  │
│ │ソフト  │ 1,300pt  │ 1,800pt  │ 2,100pt  │                  │
│ │特徴    │車衝突あり│全制約OK  │人員偏り  │                  │
│ └────────┴──────────┴──────────┴──────────┘                  │
│ [案Bを採用] [案Aを修正して再実行]                            │
└─────────────────────────────────────────────────────────────┘
```

### 6.5 定期予定参照データ（デフォルトサンプル）

PDF下部に記載されている繰り返し予定を、ルール/参照データの初期値として登録する。
`recurring_references` テーブルに初期データとして投入し、`rules` テーブルの `recurring` テンプレートタイプとしても登録する。

#### プログラム定期予定
| プログラム | 曜日/頻度 | 備考 |
|------------|-----------|------|
| パソコン教室 | 第2・第4水曜 | 24回シリーズ（日程固定）。2月は18日・25日（4日は外出プログラムのため変更） |
| 音楽 | 隔週（午後） | ハンドベル含む |
| ナイトケア | 毎週金曜 16:00-20:00 | NC準備→NC本体→振り返り |
| すずかけM | 月2回程度（金曜） | |
| WRAP | 不定期 | |
| マインドフルネス | 月1回程度 | |
| ヨガ | 月1回程度 | |
| 料理 | 月1回程度 | 防災関連テーマ等 |

#### 外来面接・訪問（外部予定）
| 対象 | 頻度 | 備考 |
|------|------|------|
| 大野 | 週1（火・木・金） | |
| 上野恵 | 月1 | |
| 上野光 | 週1 | iPad持参 |
| 畑 | 月1 | |
| 小此木 | 月1 | |
| 中谷 | 月1 | |
| 左海 | 月2 | 年金面接、検査 |

#### 訪問看護
| 担当 | 頻度 | 制約 |
|------|------|------|
| 沼田 | 月1回 | |
| 稲垣 | 月2回 | |
| 蟻川 | 月2回 | |
| 中村春 | 週1回 | |
| 佐々木 | 週1回 | 火・水以外 |
| 小坂 | 週1回（金曜） | |
| 大須賀 | 月2回 | |
| 大内 | 月2回 | |

#### 定期会議
| 会議名 | 頻度/備考 |
|--------|-----------|
| 支援部会議 | 定期（月複数回） |
| はらから事務局 | 定期 |
| 全体会議 | 定期 |
| ちたま運営会議 | 定期（2月は19日） |
| 多摩心理 | 定期 |
| OD（ODNJP） | 定期 |
| 棕櫚亭 | 定期 |
| あゆみ会 | 定期 |
| 家族会 | 定期（打合せ・実施） |

#### その他の定期事項
- 見学会: 月2回。DCインテークのため検査は入れない
- 面接内容: CBTフォロー、計画、年金、毎月のスケジュール目的確認、訪問打ち合わせ、SHARE
- 事務: スケジュール、メンバースケジュール、ケース記録、グループ記録、準備（生活、防災、ヘルス、WRAP、CBT、山あらし）
- 出前講座: 不定期（2月は4日）

---

## 7. ディレクトリ構成

```
clinic-schedule/
├── frontend/                          # Next.js アプリ
│   ├── src/
│   │   ├── app/                       # App Router
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx               # ダッシュボード
│   │   │   ├── schedule/
│   │   │   │   └── [yearMonth]/
│   │   │   │       └── page.tsx       # 月間シフト表
│   │   │   ├── events/
│   │   │   │   └── page.tsx           # イベント一覧
│   │   │   ├── rules/
│   │   │   │   └── page.tsx           # ルール辞書
│   │   │   └── reports/
│   │   │       └── page.tsx           # 違反レポート
│   │   ├── components/
│   │   │   ├── ui/                    # shadcn/ui コンポーネント
│   │   │   ├── schedule/
│   │   │   │   ├── ShiftGrid.tsx      # メイングリッド（日付×職員）
│   │   │   │   ├── ShiftCell.tsx      # セルコンポーネント（2層色表示対応）
│   │   │   │   ├── DNCColumn.tsx      # DNC列（プログラム表示）
│   │   │   │   ├── DaySummaryColumn.tsx # 予定列（日概要）
│   │   │   │   ├── ColorLegend.tsx    # 凡例バー
│   │   │   │   ├── GridToolbar.tsx    # ツールバー（自然文入力バー含む）
│   │   │   │   └── ViewModeToggle.tsx # モード切替（作成/閲覧/印刷）
│   │   │   ├── events/
│   │   │   │   ├── EventList.tsx
│   │   │   │   ├── EventForm.tsx
│   │   │   │   └── NaturalTextInput.tsx # 自然文入力
│   │   │   ├── rules/
│   │   │   │   ├── RuleList.tsx
│   │   │   │   ├── RuleDetail.tsx     # 自然文⇄式化並列表示
│   │   │   │   └── RuleForm.tsx
│   │   │   └── reports/
│   │   │       ├── ViolationList.tsx
│   │   │       ├── ViolationCard.tsx
│   │   │       └── SolutionCompare.tsx # 案A/B/C比較
│   │   ├── lib/
│   │   │   ├── api.ts                 # APIクライアント
│   │   │   └── types.ts              # 型定義
│   │   └── hooks/
│   │       ├── useSchedule.ts
│   │       ├── useEvents.ts
│   │       └── useWebSocket.ts
│   ├── package.json
│   ├── tailwind.config.ts
│   └── tsconfig.json
│
├── backend/                           # FastAPI アプリ
│   ├── app/
│   │   ├── main.py                    # FastAPI エントリポイント
│   │   ├── config.py                  # 設定
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── staffs.py
│   │   │   │   ├── task_types.py
│   │   │   │   ├── events.py
│   │   │   │   ├── rules.py
│   │   │   │   ├── schedules.py
│   │   │   │   ├── solver.py
│   │   │   │   ├── violations.py
│   │   │   │   ├── import_export.py
│   │   │   │   └── websocket.py
│   │   │   └── deps.py               # 依存性注入
│   │   ├── models/                    # SQLAlchemy モデル
│   │   │   ├── staff.py
│   │   │   ├── task_type.py
│   │   │   ├── event.py
│   │   │   ├── rule.py
│   │   │   ├── schedule.py
│   │   │   ├── resource.py
│   │   │   └── violation.py
│   │   ├── schemas/                   # Pydantic スキーマ
│   │   │   ├── staff.py
│   │   │   ├── event.py
│   │   │   ├── rule.py
│   │   │   ├── schedule.py
│   │   │   └── solver.py
│   │   ├── services/
│   │   │   ├── nlp_service.py         # Claude API 連携
│   │   │   ├── solver_service.py      # OR-Tools CP-SAT
│   │   │   ├── schedule_service.py    # スケジュール管理
│   │   │   ├── validation_service.py  # 即時検証
│   │   │   ├── rule_search_service.py # ルールRAG検索
│   │   │   └── export_service.py      # CSV/PDF出力
│   │   ├── repositories/             # データアクセス層
│   │   │   ├── staff_repo.py
│   │   │   ├── event_repo.py
│   │   │   ├── rule_repo.py
│   │   │   └── schedule_repo.py
│   │   └── core/
│   │       ├── database.py            # DB接続
│   │       ├── security.py            # 認証・匿名化
│   │       └── llm_client.py          # Claude APIクライアント
│   ├── alembic/                       # DBマイグレーション
│   │   └── versions/
│   ├── tests/
│   ├── requirements.txt
│   └── alembic.ini
│
├── docker-compose.yml                 # PostgreSQL + Redis + App
├── .env.example
├── README.md
└── 多層条件・自然文対応の職員シフト作成システム_要件定義書（ドラフト）.md
```

---

## 8. 処理フロー

### 8.1 自然文→イベント作成フロー

```
ユーザー入力: "山田さんの心理検査2回目を今月の木曜午後のどこかに入れる"
    │
    ▼
[Frontend] POST /api/v1/events/from-text
    │
    ▼
[NLP Service] Claude API (Tool Use)
    │  - システムプロンプト: 業務コード辞書 + ルール辞書（関連分）
    │  - ユーザーメッセージ: 自然文
    │  - Tool: create_event
    │
    ▼
[Claude応答] create_event({
    type_code: "psych_test",
    subject_name: "山田",
    location_type: "in_clinic",
    duration_hours: 2,
    time_constraint: { type: "range", data: { weekdays: [3], period: "pm", month: "2025-05" }},
    required_skills: ["CP"],
    required_resources: ["room"],
    priority: "required",
    notes: "2回目"
})
    │
    ▼
[バリデーション] JSON Schema + 業務辞書チェック
    │  - 曖昧さがあれば確認質問を生成
    │
    ▼
[Frontend] 確認画面表示 → ユーザー確定
    │
    ▼
[DB保存] events テーブルに INSERT
```

### 8.2 叩き台生成フロー

```
ユーザー: [案生成] ボタン押下
    │
    ▼
[Frontend] POST /api/v1/schedules/{id}/solve
    │
    ▼
[Solver Service]
    │
    ├── 1. データ収集
    │   ├── 全職員の勤務条件
    │   ├── 全イベント（未割当 + 固定）
    │   ├── 全有効ルール
    │   └── 資源一覧
    │
    ├── 2. モデル構築 (CP-SAT)
    │   ├── 変数定義: x[staff, date, time_block], y[event, time_block, staff]
    │   ├── ハード制約追加（同時1タスク、資源上限、必須資格...）
    │   ├── ソフト制約追加（重み付きペナルティ変数）
    │   └── 目的関数: Σペナルティ最小化
    │
    ├── 3. 解探索（重み設定を変えて最大3案）
    │   ├── 案A: バランス型
    │   ├── 案B: ハード制約完全遵守型
    │   └── 案C: ソフト制約最大充足型
    │
    ├── 4. 違反抽出
    │   └── 各案のハード/ソフト違反を記録
    │
    └── 5. 結果返却
        │
        ▼
[WebSocket] 進捗通知 → [Frontend] グリッド表示更新
```

### 8.3 修正ループフロー

```
ユーザー: グリッドのセルを手動変更
    │
    ▼
[Frontend] PUT /api/v1/schedules/{id}/assignments
    │
    ▼
[Validation Service] 即時検証
    ├── 変更セルに関わるルールのみチェック
    ├── 影響範囲分析（同時間帯の他スタッフ、資源）
    └── 違反があればハイライト + 理由表示
    │
    ▼
[Frontend] セル色更新 + 違反バー更新
    │
    ▼（ユーザーが「説明」を要求した場合）
[NLP Service] POST /api/v1/schedules/{id}/violations/explain
    └── Claude API で自然文説明 + 代替案の方向性を生成
```

---

## 9. セキュリティ設計

### 9.1 患者情報の取り扱い

| 処理 | 実名 | 匿名ID |
|------|------|---------|
| UI表示（権限あり） | ○ | — |
| UI表示（権限なし） | マスキング | ○ |
| DB保存 | ○ (subject_name) | ○ (subject_anonymous_id) |
| Claude API送信（構造化） | 不要時は匿名化 | ○ |
| Claude API送信（説明生成） | 必要時のみ実名 | ○ |
| ログ保存 | — | ○ + 送信内容ハッシュ |

### 9.2 認証・認可
- 初期: セッションベース認証（シフト作成者 / 閲覧者の2ロール）
- 将来拡張: OAuth2 / OIDC 対応可能な設計

---

## 10. 開発フェーズ（段階的実装）

### Phase 1: MVP（コア機能）
- DB設計 + マイグレーション
- 職員/業務コード/資源のマスタCRUD
- 月間スケジュール + 手動割当（グリッドUI）
- 即時検証（ハード制約のみ）
- CSV出力

### Phase 2: ソルバ統合
- OR-Tools CP-SAT によるソルバ実装
- ハード制約 + ソフト制約のモデル化
- 叩き台生成（単一案）
- 違反レポート画面

### Phase 3: LLM統合
- Claude API 連携（自然文→イベント/ルール変換）
- ルール辞書（自然文⇄式化）
- 違反の自然文説明
- ルール検索（RAG）

### Phase 4: 高度機能
- 複数案生成（A/B/C）
- インクリメンタル再調整
- Excelインポート
- PDF出力
- 代替案提示
- 仮ルールのテンプレ昇格

### Phase 5: 運用・品質
- 権限管理
- 監査ログ
- パフォーマンス最適化
- テスト充実
