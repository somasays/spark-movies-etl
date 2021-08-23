SHELL=/bin/bash

help:
	@echo  'Options:'
	@echo  '  setup           - Set up local virtual env for development.'
	@echo  '  build           - Build and package the application and its dependencies,'
	@echo  '                    to be distributed through spark-submit.'
	@echo  '  test            - Run unit and integration tests.'
	@echo  '  pre-commit      - Run checks (code formatter, linter, type checker)'
	@echo  '  run-local       - Run a task locally. Example usage:'
	@echo  '                    make run-local task=ingest execution-date=2021-01-01'
	@echo  '                    make run-local task=transform execution-date=2021-01-01'
	@echo  '  run-cluster     - Run a task on a cluster.'
	@echo  '  clean           - Clean auxiliary files.'

setup:
	pip install poetry
	poetry config virtualenvs.in-project true --local
	poetry install

build:
	# Can't use `poetry build`: we need to package the whole venv with all dependencies.
	rm -rf deps && \
	mkdir deps && \
	python -m venv .venv_build && \
	source .venv_build/bin/activate && \
	pip install venv-pack==0.2.0 . && \
	venv-pack -o deps/venv_build.tar.gz && \
	cp spark_movies_etl/main.py deps && \
	rm -r .venv_build

test:
	poetry run pytest --cov -vvvv --showlocals tests --disable-warnings

pre-commit:
	poetry run pre-commit run --all-files

run-local:
	poetry run spark-submit \
	--master local[*] \
	--packages org.apache.spark:spark-avro_2.12:3.1.2,io.delta:delta-core_2.12:1.0.0 \
	--conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
	--conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
	spark_movies_etl/main.py \
	--task ${task} \
	--execution-date $(execution-date)

run-cluster:
	spark-submit \
	--master yarn \
	--deploy-mode cluster \
	--archives s3a://movies-binaries/spark-movies-etl/latest/venv_build.tar.gz#env \
	--packages org.apache.spark:spark-avro_2.12:3.1.2,io.delta:delta-core_2.12:1.0.0 \
	--conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
	--conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
	--conf spark.yarn.appMasterEnv.PYSPARK_PYTHON=./env/bin/python \
	s3a://movies-binaries/spark-movies-etl/latest/main.py \
	--task ${task} \
	--execution-date $(execution-date)

clean:
	rm -rf deps/ .pytest_cache .mypy_cache spark_movies_etl.egg-info *.xml .coverage
