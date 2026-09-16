import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 180000,  // 3分钟超时（LLM 全流程 60-90 秒，网络慢时 180 秒更稳）
  headers: {
    'Content-Type': 'application/json; charset=utf-8',
  },
  // 关键：让 axios 不要转换请求体编码（vite 代理 + 后端都按 UTF-8 处理）
  transformRequest: [(data) => {
    if (typeof data === 'string') return data
    return JSON.stringify(data)
  }],
})

// 请求拦截器：自动加 Authorization 头
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const url = error?.config?.url || ''
    const status = error?.response?.status || 'unknown'
    console.error(`[API ${status}] ${error?.config?.method?.toUpperCase()} ${url}: ${error?.message}`)
    // 401：token 失效或没登录，跳登录页（但不要在登录页本身触发跳转）
    if (status === 401 && !url.includes('/auth/')) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api

// ---- 认证 API ----

export interface UserInfo {
  id: number
  username: string
  nickname: string | null
  created_at: string
}

export interface AuthResponse {
  token: string
  user: UserInfo
}

export function login(username: string, password: string) {
  return api.post<AuthResponse>('/auth/login', { username, password })
}

export function register(username: string, password: string, nickname?: string) {
  return api.post<AuthResponse>('/auth/register', { username, password, nickname })
}

export function fetchMe() {
  return api.get<UserInfo>('/auth/me')
}

// ---- JD分析 ----
export function analyzeJD(jdText: string) {
  return api.post('/jd/analyze', { jd_text: jdText })
}

// JD分析历史
export function getJDAnalyses() {
  return api.get('/jd/history')
}

export function deleteJDAnalysis(id: number) {
  return api.delete(`/jd/history/${id}`)
}

// JD分析（流式）
export function analyzeJDStream(
  jdText: string,
  onChunk: (text: string) => void,
  onDone: (result: any) => void,
  onError: (err: string) => void,
) {
  fetch('/api/jd/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jd_text: jdText }),
  })
    .then(async (response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const reader = response.body?.getReader()
      if (!reader) throw new Error('No reader')
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.done) {
              onDone(data)
            } else if (data.chunk) {
              onChunk(data.chunk)
            }
          } catch {}
        }
      }
    })
    .catch((e) => onError(e.message))
}

// 简历匹配
export function matchResume(resumeText: string, jdAnalysis: string, jdAnalysisId?: number) {
  return api.post('/resume/match', {
    resume_text: resumeText,
    jd_analysis: jdAnalysis,
    jd_analysis_id: jdAnalysisId,
  })
}

// 简历改写
export function tailorResume(resumeText: string, jdAnalysis: string, matchResult: string, optId?: number, showAnnotations?: boolean) {
  return api.post('/resume/tailor', {
    resume_text: resumeText,
    jd_analysis: jdAnalysis,
    match_result: matchResult,
    opt_id: optId,
    show_annotations: showAnnotations,
  })
}

// 简历优化历史
export function getResumeOptimizations() {
  return api.get('/resume/history')
}

export function deleteResumeOptimization(id: number) {
  return api.delete(`/resume/history/${id}`)
}

// 求职信生成
export function generateCoverLetter(data: {
  jd_text: string
  resume_text: string
  candidate_name: string
  style: string
  recipient: string
  user_id?: string
  company_name?: string
  position_title?: string
}) {
  return api.post('/cover-letter/generate', data)
}

// 求职信历史
export function getCoverLetterHistory(userId?: string) {
  return api.get('/cover-letter/history', { params: userId ? { user_id: userId } : {} })
}

export function getCoverLetterDetail(id: number) {
  return api.get(`/cover-letter/history/${id}`)
}

export function deleteCoverLetter(id: number) {
  return api.delete(`/cover-letter/history/${id}`)
}

// 投递管理
export function listApplications(status?: string) {
  return api.get('/tracker/', { params: status ? { status } : {} })
}

export function getApplication(id: number) {
  return api.get(`/tracker/${id}`)
}

export function createApplication(data: any) {
  return api.post('/tracker/', data)
}

export function updateApplication(id: number, data: any) {
  return api.put(`/tracker/${id}`, data)
}

export function deleteApplication(id: number) {
  return api.delete(`/tracker/${id}`)
}

export function getTrackerStats() {
  return api.get('/tracker/stats')
}

// Agent全流程
export function runAgent(question: string) {
  return api.post('/agent/run', { question })
}

// 简历存储
export function getActiveResume() {
  return api.get('/resume/active')
}

export function saveActiveResume(resumeText: string) {
  return api.post('/resume/active', { resume_text: resumeText })
}

// 历史简历
export function getResumeHistory() {
  return api.get('/resume/versions')
}

export function updateResumeHistory(id: number, resumeText: string, name?: string) {
  return api.put(`/resume/${id}`, { resume_text: resumeText, name })
}

export function deleteResumeHistory(id: number) {
  return api.delete(`/resume/${id}`)
}

// 健康检查
export function healthCheck() {
  return api.get('/health')
}

// ===== 素材库（多份简历 + 多份 JD）=====

export interface ResumeMaterial {
  id: number
  title: string
  content: string
  is_active: number
  created_at: string
  updated_at: string
}

export interface JDMaterial {
  id: number
  title: string
  company_name: string | null
  content: string
  created_at: string
  updated_at: string
}

export function listResumeMaterials() {
  return api.get<ResumeMaterial[]>('/materials/resumes')
}
export function createResumeMaterial(data: { title: string; content: string; is_active?: boolean }) {
  return api.post<ResumeMaterial>('/materials/resumes', data)
}
export function updateResumeMaterial(id: number, data: { title?: string; content?: string; is_active?: boolean }) {
  return api.put<ResumeMaterial>(`/materials/resumes/${id}`, data)
}
export function deleteResumeMaterial(id: number) {
  return api.delete(`/materials/resumes/${id}`)
}

// 简历导出 Word
export function exportResumeDocx(data: { title?: string; content: string; candidate_name?: string }) {
  return api.post('/resume/export-docx', data, {
    responseType: 'blob',
    timeout: 30000,
  })
}

export function listJDMaterials() {
  return api.get<JDMaterial[]>('/materials/jds')
}
export function createJDMaterial(data: { title: string; company_name?: string; content: string }) {
  return api.post<JDMaterial>('/materials/jds', data)
}
export function updateJDMaterial(id: number, data: { title?: string; company_name?: string; content?: string }) {
  return api.put<JDMaterial>(`/materials/jds/${id}`, data)
}
export function deleteJDMaterial(id: number) {
  return api.delete(`/materials/jds/${id}`)
}

// 简历文件上传
export function uploadResume(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/resume/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
  })
}

// 一键全流程
export function submitFullPipeline(data: {
  resume_text: string
  jd_text: string
  jd_analysis_id?: number
  style?: string
  candidate_name?: string
}) {
  return api.post('/resume/full-pipeline', data)
}

// 查询异步任务状态
export function getTaskStatus(taskId: string) {
  return api.get(`/task/${taskId}`)
}

// Redis 状态
export function getRedisStatus() {
  return api.get('/resume/redis-status')
}

// 个性化打招呼
export function generateGreeting(data: {
  resume_text: string
  jd_text?: string
  company_name?: string
  position_title?: string
  candidate_name?: string
  style?: string
  variant_count?: number
}) {
  return api.post('/greet/generate', data)
}

// Chat 对话
export function chatSend(data: {
  question: string
  session_id?: string
  resume_text?: string
  jd_text?: string
}) {
  return api.post('/chat/send', data)
}

export function chatHistory(sessionId: string) {
  return api.get(`/chat/history/${sessionId}`)
}

export function chatClear(sessionId: string) {
  return api.delete(`/chat/history/${sessionId}`)
}
