.PHONY: init monitor validate analyze report export health test

init:
	python -m research source check

monitor:
	python -m research monitor

validate:
	python -m research validate

analyze:
	python -m research analyze

report:
	python -m research report

export:
	python -m research export --public

health:
	python -m research health

test:
	pytest -q
