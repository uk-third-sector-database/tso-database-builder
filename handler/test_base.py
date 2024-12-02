import pytest

from .base import sort_csv_by_field

import csv
import tempfile
import os

# Define a fixture to create a sample CSV file
@pytest.fixture
def sample_csv():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as temp_file:
        data = [
            ["id", "name", "date"],
            [1, "Alice", '30/01/1999'],
            [2, "Bob", ''],
            [3, "Charlie", '25/12/2000'],
        ]
        writer = csv.writer(temp_file)
        writer.writerows(data)
        temp_file_path = temp_file.name  # Get the file path
    
    # Provide the file path to the test
    yield temp_file_path

    # Cleanup the temporary file after the test
    #os.remove(temp_file_path)

# Test using the fixture
def test_function_with_csv(sample_csv):
    # Function to test
    def read_csv(file_path):
        with open(file_path, "r") as f:
            return [row for row in csv.reader(f)]
    
    print(sample_csv)
    # testing this function
    sort_csv_by_field(sample_csv,'date')
    
    # a new file called sample_csv.replace('.csv','.notsorted.csv') should have been created

    assert os.path.exists(sample_csv.replace('.csv','.notsorted.csv'))
    assert os.path.exists(sample_csv) # a file with original filename should have been created

    rows = read_csv(sample_csv)

    # Assert the content is as expected
    assert [row[1] for row in rows] == ['name', "Bob", "Charlie", "Alice"]

    
    assert [row[2] for row in rows] == ['date', "", "25/12/2000", "30/01/1999"]




