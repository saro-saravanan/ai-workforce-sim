.PHONY: demo setup data sim api web test lint static chat

# One command from a clean clone: install, build data, run baseline, start API and web.
demo: setup data run
	@echo "Starting API on :8000 and web on :5173"
	@(uv run uvicorn aiwsim_api.app:app --port 8000 --reload &) && cd web && pnpm dev

setup:
	uv sync --all-packages
	cd web && pnpm install

data:
	uv run aiwsim data build

run:
	uv run aiwsim run --scenario scenarios/baseline.json --out data/cache/baseline.json

test:
	uv run pytest -q
	cd web && pnpm test --run

lint:
	uv run ruff check sim api
	cd web && pnpm lint

static:      ## serverless demo bundle (contracts §18); then: cd web && VITE_STATIC=1 pnpm build
	uv run python -m aiwsim_api.export_static --out web/public/static --draws 200

chat:        ## terminal chat against the last baseline run (needs ANTHROPIC_API_KEY); make chat Q="what is surprising?"
	cd api && uv run python -m aiwsim_api.chat "$(Q)" --mode insights
