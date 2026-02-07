import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000
})

export const scriptApi = {
  async generateScript(data) {
    const response = await api.post('/generate-script-deepseek', data)
    return response.data
  },

  async generateScriptBatch(data) {
    const response = await api.post('/generate-script-batch', data)
    return response.data
  },

  async evaluateScript(data) {
    const response = await api.post('/evaluate-script-deepseek', data)
    return response.data
  },

  async evaluateQuality(data) {
    const response = await api.post('/quality-evaluate', data)
    return response.data
  },

  async evaluateQualityBatch(data) {
    const response = await api.post('/quality-evaluate-batch', data)
    return response.data
  },

  async getQualityMetrics() {
    const response = await api.get('/quality-metrics')
    return response.data
  },

  async searchStoryUnits(params) {
    const response = await api.post('/story-units/search', params)
    return response.data
  },

  async createStoryUnit(data) {
    const response = await api.post('/story-units', data)
    return response.data
  },

  async getStoryUnit(id) {
    const response = await api.get(`/story-units/${id}`)
    return response.data
  },

  async listStoryUnits(skip = 0, limit = 100) {
    const response = await api.get('/story-units', {
      params: { skip, limit }
    })
    return response.data
  }
}
