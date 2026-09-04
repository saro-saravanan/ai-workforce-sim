<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { REPO_URL } from '@/api/client'
import { useTourStore } from '@/stores/tour'

const AUTHOR = 'Saro Saravanan'
const AUTHOR_URL = 'https://saro-saravanan.github.io'
const tour = useTourStore()
</script>

<template>
  <div class="credit" role="contentinfo" aria-label="Credits, terms and collaboration">
    <span class="who">
      <span class="name">AI Workforce Sim</span>
      <span class="sep name" aria-hidden="true">·</span>
      <span class="long">an open-source scenario model </span>by
      <a :href="AUTHOR_URL" target="_blank" rel="noopener author">{{ AUTHOR }}</a>
    </span>
    <span class="sep" aria-hidden="true">·</span>
    <RouterLink class="why" :to="{ path: '/about', query: $route.query, hash: '#why' }" title="Why this was built, and the questions it tries to answer">Why</RouterLink>
    <span class="sep" aria-hidden="true">·</span>
    <span class="terms">
      <span class="long">Scenarios, not forecasts or advice: </span>
      <RouterLink :to="{ path: '/terms', query: $route.query }" title="Terms of use: no warranty, no liability, no advice">Terms</RouterLink>
    </span>
    <span class="sep" aria-hidden="true">·</span>
    <a class="repo" :href="REPO_URL" target="_blank" rel="noopener" title="Bugs, data, ideas and pull requests are welcome">
      <span class="long">Collaborators welcome on </span>GitHub
    </a>
    <span class="spacer"></span>
    <button class="tour" type="button" title="A two-minute walk through the app" @click="tour.start()">
      Take the tour
    </button>
  </div>
</template>

<style scoped>
.credit {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 24px;
  padding: 2px 12px;
  font-size: 12px;
  line-height: 1.3;
  color: var(--ink-2);
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
  overflow: hidden;
}
.name {
  font-weight: 600;
  color: var(--ink);
}
.credit a,
.credit .tour {
  color: var(--accent-ink);
  text-decoration: none;
  text-underline-offset: 2px;
}
.credit a:hover,
.credit .tour:hover {
  text-decoration: underline;
}
.tour {
  border: 1px solid var(--border);
  background: var(--surface);
  border-radius: 999px;
  padding: 1px 9px;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}
.sep {
  color: var(--muted);
}
.spacer {
  flex: 1;
}
.who {
  display: inline-flex;
  gap: 5px;
  align-items: baseline;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
}
.terms,
.repo,
.why,
.tour,
.credit > .sep {
  flex-shrink: 0;
}
@media (max-width: 720px) {
  .credit {
    padding: 2px 10px;
    font-size: 11px;
  }
  .long,
  .name {
    display: none;
  }
}
</style>
