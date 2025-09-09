#!/usr/bin/env python3
"""
Tests for the clean_name_for_search function to validate parenthetical content and suffix removal.
"""

import sys
import os

# Add the current directory to the path so we can import the main module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from AppleMusicXmlToLidarr import clean_name_for_search


def test_clean_name_for_search():
    """Test the clean_name_for_search function with various inputs."""
    
    test_cases = [
        # Test parenthetical content removal
        ("Abbey Road (Remastered)", "Abbey Road"),
        ("Greatest Hits (Deluxe Edition)", "Greatest Hits"),
        ("Live Album (Live)", "Live Album"),
        ("Song Title (feat. Artist)", "Song Title"),
        ("Album (2023 Reissue)", "Album"),
        
        # Test suffix removal
        ("Love Song - Single", "Love Song"),
        ("EP Title - EP", "EP Title"),
        ("love song - single", "love song"),  # lowercase
        ("ep title - ep", "ep title"),  # lowercase
        
        # Test combined removal (parentheses + suffix)
        ("Hit Song (Radio Edit) - Single", "Hit Song"),
        ("EP Name (Deluxe) - EP", "EP Name"),
        
        # Test edge cases
        ("", ""),
        (None, None),
        ("Simple Title", "Simple Title"),  # no changes needed
        ("Title with (brackets) in middle", "Title with in middle"),
        ("Multiple (First) (Second) Parentheses", "Multiple Parentheses"),
        
        # Test whitespace handling
        ("  Spaced Title (Edition)  ", "Spaced Title"),
        ("Title ( With Spaces ) - Single", "Title"),
        
        # Test nested parentheses (should remove outer ones)
        ("Title (Contains (Nested) Text)", "Title"),
    ]
    
    failed_tests = []
    
    for input_name, expected_output in test_cases:
        try:
            actual_output = clean_name_for_search(input_name)
            if actual_output != expected_output:
                failed_tests.append((input_name, expected_output, actual_output))
        except Exception as e:
            failed_tests.append((input_name, expected_output, f"Exception: {e}"))
    
    if failed_tests:
        print("FAILED TESTS:")
        for input_val, expected, actual in failed_tests:
            print(f"  Input: {repr(input_val)}")
            print(f"  Expected: {repr(expected)}")
            print(f"  Actual: {repr(actual)}")
            print()
        return False
    else:
        print(f"All {len(test_cases)} tests passed!")
        return True


def test_integration_scenarios():
    """Test realistic scenarios that might be encountered in Apple Music libraries."""
    
    # Realistic album names from Apple Music
    realistic_cases = [
        ("1989 (Taylor's Version)", "1989"),
        ("Sgt. Pepper's Lonely Hearts Club Band (Remastered)", "Sgt. Pepper's Lonely Hearts Club Band"),
        ("The Dark Side of the Moon (Remastered)", "The Dark Side of the Moon"),
        ("Thriller (Special Edition)", "Thriller"),
        ("Born to Run (Remastered) - Single", "Born to Run"),
        ("Christmas Songs - EP", "Christmas Songs"),
        ("Greatest Hits (Deluxe Edition) - EP", "Greatest Hits"),
    ]
    
    failed_tests = []
    
    for input_name, expected_output in realistic_cases:
        actual_output = clean_name_for_search(input_name)
        if actual_output != expected_output:
            failed_tests.append((input_name, expected_output, actual_output))
    
    if failed_tests:
        print("FAILED INTEGRATION TESTS:")
        for input_val, expected, actual in failed_tests:
            print(f"  Input: {repr(input_val)}")
            print(f"  Expected: {repr(expected)}")
            print(f"  Actual: {repr(actual)}")
            print()
        return False
    else:
        print(f"All {len(realistic_cases)} integration tests passed!")
        return True


if __name__ == "__main__":
    print("Testing clean_name_for_search function...")
    print("=" * 50)
    
    success1 = test_clean_name_for_search()
    print()
    success2 = test_integration_scenarios()
    
    if success1 and success2:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1)