<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { REPO_URL } from '@/api/client'

const AUTHOR_URL = 'https://saro-saravanan.github.io'
const TERMS_MD = `${REPO_URL}/blob/main/docs/terms.md`
const LICENSE_URL = `${REPO_URL}/blob/main/LICENSE`
const INVENTORY_URL = `${REPO_URL}/blob/main/docs/data-inventory.md`
</script>

<template>
  <article class="terms">
    <header>
      <h2>Terms of use</h2>
      <p class="lede">
        AI Workforce Sim is an open-source scenario model built by
        <a :href="AUTHOR_URL" target="_blank" rel="noopener author">Saro Saravanan</a>. By using the
        public page, the code, the data tables or any output of the model you accept the terms
        below. They are written in plain language on purpose; where they use a legal term it
        carries its ordinary legal meaning. The canonical text is
        <a :href="TERMS_MD" target="_blank" rel="noopener">docs/terms.md</a> in the repository.
      </p>
    </header>

    <section class="card">
      <h3>1. What this is, and what it is not</h3>
      <p>
        The model is a structured set of mechanisms with stated parameters. It produces scenarios:
        differences between a world with continuing AI progress and a world in which frontier AI
        stopped improving in 2023. Its ranges are ranges over its own assumptions. They are not
        forecasts, not forecast intervals, and not statements about what will happen to any
        person, occupation, company, region or economy.
      </p>
    </section>

    <section class="card">
      <h3>2. No advice</h3>
      <p>
        Nothing on the page, in the briefs, in the documents or in the chat layer is financial,
        investment, career, employment, legal, tax or policy advice. Do not make decisions about
        jobs, hiring, training, investment, legislation or anything else on the strength of the
        model alone. Consult a qualified professional for advice about your situation.
      </p>
    </section>

    <section class="card">
      <h3>3. No warranty</h3>
      <p>
        The software, the data tables, the documents and every output are provided "as is" and
        "as available", without warranty of any kind, express or implied, including any warranty
        of accuracy, completeness, fitness for a particular purpose, merchantability or
        non-infringement. The author does not warrant that the model is correct, that the data
        are current, that the page will be available, or that errors will be corrected. Known
        limits are listed on the
        <RouterLink :to="{ path: '/about', query: $route.query }">About</RouterLink> page and in
        the risks document; they are not the only limits.
      </p>
    </section>

    <section class="card">
      <h3>4. Limitation of liability</h3>
      <p>
        To the fullest extent permitted by law, the author and contributors are not liable for
        any loss or damage of any kind (direct, indirect, incidental, consequential, special or
        exemplary, including lost profits, lost data or business interruption) arising from or
        connected with the use of, or inability to use, the software, the page, the data or any
        output, even if advised of the possibility of such loss. Where liability cannot be
        excluded, it is limited to the greatest extent the law allows. Some jurisdictions do not
        allow some of these exclusions, so parts of this section may not apply to you.
      </p>
    </section>

    <section class="card">
      <h3>5. Data and third-party sources</h3>
      <p>
        The model reads published data from public sources (among them BLS OEWS, BEA input-output
        tables, O*NET, METR, the Census Bureau's Business Trends and Outlook Survey, Challenger,
        Gray &amp; Christmas and Natural Earth) and reproduces some of them in derived form. Each
        source keeps its own licence and terms, listed in the
        <a :href="INVENTORY_URL" target="_blank" rel="noopener">data inventory</a>. Some inputs
        are labelled fixtures or the authors' estimates; the run's data flags say which. Named
        forecasts on the scoreboard are quoted for comparison and remain the work of their
        authors.
      </p>
    </section>

    <section class="card">
      <h3>6. Open source, licence and contributions</h3>
      <p>
        The code, the scenario files and the documents are released under the
        <a :href="LICENSE_URL" target="_blank" rel="noopener">MIT License</a>. You may use, copy,
        modify and redistribute them under that licence, which also carries the no-warranty and
        no-liability terms above. Contributions through the
        <a :href="REPO_URL" target="_blank" rel="noopener">repository</a> are welcome and are
        accepted under the same licence; by contributing you confirm you have the right to
        license your contribution. Please credit the project and its author when you build on it.
      </p>
    </section>

    <section class="card">
      <h3>7. The chat layer and privacy</h3>
      <p>
        The public page is a static site: it keeps no accounts and sends nothing you type
        anywhere, except what your browser sends to the host that serves the page. The Ask tab
        exists only when someone runs the API server with a model key; questions typed there are
        sent to that model provider under the provider's own terms, and the operator of that
        server, not the author of this project, is responsible for that deployment.
      </p>
    </section>

    <section class="card">
      <h3>8. Changes</h3>
      <p>
        These terms may change as the project changes. The version in the repository at the time
        you use the project applies. <span class="muted">Last updated: September 2026.</span>
      </p>
    </section>
  </article>
</template>

<style scoped>
.terms {
  max-width: 760px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-bottom: 24px;
  font-size: 15px;
  line-height: 1.5;
}
.terms h2 {
  font-size: 22px;
  margin-bottom: 6px;
}
.terms h3 {
  font-size: 16px;
  margin-bottom: 8px;
}
.lede {
  margin: 0;
  color: var(--ink-2);
  font-size: 16px;
}
.card {
  padding: 14px 18px;
}
.card p {
  margin: 0;
}
.terms a {
  color: var(--accent-ink);
}
</style>
