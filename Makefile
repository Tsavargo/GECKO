.PHONY: generate deploy destroy

generate:
	python3 source/generator/generator.py --input application --output output

deploy: generate
	tofu -chdir=opentofu init
	tofu -chdir=opentofu apply

destroy:
	tofu -chdir=opentofu init
	tofu -chdir=opentofu destroy
