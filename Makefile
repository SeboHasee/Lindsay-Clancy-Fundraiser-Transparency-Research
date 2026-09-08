.PHONY: init setup monitor validate analyze report seo-validate export health status test

init:
	python -m research source check

setup:
	python -m research setup

monitor:
	python -m research monitor

validate:
	python -m research validate

analyze:
	python -m research analyze

report:
	python -m research report

seo-validate:
	python -m research seo-validate

export:
	python -m research export --public

health:
	python -m research health

status:
	python -m research status

test:
	pytest -q
