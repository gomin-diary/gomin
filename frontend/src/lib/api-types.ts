export type ErrorDetail = {
  path: (string | number)[];
  code: string;
  message: string;
};

export type ApiError = {
  code: string;
  message: string;
  details: ErrorDetail[];
};

export type ApiResponse<T> =
  | { success: true; data: T; error: null }
  | { success: false; data: null; error: ApiError };

export type HealthData = { status: "ok" };
export type DatabaseHealthData = HealthData & { database: "connected" };
