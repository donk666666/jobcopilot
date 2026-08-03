import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,  // 2分钟超时（LLM调用可能较慢）
  headers: {
    'Content-Type': 'application/json',
  },
})

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export default api

// ---- API 函数 ----

// JD分析
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
}) {
  return api.post('/cover-letter/generate', data)
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

// 健康检查
export function healthCheck() {
  return api.get('/health')
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
