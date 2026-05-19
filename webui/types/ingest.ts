export type IngestItem = {
  text: string;
  source: string;
};

export type IngestRequest = {
  items: IngestItem[];
  retry_times?: number;
};

export type IngestResult = {
  record_id: string;
  source: string;
  summary: string;
  category: string;
  risk_keywords: string[];
};

export type IngestResponse = {
  total: number;
  success: number;
  failed: number;
  skipped: number;
  results: IngestResult[];
  errors: string[];
  skipped_messages: string[];
};
