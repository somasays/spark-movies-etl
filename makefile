SHELL=/bin/bash

init:
	make clean
	python3.7 -m venv movies_venv
	. movies_venv/bin/activate && pip install --upgrade pip setuptools \
	&& pip install -r requirements.txt \
	&& pip install -e . \
	&& make build_spark_dependencies

clean:
	rm -rf movies_venv
	find . -name '__pycache__' | xargs rm -rf
	find . -name '*pytest_cache' | xargs rm -rf

build_spark_dependencies:
	zip -r moviesetl.zip moviesetl && \
	cd ./movies_venv/lib/python3.7/site-packages && \
	zip -r packages.zip . && \
	mv packages.zip ../../../../packages.zip

run:
	. movies_venv/bin/activate && \
    PYSPARK_PYTHON=/home/movies/movies_venv/bin/python spark-submit \
    --master local[*] \
    --conf spark.sql.shuffle.partitions=10 \
    --conf spark.executor.instances=3 \
    --conf spark.executor.cores=1 \
    --conf spark.executor.memory=1g \
    moviesetl/main.py \
    --task ${task}

test:
	. movies_venv/bin/activate && python -m pytest tests

lint:
	. movies_venv/bin/activate && flake8 moviesetl/ tests/
