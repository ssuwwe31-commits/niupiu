import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000
})

export const characterApi = {
  async createCharacter(data) {
    const response = await api.post('/characters', data)
    return response.data
  },

  async getCharacter(id) {
    const response = await api.get(`/characters/${id}`)
    return response.data
  },

  async updateCharacter(id, data) {
    const response = await api.put(`/characters/${id}`, data)
    return response.data
  },

  async listCharacters(skip = 0, limit = 100) {
    const response = await api.get('/characters', {
      params: { skip, limit }
    })
    return response.data
  },

  async deleteCharacter(id) {
    const response = await api.delete(`/characters/${id}`)
    return response.data
  }
}
