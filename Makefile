.PHONY: demo setup data sim api web test lint

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
