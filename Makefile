.PHONY: format
format: ## Format the code
	uv run ruff format
	uv run ruff check --fix --fix-only

.PHONY: typecheck
typecheck:
	@# PYRIGHT_PYTHON_IGNORE_WARNINGS avoids the overhead of making a request to github on every invocation
	PYRIGHT_PYTHON_IGNORE_WARNINGS=1 uv run pyright
