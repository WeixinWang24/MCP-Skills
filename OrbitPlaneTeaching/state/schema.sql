PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS learners (
  learner_id TEXT PRIMARY KEY,
  display_name TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  active_profile_id TEXT
);

CREATE TABLE IF NOT EXISTS learner_profiles (
  profile_id TEXT PRIMARY KEY,
  learner_id TEXT NOT NULL,
  level TEXT NOT NULL,
  primary_goal TEXT NOT NULL,
  prior_languages_json TEXT NOT NULL DEFAULT '[]',
  preferred_teaching_style TEXT NOT NULL,
  pacing TEXT NOT NULL,
  review_preference TEXT NOT NULL,
  explanation_language TEXT NOT NULL DEFAULT 'zh-CN',
  notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (learner_id) REFERENCES learners(learner_id)
);

CREATE TABLE IF NOT EXISTS learning_paths (
  path_id TEXT PRIMARY KEY,
  language TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  target_level TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS concepts (
  concept_id TEXT PRIMARY KEY,
  path_id TEXT NOT NULL,
  language TEXT NOT NULL,
  slug TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  difficulty INTEGER NOT NULL,
  default_order INTEGER NOT NULL,
  parent_concept_id TEXT,
  tags_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (path_id) REFERENCES learning_paths(path_id),
  FOREIGN KEY (parent_concept_id) REFERENCES concepts(concept_id)
);

CREATE TABLE IF NOT EXISTS concept_prerequisites (
  concept_id TEXT NOT NULL,
  prerequisite_concept_id TEXT NOT NULL,
  relation_type TEXT NOT NULL DEFAULT 'requires',
  PRIMARY KEY (concept_id, prerequisite_concept_id),
  FOREIGN KEY (concept_id) REFERENCES concepts(concept_id),
  FOREIGN KEY (prerequisite_concept_id) REFERENCES concepts(concept_id)
);

CREATE TABLE IF NOT EXISTS learner_concept_progress (
  learner_id TEXT NOT NULL,
  concept_id TEXT NOT NULL,
  status TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0.0,
  exposure_count INTEGER NOT NULL DEFAULT 0,
  practice_count INTEGER NOT NULL DEFAULT 0,
  applied_count INTEGER NOT NULL DEFAULT 0,
  review_count INTEGER NOT NULL DEFAULT 0,
  first_seen_at TEXT,
  last_seen_at TEXT,
  next_review_at TEXT,
  last_event_id TEXT,
  notes TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (learner_id, concept_id),
  FOREIGN KEY (learner_id) REFERENCES learners(learner_id),
  FOREIGN KEY (concept_id) REFERENCES concepts(concept_id)
);

CREATE TABLE IF NOT EXISTS learning_projects (
  project_id TEXT PRIMARY KEY,
  learner_id TEXT NOT NULL,
  title TEXT NOT NULL,
  repo_root TEXT,
  language TEXT NOT NULL,
  path_id TEXT,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (learner_id) REFERENCES learners(learner_id),
  FOREIGN KEY (path_id) REFERENCES learning_paths(path_id)
);

CREATE TABLE IF NOT EXISTS project_milestones (
  milestone_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  status TEXT NOT NULL,
  order_index INTEGER NOT NULL,
  target_concepts_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (project_id) REFERENCES learning_projects(project_id)
);

CREATE TABLE IF NOT EXISTS practice_records (
  practice_id TEXT PRIMARY KEY,
  learner_id TEXT NOT NULL,
  project_id TEXT,
  milestone_id TEXT,
  concept_ids_json TEXT NOT NULL,
  event_ids_json TEXT NOT NULL,
  file_paths_json TEXT NOT NULL DEFAULT '[]',
  practice_type TEXT NOT NULL,
  summary TEXT NOT NULL,
  outcome TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (learner_id) REFERENCES learners(learner_id),
  FOREIGN KEY (project_id) REFERENCES learning_projects(project_id),
  FOREIGN KEY (milestone_id) REFERENCES project_milestones(milestone_id)
);

CREATE TABLE IF NOT EXISTS event_evidence (
  evidence_id TEXT PRIMARY KEY,
  learner_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  event_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  concept_id TEXT,
  project_id TEXT,
  practice_id TEXT,
  file_path TEXT,
  line_hint INTEGER,
  summary TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (learner_id) REFERENCES learners(learner_id),
  FOREIGN KEY (concept_id) REFERENCES concepts(concept_id),
  FOREIGN KEY (project_id) REFERENCES learning_projects(project_id),
  FOREIGN KEY (practice_id) REFERENCES practice_records(practice_id)
);

CREATE TABLE IF NOT EXISTS review_queue (
  review_id TEXT PRIMARY KEY,
  learner_id TEXT NOT NULL,
  concept_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  due_at TEXT NOT NULL,
  priority INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (learner_id) REFERENCES learners(learner_id),
  FOREIGN KEY (concept_id) REFERENCES concepts(concept_id)
);

CREATE INDEX IF NOT EXISTS idx_learner_profiles_learner ON learner_profiles(learner_id);
CREATE INDEX IF NOT EXISTS idx_concepts_path_order ON concepts(path_id, default_order);
CREATE INDEX IF NOT EXISTS idx_progress_learner_status ON learner_concept_progress(learner_id, status);
CREATE INDEX IF NOT EXISTS idx_practice_learner_project ON practice_records(learner_id, project_id);
CREATE INDEX IF NOT EXISTS idx_evidence_event ON event_evidence(session_id, event_id);
CREATE INDEX IF NOT EXISTS idx_evidence_concept ON event_evidence(learner_id, concept_id);
CREATE INDEX IF NOT EXISTS idx_review_due ON review_queue(learner_id, status, due_at);
