import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000
})

export const scriptApi = {
  async generateScript(data) {
    const response = await api.post('/generate-script', data)
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
