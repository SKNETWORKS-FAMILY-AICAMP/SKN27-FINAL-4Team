import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/chat',
  },
  {
    path: '/chat',
    component: () => import('../views/ChatView.vue'),
  },
  {
    path: '/chat/council',
    component: () => import('../views/InnerCouncilView.vue'),
  },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
