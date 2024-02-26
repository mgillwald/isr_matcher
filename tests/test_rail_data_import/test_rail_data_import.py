import pytest
from isr_matcher.data_handlers.rail_data_import import RailDataImport

# TEST DATA
TRACK = [3010]
BOUNDARY_ISR = ['3340000 5645000 3345000 5645000 3345000 5650000 3340000 5650000 3340000 5645000']


@pytest.mark.parametrize("filter_name, args", [("EQUALS_TRACK", TRACK), ("BOUNDARY", BOUNDARY_ISR)])
def test_isr_import(filter_name, args):
    """Test import of railway data from ISR"""
    # importer
    rdi = RailDataImport()

    # query
    response = rdi.query(filter_name=filter_name, args=args, enhance_kilometrage=True)

    # assert response contains elements
    assert len(response) > 0


if __name__ == '__main__':
    test_isr_import()
