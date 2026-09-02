import { createRouter, createWebHistory } from 'vue-router'

export const VIEWS = [
  { name: 'map', path: '/map', label: 'Map', phase: 1 },
  { name: 'flows', path: '/flows', label: 'Flows', phase: 2 },
  { name: 'occupations', path: '/occupations', label: 'Occupations', phase: 1 },
  { name: 'cohorts', path: '/cohorts', label: 'Cohorts', phase: 2 },
  { name: 'economy', path: '/economy', label: 'Economy', phase: 1 },
  { name: 'supply', path: '/supply', label: 'AI Supply', phase: 3 },
  { name: 'compare', path: '/compare', label: 'Compare', phase: 2 },
  { name: 'about', path: '/about', label: 'About', phase: 5 },
] as const

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/map' },
    { path: '/map', name: 'map', component: () => import('@/views/MapView.vue') },
    {
      path: '/occupations',
      name: 'occupations',
      component: () => import('@/views/OccupationsView.vue'),
    },
    { path: '/economy', name: 'economy', component: () => import('@/views/DashboardView.vue') },
    { path: '/flows', name: 'flows', component: () => import('@/views/FlowsView.vue') },
    { path: '/cohorts', name: 'cohorts', component: () => import('@/views/CohortView.vue') },
    { path: '/compare', name: 'compare', component: () => import('@/views/CompareView.vue') },
    { path: '/supply', name: 'supply', component: () => import('@/views/SupplyView.vue') },
    { path: '/about', name: 'about', component: () => import('@/views/AboutView.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/map' },
  ],
})

export default router
