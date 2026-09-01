import { createRouter, createWebHistory } from 'vue-router'

export const VIEWS = [
  { name: 'map', path: '/map', label: 'Map', phase: 1 },
  { name: 'flows', path: '/flows', label: 'Flows', phase: 2 },
  { name: 'occupations', path: '/occupations', label: 'Occupations', phase: 1 },
  { name: 'cohorts', path: '/cohorts', label: 'Cohorts', phase: 2 },
  { name: 'economy', path: '/economy', label: 'Economy', phase: 1 },
  { name: 'supply', path: '/supply', label: 'AI Supply', phase: 2 },
  { name: 'compare', path: '/compare', label: 'Compare', phase: 2 },
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
    ...(['flows', 'cohorts', 'supply', 'compare'] as const).map((name) => ({
      path: `/${name}`,
      name,
      component: () => import('@/views/PlaceholderView.vue'),
      props: { view: name },
    })),
    { path: '/:pathMatch(.*)*', redirect: '/map' },
  ],
})

export default router
