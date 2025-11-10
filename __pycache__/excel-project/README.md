# Excel Project

This project is designed to create a new Excel file that replicates the structure and columns of an existing template Excel workbook.

## Project Structure

- `src/data/templates/workbook.xlsx`: This file is a template Excel workbook that contains the original columns and structure that will be replicated in the new Excel file.
- `src/data/output`: This directory will contain the newly created Excel file with the same columns as the original template.
- `package.json`: This file is the configuration file for npm. It lists the dependencies and scripts for the project.

## Usage

1. Place your template Excel file in the `src/data/templates` directory.
2. Run the script to generate a new Excel file in the `src/data/output` directory.
3. The new Excel file will have the same columns as the template.

## Dependencies

- pandas
- openpyxl

## License

This project is licensed under the MIT License.