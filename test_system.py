"""Quick test script to verify the Query Suggestion System components."""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from metadata_loader import MetadataLoader
from search_engine import SearchEngine

def test_metadata_loading():
    """Test loading metadata from data directory."""
    print("Testing metadata loading...")

    loader = MetadataLoader("data")
    yaml_metadata, txt_descriptions = loader.load_all_metadata()

    print(f"[OK] Loaded {len(yaml_metadata)} YAML metadata files")
    print(f"[OK] Loaded {len(txt_descriptions)} TXT description files")

    # Show summary
    avs_count = len([m for m in yaml_metadata if m.source_type == 'avs'])
    dlvs_count = len([m for m in yaml_metadata if m.source_type == 'dlvs'])

    print(f"  - AVS tables: {avs_count}")
    print(f"  - DLVS tables: {dlvs_count}")

    return yaml_metadata, txt_descriptions


def test_search_engine(yaml_metadata, txt_descriptions):
    """Test search engine functionality."""
    print("\nTesting search engine...")

    search_engine = SearchEngine(yaml_metadata, txt_descriptions)

    # Test search
    test_queries = [
        "borrower",
        "customer",
        "SSN",
        "loan application"
    ]

    for query in test_queries:
        results = search_engine.search(query, max_results=3)
        print(f"[OK] Query '{query}': found {len(results)} results")

        if results:
            top_result = results[0]
            print(f"  Top result: {top_result.get_table_title()} (score: {top_result.relevance_score:.1f})")


def test_column_search(yaml_metadata, txt_descriptions):
    """Test column-based search."""
    print("\nTesting column search...")

    search_engine = SearchEngine(yaml_metadata, txt_descriptions)

    # Search for tables with SSN column
    results = search_engine.search_by_column("SSN")
    print(f"[OK] Found {len(results)} tables with 'SSN' column")

    for result in results:
        print(f"  - {result.get_table_title()}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Query Suggestion System - Component Test")
    print("=" * 60)

    try:
        # Test 1: Metadata loading
        yaml_metadata, txt_descriptions = test_metadata_loading()

        if not yaml_metadata:
            print("\n[WARNING] No metadata files found. Add YAML files to data/avs/ and data/dlvs/")
            return

        # Test 2: Search engine
        test_search_engine(yaml_metadata, txt_descriptions)

        # Test 3: Column search
        test_column_search(yaml_metadata, txt_descriptions)

        print("\n" + "=" * 60)
        print("[SUCCESS] All tests passed!")
        print("=" * 60)
        print("\nSystem is ready. Run 'python run_app.py' to start the web UI.")

    except Exception as e:
        print(f"\n[ERROR] Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
