# 🛠️ Python Refactor Advisor Tool

**Refactor Advisor** is a Python-based automated code analysis tool that scans your project, splits code into chunks, and uses Amazon Q (via CLI) to suggest potential refactorings. It helps developers quickly identify code smells, anti-patterns, and improvement opportunities based on principles like DRY, SOLID, and readability.

---

## 🚀 Features

- ✅ Analyzes all `.py` files in a directory recursively  
- ✅ Splits code into manageable chunks  
- ✅ Uses Amazon Q CLI to generate refactoring advice  
- ✅ Provides fallback analysis when Amazon Q is unavailable  
- ✅ Highlights code smells, design issues, and improvement suggestions  
- ✅ Color-coded terminal output for easy reading  
- ✅ Optionally saves reports to a directory  

---

## 📦 Requirements

- Python 3.7+
- Amazon Q CLI or AWS CLI v2 (with `q` feature enabled)
- Optional: `amazon-q` CLI installed if `aws q` is unavailable

---

## 📂 Directory Structure

project/
├── refactor_advisor.py # Main script

├── README.md # This file

### Basic command:

## Just run the Script
`Python refactor_advisor.py`
```bash
python refactor_advisor.py --project-path ./your_project
```
With output directory for reports:

```bash
python refactor_advisor.py --project-path ./your_project --output-path ./refactor_reports
```

Optional arguments:

--project-path: Path to the target Python project (required)

--output-path: Where to save analysis results (optional)

--chunk-size: Number of lines per chunk (default: 100)
<p align="center">
  <img src="https://github.com/user-attachments/assets/541c9485-496c-4255-bf5d-e625635a6915" alt="image_3" width="45%" />
  &nbsp;
  <img src="https://github.com/user-attachments/assets/1be2dc62-130b-4e10-84e4-be061f990fe5" alt="image2" width="55%" />
</p>
