.PHONY: setup run test clean

# Setup: Install dependencies
setup:
	pip install -r requirements.txt
	@echo "✓ Dependencies installed"
	@echo ""
	@echo "Next step: Ensure Instacart CSV files are in data/ directory"
	@echo "Download from: https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis"

# Run: Execute full analysis
run:
	python run_analysis.py
	@echo ""
	@echo "Results saved to:"
	@echo "  - figures/00_executive_dashboard.png"
	@echo "  - reports/weekly_business_review.md"

# Run (quiet mode)
run-quiet:
	python run_analysis.py --quiet

# Run (skip visualizations for speed)
run-fast:
	python run_analysis.py --skip-viz

# Test: Run all unit tests
test:
	pytest tests/ -v

# Clean: Remove generated files
clean:
	rm -f figures/*.png
	rm -f reports/*.md
	@echo "✓ Cleaned generated files"
