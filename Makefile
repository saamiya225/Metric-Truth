# SOURCE = synthetic (default) | online_retail_ii
SOURCE ?= synthetic
export DBT_DUCKDB_PATH ?= warehouse_$(SOURCE).duckdb
VARS = --vars '{source_system: $(SOURCE)}'

.PHONY: setup data prepare build test conflict docs all fixture clean

setup:
	pip install -r requirements.txt

# synthetic data
data:
	python scripts/generate_data.py

# real data: make prepare INPUT=~/Downloads/online_retail_II.xlsx
prepare:
	python scripts/prepare_online_retail.py --input $(INPUT)

build:
	dbt seed $(VARS) && dbt run $(VARS)

test:
	dbt test $(VARS)

conflict:
	python scripts/show_conflict.py --source $(SOURCE)

docs:
	dbt docs generate $(VARS) && dbt docs serve

# synthetic end-to-end
all: data build test conflict

# real-data adapter check using the tiny hand-made file (runs in CI, no download)
fixture:
	python scripts/prepare_online_retail.py --input tests/fixtures/online_retail_ii_sample.csv
	DBT_DUCKDB_PATH=warehouse_fixture.duckdb dbt seed --vars '{source_system: online_retail_ii}'
	DBT_DUCKDB_PATH=warehouse_fixture.duckdb dbt run  --vars '{source_system: online_retail_ii}'
	DBT_DUCKDB_PATH=warehouse_fixture.duckdb dbt test --vars '{source_system: online_retail_ii}'
	python scripts/verify_fixture.py
	rm -f data/raw/online_retail_ii.csv

clean:
	rm -rf target logs *.duckdb data/raw/*.csv
