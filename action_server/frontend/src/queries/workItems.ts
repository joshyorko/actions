import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Work Item Types
export type WorkItemState =
  | 'PENDING'
  | 'IN_PROGRESS'
  | 'DONE'
  | 'COMPLETED'
  | 'FAILED';

export class WorkItemsApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
  ) {
    super(message);
    this.name = 'WorkItemsApiError';
  }
}

export async function parseWorkItemsApiError(response: {
  json: () => Promise<unknown>;
  status: number;
  statusText: string;
}): Promise<WorkItemsApiError> {
  const bodyValue = await response.json().catch(() => ({}));
  const body =
    typeof bodyValue === 'object' && bodyValue !== null
      ? (bodyValue as Record<string, unknown>)
      : {};
  const detail = body.detail;
  let detailMessage: string | undefined;
  let code: string | undefined;
  if (typeof detail === 'string') {
    detailMessage = detail;
  } else if (typeof detail === 'object' && detail !== null) {
    const detailObject = detail as Record<string, unknown>;
    if (typeof detailObject.message === 'string') detailMessage = detailObject.message;
    if (typeof detailObject.code === 'string') code = detailObject.code;
  }
  const message =
    detailMessage ||
    (typeof body.message === 'string' && body.message) ||
    response.statusText ||
    `HTTP ${response.status}`;
  return new WorkItemsApiError(message, response.status, code);
}

export interface WorkItemResponse {
  id: string;
  queue_name: string;
  state: WorkItemState;
  payload: Record<string, any> | null;
  parent_id: string | null;
  error_code: string | null;
  error_message: string | null;
  files: string[];
  created_at: string;
  updated_at: string;
}

export interface WorkItemListResponse {
  items: WorkItemResponse[];
  total: number;
}

export interface QueueStatsResponse {
  queue_name: string;
  pending: number;
  in_progress: number;
  done: number;
  failed: number;
  total: number;
}

export interface CreateWorkItemPayload {
  queue_name: string;
  payload: Record<string, any>;
}

// Fetch work items with filters
export const useWorkItems = (
  queueName?: string,
  state?: WorkItemState | 'all',
  limit: number = 25
) => {
  return useQuery<WorkItemListResponse, Error>({
    queryKey: ['workItems', queueName, state, limit],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (queueName && queueName !== 'all') {
        params.append('queue_name', queueName);
      }
      if (state && state !== 'all') {
        params.append('state', state);
      }
      params.append('limit', limit.toString());

      const response = await fetch(`/api/work-items?${params.toString()}`);
      if (!response.ok) {
        throw await parseWorkItemsApiError(response);
      }
      return response.json();
    },
    refetchInterval: (query) => {
      // Don't auto-refresh after an error; the user can retry from the error state.
      return query.state.error ? false : 5000;
    },
    retry: (failureCount, error) => {
      // Runtime support, storage, or access errors need a user action.
      if (
        error instanceof WorkItemsApiError &&
        (error.status === 403 || error.status === 503)
      ) {
        return false;
      }
      return failureCount < 3;
    },
  });
};

// Fetch queue statistics
export const useWorkItemStats = (queueName?: string) => {
  return useQuery<QueueStatsResponse, Error>({
    queryKey: ['workItemStats', queueName],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (queueName && queueName !== 'all') {
        params.append('queue_name', queueName);
      }

      const response = await fetch(`/api/work-items/stats?${params.toString()}`);
      if (!response.ok) {
        throw await parseWorkItemsApiError(response);
      }
      return response.json();
    },
    refetchInterval: (query) => {
      return query.state.error ? false : 5000;
    },
    retry: (failureCount, error) => {
      if (
        error instanceof WorkItemsApiError &&
        (error.status === 403 || error.status === 503)
      ) {
        return false;
      }
      return failureCount < 3;
    },
  });
};

// Fetch single work item
export const useWorkItem = (itemId: string | null) => {
  return useQuery<WorkItemResponse, Error>({
    queryKey: ['workItem', itemId],
    queryFn: async () => {
      if (!itemId) throw new Error('Item ID is required');

      const response = await fetch(`/api/work-items/${itemId}`);
      if (!response.ok) {
        throw await parseWorkItemsApiError(response);
      }
      return response.json();
    },
    enabled: !!itemId,
  });
};

// Create work item mutation
export const useCreateWorkItem = () => {
  const queryClient = useQueryClient();

  return useMutation<WorkItemResponse, Error, CreateWorkItemPayload>({
    mutationFn: async (payload) => {
      const response = await fetch('/api/work-items', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw await parseWorkItemsApiError(response);
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workItems'] });
      queryClient.invalidateQueries({ queryKey: ['workItemStats'] });
    },
  });
};

// Delete work item mutation
export const useDeleteWorkItem = () => {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: async (itemId) => {
      const response = await fetch(`/api/work-items/${itemId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw await parseWorkItemsApiError(response);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workItems'] });
      queryClient.invalidateQueries({ queryKey: ['workItemStats'] });
    },
  });
};

// Fetch unique queue names from work items
export const useWorkItemQueues = () => {
  return useQuery<string[], Error>({
    queryKey: ['workItemQueues'],
    queryFn: async () => {
      const response = await fetch('/api/work-items?limit=1000');
      if (!response.ok) {
        throw await parseWorkItemsApiError(response);
      }
      const data: WorkItemListResponse = await response.json();
      const queueNames = new Set<string>();
      data.items.forEach((item) => queueNames.add(item.queue_name));
      return Array.from(queueNames).sort();
    },
    refetchInterval: 10000,
    retry: (failureCount, error) => {
      if (
        error instanceof WorkItemsApiError &&
        (error.status === 403 || error.status === 503)
      ) {
        return false;
      }
      return failureCount < 3;
    },
  });
};

// Download file helper
export const downloadWorkItemFile = async (itemId: string, fileName: string) => {
  const response = await fetch(`/api/work-items/${itemId}/files/${fileName}`);

  if (!response.ok) {
    throw new Error('Failed to download file');
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};
