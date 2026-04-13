import apiClient from './client'

export interface Workflow {
  name: string
  display_name: string
  status: string
  last_run?: string
  next_run?: string
  interval: string
}

export interface TriggerResponse {
  success: boolean
  message: string
  workflow: string
  triggered_at: string
}

export const workflowsApi = {
  getWorkflows: (): Promise<Workflow[]> =>
    apiClient.get('/workflows').then(res => res.data),
  
  triggerWorkflow: (name: string): Promise<TriggerResponse> =>
    apiClient.post(`/workflows/${name}/trigger`).then(res => res.data),
}
