"""
Tests for Israeli Companies Gatherer
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import json
import os
import tempfile
import csv
from io import StringIO
import sys

# Add parent directory to path to import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from israeli_companies_gatherer import IsraeliCompaniesGatherer


class TestIsraeliCompaniesGatherer(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        # Note: Individual tests will create their own gatherer instances
        # with mocked Groq clients to avoid API key requirement
        pass
        
    @patch('israeli_companies_gatherer.Groq')
    def test_init(self, mock_groq_class):
        """Test that gatherer initializes correctly"""
        mock_client = Mock()
        mock_groq_class.return_value = mock_client
        
        gatherer = IsraeliCompaniesGatherer()
        self.assertIsNotNone(gatherer)
        self.assertIsNotNone(gatherer.client)
        mock_groq_class.assert_called_once()
    
    @patch('israeli_companies_gatherer.Groq')
    def test_load_categories_from_csv(self, mock_groq_class):
        """Test loading categories from CSV file"""
        mock_client = Mock()
        mock_groq_class.return_value = mock_client
        gatherer = IsraeliCompaniesGatherer()
        
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['category', 'subcategory'])
            writer.writerow(['Magnetics', 'Cryogenic Systems and Components'])
            writer.writerow(['Electronic Components', 'Capacitors'])
            writer.writerow(['Fuel Cycle', 'Detritiation Systems'])
            temp_filename = f.name
        
        try:
            categories = gatherer.load_categories_from_csv(temp_filename)
            
            self.assertEqual(len(categories), 3)
            self.assertEqual(categories[0]['category'], 'Magnetics')
            self.assertEqual(categories[0]['subcategory'], 'Cryogenic Systems and Components')
            self.assertEqual(categories[1]['category'], 'Electronic Components')
            self.assertEqual(categories[1]['subcategory'], 'Capacitors')
        finally:
            os.unlink(temp_filename)
    
    @patch('israeli_companies_gatherer.Groq')
    def test_load_categories_from_csv_file_not_found(self, mock_groq_class):
        """Test loading categories from non-existent file"""
        mock_client = Mock()
        mock_groq_class.return_value = mock_client
        gatherer = IsraeliCompaniesGatherer()
        
        categories = gatherer.load_categories_from_csv('nonexistent_file.csv')
        self.assertEqual(categories, [])
    
    @patch('israeli_companies_gatherer.Groq')
    def test_query_groq_for_israeli_companies_with_json_array(self, mock_groq_class):
        """Test querying Groq API and parsing JSON array response"""
        # Mock the Groq client and response
        mock_client = Mock()
        mock_groq_class.return_value = mock_client
        
        # Create mock streaming response
        mock_chunk1 = Mock()
        mock_chunk1.choices = [Mock()]
        mock_chunk1.choices[0].delta = Mock()
        mock_chunk1.choices[0].delta.content = '[{"companyName": "Test Company", "website": "https://test.com"'
        
        mock_chunk2 = Mock()
        mock_chunk2.choices = [Mock()]
        mock_chunk2.choices[0].delta = Mock()
        mock_chunk2.choices[0].delta.content = ', "headquarters": "Tel Aviv", "yearFounded": "2020"}]'
        
        mock_completion = [mock_chunk1, mock_chunk2]
        mock_client.chat.completions.create.return_value = mock_completion
        
        gatherer = IsraeliCompaniesGatherer()
        companies = gatherer.query_groq_for_israeli_companies("Test Subcategory")
        
        # Verify the response was parsed correctly
        self.assertEqual(len(companies), 1)
        self.assertEqual(companies[0]['companyName'], 'Test Company')
        self.assertEqual(companies[0]['website'], 'https://test.com')
        self.assertEqual(companies[0]['headquarters'], 'Tel Aviv')
        self.assertEqual(companies[0]['yearFounded'], '2020')
    
    @patch('israeli_companies_gatherer.Groq')
    def test_query_groq_for_israeli_companies_with_markdown_code_block(self, mock_groq_class):
        """Test parsing JSON from markdown code block"""
        mock_client = Mock()
        mock_groq_class.return_value = mock_client
        
        # Mock response with JSON in markdown code block
        mock_chunk = Mock()
        mock_chunk.choices = [Mock()]
        mock_chunk.choices[0].delta = Mock()
        mock_chunk.choices[0].delta.content = '```json\n[{"companyName": "Test Corp", "website": "https://testcorp.com"}]\n```'
        
        mock_client.chat.completions.create.return_value = [mock_chunk]
        
        gatherer = IsraeliCompaniesGatherer()
        companies = gatherer.query_groq_for_israeli_companies("Test Subcategory")
        
        self.assertEqual(len(companies), 1)
        self.assertEqual(companies[0]['companyName'], 'Test Corp')
        self.assertEqual(companies[0]['website'], 'https://testcorp.com')
    
    @patch('israeli_companies_gatherer.Groq')
    def test_query_groq_for_israeli_companies_empty_response(self, mock_groq_class):
        """Test handling empty or invalid response"""
        mock_client = Mock()
        mock_groq_class.return_value = mock_client
        
        # Mock empty response
        mock_chunk = Mock()
        mock_chunk.choices = [Mock()]
        mock_chunk.choices[0].delta = Mock()
        mock_chunk.choices[0].delta.content = 'No companies found'
        
        mock_client.chat.completions.create.return_value = [mock_chunk]
        
        gatherer = IsraeliCompaniesGatherer()
        companies = gatherer.query_groq_for_israeli_companies("Test Subcategory")
        
        self.assertEqual(len(companies), 0)
    
    @patch('israeli_companies_gatherer.Groq')
    def test_query_groq_for_israeli_companies_api_error(self, mock_groq_class):
        """Test handling API errors"""
        mock_client = Mock()
        mock_groq_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        gatherer = IsraeliCompaniesGatherer()
        companies = gatherer.query_groq_for_israeli_companies("Test Subcategory")
        
        # Should return empty list on error
        self.assertEqual(len(companies), 0)
    
    @patch('israeli_companies_gatherer.Groq')
    def test_save_israeli_companies_to_csv(self, mock_groq_class):
        """Test saving Israeli companies to CSV"""
        mock_client = Mock()
        mock_groq_class.return_value = mock_client
        gatherer = IsraeliCompaniesGatherer()
        
        companies = [
            {
                'category': 'Magnetics',
                'subcategory': 'Cryogenic Systems',
                'companyName': 'Test Company 1',
                'website': 'https://test1.com',
                'headquarters': 'Tel Aviv',
                'yearFounded': '2020',
                'coreProducts': 'Cooling systems',
                'innovations': 'Advanced cryogenics',
                'notes': 'Test notes'
            },
            {
                'category': 'Electronic Components',
                'subcategory': 'Capacitors',
                'companyName': 'Test Company 2',
                'website': 'https://test2.com',
                'headquarters': 'Haifa',
                'yearFounded': '2018',
                'coreProducts': 'High voltage capacitors',
                'innovations': 'Supercapacitors',
                'notes': 'Another test'
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            temp_filename = f.name
        
        try:
            gatherer.save_israeli_companies_to_csv(companies, temp_filename)
            
            # Verify file was created
            self.assertTrue(os.path.exists(temp_filename))
            
            # Read and verify contents
            with open(temp_filename, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[0]['companyName'], 'Test Company 1')
                self.assertEqual(rows[0]['category'], 'Magnetics')
                self.assertEqual(rows[1]['companyName'], 'Test Company 2')
                self.assertEqual(rows[1]['category'], 'Electronic Components')
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
    
    @patch('israeli_companies_gatherer.Groq')
    def test_save_israeli_companies_to_csv_empty_list(self, mock_groq_class):
        """Test saving empty list of companies"""
        mock_client = Mock()
        mock_groq_class.return_value = mock_client
        gatherer = IsraeliCompaniesGatherer()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            temp_filename = f.name
        
        try:
            gatherer.save_israeli_companies_to_csv([], temp_filename)
            
            # File should exist but be empty (just header)
            if os.path.exists(temp_filename):
                with open(temp_filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Should only have header
                    lines = content.strip().split('\n')
                    self.assertEqual(len(lines), 1)  # Just the header
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
    
    @patch('israeli_companies_gatherer.Groq')
    @patch.object(IsraeliCompaniesGatherer, 'load_categories_from_csv')
    @patch.object(IsraeliCompaniesGatherer, 'query_groq_for_israeli_companies')
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_gather_israeli_companies_for_all_subcategories(self, mock_sleep, mock_query, mock_load, mock_groq_class):
        """Test gathering companies for all subcategories"""
        mock_client = Mock()
        mock_groq_class.return_value = mock_client
        gatherer = IsraeliCompaniesGatherer()
        
        # Setup mocks
        mock_load.return_value = [
            {'category': 'Magnetics', 'subcategory': 'Cryogenic Systems'},
            {'category': 'Electronic Components', 'subcategory': 'Capacitors'},
        ]
        
        mock_query.side_effect = [
            [
                {'companyName': 'Company 1', 'website': 'https://c1.com'},
            ],
            [
                {'companyName': 'Company 2', 'website': 'https://c2.com'},
                {'companyName': 'Company 3', 'website': 'https://c3.com'},
            ]
        ]
        
        companies = gatherer.gather_israeli_companies_for_all_subcategories('test.csv')
        
        # Verify results
        self.assertEqual(len(companies), 3)
        self.assertEqual(companies[0]['category'], 'Magnetics')
        self.assertEqual(companies[0]['subcategory'], 'Cryogenic Systems')
        self.assertEqual(companies[1]['category'], 'Electronic Components')
        self.assertEqual(companies[1]['subcategory'], 'Capacitors')
        
        # Verify methods were called
        mock_load.assert_called_once_with('test.csv')
        self.assertEqual(mock_query.call_count, 2)
    
    @patch('israeli_companies_gatherer.Groq')
    @patch.object(IsraeliCompaniesGatherer, 'load_categories_from_csv')
    @patch.object(IsraeliCompaniesGatherer, 'query_groq_for_israeli_companies')
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_gather_israeli_companies_with_limit(self, mock_sleep, mock_query, mock_load, mock_groq_class):
        """Test gathering companies with limit"""
        mock_client = Mock()
        mock_groq_class.return_value = mock_client
        gatherer = IsraeliCompaniesGatherer()
        
        # Setup mocks
        mock_load.return_value = [
            {'category': 'Magnetics', 'subcategory': 'Cryogenic Systems'},
            {'category': 'Electronic Components', 'subcategory': 'Capacitors'},
            {'category': 'Fuel Cycle', 'subcategory': 'Detritiation Systems'},
        ]
        
        mock_query.return_value = [
            {'companyName': 'Test Company', 'website': 'https://test.com'}
        ]
        
        companies = gatherer.gather_israeli_companies_for_all_subcategories('test.csv', limit=2)
        
        # Verify only first 2 subcategories were processed
        self.assertEqual(len(companies), 2)
        self.assertEqual(mock_query.call_count, 2)
        
        # Verify which subcategories were called
        call_args = [call[0][0] for call in mock_query.call_args_list]
        self.assertIn('Cryogenic Systems', call_args)
        self.assertIn('Capacitors', call_args)
        self.assertNotIn('Detritiation Systems', call_args)
    
    @patch('israeli_companies_gatherer.Groq')
    @patch.object(IsraeliCompaniesGatherer, 'load_categories_from_csv')
    def test_gather_israeli_companies_no_categories(self, mock_load, mock_groq_class):
        """Test gathering when no categories are found"""
        mock_client = Mock()
        mock_groq_class.return_value = mock_client
        gatherer = IsraeliCompaniesGatherer()
        
        mock_load.return_value = []
        
        companies = gatherer.gather_israeli_companies_for_all_subcategories('test.csv')
        
        self.assertEqual(companies, [])


if __name__ == '__main__':
    unittest.main()

