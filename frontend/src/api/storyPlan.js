import request from './request'

export const storyPlanApi = {
  getStructureTemplates() {
    return request({
      url: '/story-plan/templates',
      method: 'get'
    })
  },

  generateStoryPlan(data) {
    return request({
      url: '/story-plan/generate',
      method: 'post',
      data
    })
  },

  adjustScenePlan(data) {
    return request({
      url: '/story-plan/adjust-scene',
      method: 'post',
      data
    })
  },

  generateFullScript(data) {
    return request({
      url: '/story-plan/generate-full-script',
      method: 'post',
      data
    })
  },

  saveStoryPlan(data) {
    return request({
      url: '/story-plan/plan-story',
      method: 'post',
      data
    })
  },

  updateStoryPlan(id, data) {
    return request({
      url: `/story-plan/plan/${id}`,
      method: 'put',
      data
    })
  },

  getStoryPlan(id) {
    return request({
      url: `/story-plan/plan/${id}`,
      method: 'get'
    })
  },

  listStoryPlans(params) {
    return request({
      url: '/story-plan/plan',
      method: 'get',
      params
    })
  },

  deleteStoryPlan(id) {
    return request({
      url: `/story-plan/plan/${id}`,
      method: 'delete'
    })
  }
}