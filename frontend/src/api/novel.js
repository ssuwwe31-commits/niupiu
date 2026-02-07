import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

export const novelApi = {
  async uploadNovel(formData) {
    const config = {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }
    return (await api.post('/api/novels/upload', formData, config)).data
  },

  async listNovels(params = {}) {
    return (await api.get('/api/novels', { params })).data
  },

  async getNovel(novelId) {
    return (await api.get(`/api/novels/${novelId}`)).data
  },

  async decomposeNovel(novelId, data = {}) {
    return (await api.post(`/api/novels/${novelId}/decompose`, data)).data
  },

  async deleteNovel(novelId) {
    return (await api.delete(`/api/novels/${novelId}`)).data
  }
}
