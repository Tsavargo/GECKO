.PHONY: generate deploy destroy

# Application directory or zip archive
INPUT ?= application

# Scheduler of the composite functions (persistent, oneshot or forkjoin)
SCHEDULER ?= persistent

generate:
	python3 source/generator/generator.py $(if $(filter %.zip,$(INPUT)),--zip,--input) $(INPUT) --output output

deploy: generate
	tofu -chdir=opentofu init
	tofu -chdir=opentofu apply -var scheduler=$(SCHEDULER)

destroy:
	tofu -chdir=opentofu init
	tofu -chdir=opentofu destroy
