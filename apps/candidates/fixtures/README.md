# Filter Data

This directory contains comprehensive filter data for the Workfina application.

## File: filter_data.json

Contains complete data for all filter categories:

- **Religions**: 10 major religions in India
- **Departments**: 80+ job departments/roles
- **Languages**: 32+ languages including all Indian languages
- **Skills**: 110+ technical and professional skills
- **Education Levels**: 30+ education qualifications
- **States**: All 36 states and union territories of India
- **Cities**: 700+ major cities across India

## Loading Data

To load this data into the database, run:

```bash
# From the project root, activate virtual environment
source venv/bin/activate

# Navigate to server directory
cd venv/bin/server

# Run the management command
python manage.py load_filter_data
```

## Features

- **Idempotent**: Running the command multiple times won't create duplicates
- **Hierarchical**: Cities are linked to States, States to Country
- **Comprehensive**: Covers all major Indian states and cities
- **Extensible**: Easy to add more data by editing the JSON file

## Data Structure

### States and Cities
States and cities follow a hierarchical structure:
- Country (India) → State → City
- Cities are linked to their parent state
- Unique slugs prevent duplicates

### Other Categories
All other filter options (religions, departments, etc.) are flat structures with:
- Unique names and slugs
- Display order for consistent sorting
- Active/inactive flags

## Updating Data

To add more data:

1. Edit `filter_data.json`
2. Add new entries to the appropriate array
3. Run `python manage.py load_filter_data`
4. Existing entries won't be duplicated

## Notes

- The command uses `get_or_create` to prevent duplicates
- Slug generation handles special characters and spaces
- All data is marked as active by default
- Display order is preserved from the JSON file
