"""lobmp tests

Plese remember to follow the basic four steps:
1. Arrange
2. Act
3. Assert
4. Cleanup
"""

from pathlib import Path

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from lobmp import (
    find_market_by_price_lines,
    flatten_map_entry,
    flatten_market_by_price,
    run,
    run_l10,
)
from lobmp.definitions.fids import known_fids, supplement
from lobmp.logger import activate_logger, set_logger_level

activate_logger()
set_logger_level("DEBUG")


def generate_market_by_price_message(
    ticker: str,
    timestamp_iso_8601: str,
    gmt_offset: str,
    is_refresh: bool,
    message_number: int,
    summary_values: dict[str, list[str]] | None,
    map_entries: dict[tuple, dict[str, list[str]]] | None,
) -> str:
    message = f"{ticker},Market By Price,{timestamp_iso_8601},{gmt_offset},Raw,"
    if is_refresh:
        message += "REFRESH,,,,,3240,0,"
    else:
        message += "UPDATE,UNSPECIFIED,,,,3240,,"
    message += f"{message_number},0\n"
    message += generate_summary(summary_values)
    message += generate_map_entries(map_entries)
    return message


def generate_map_entries(map_entries: dict[tuple, dict[str, list[str]]] | None) -> str:
    """Generate a list of map entries

    Args:
        map_entries (dict[tuple, dict[str, list[str]]] | None): data for the generated map entries

    Returns:
        str: map entries built
    """
    message = ""
    if map_entries is not None:
        for key, value in map_entries.items():
            message += generate_map_entry(key[0], key[1], value)
    return message


def generate_map_entry(
    map_entry_type: str | None, map_entry_key: str | None, values: dict[str, list[str]] | None
) -> str:
    message = ""
    if values is not None:
        message += f",,,,MapEntry,,{map_entry_type},,,,,,{map_entry_key},{len(values.keys())}\n"
        if isinstance(values, dict):
            if len(values.keys()) > 0:
                for map_entry_key, value in values.items():
                    message += generate_field(
                        map_entry_key, value[0], value[1] if len(value) > 1 else ""
                    )
    return message


def generate_summary(
    values: dict[str, list[str]] | None,  # For example {"CURRENCY": ["999", "EUR"]} or None
) -> str:
    message = ""
    if isinstance(values, dict):
        message = f",,,,Summary,,,,,,,,,{len(values.keys())}\n"
        if len(values) > 0:
            for key, value in values.items():
                message += generate_field(key, value[0], value[1] if len(value) > 1 else "")
    return message


def generate_field(field_name: str, first_value: str, second_value: str = "") -> str:
    message = ""
    if field_name in known_fids:
        fid_code = known_fids[field_name][0]
        has_second_value = known_fids[field_name][1]
        if has_second_value and second_value == "":
            raise ValueError(
                f"The FID {field_name} needs to have two values but only one was present."
            )
        message += f",,,,FID,{fid_code},,{field_name},{first_value},{second_value}\n"
    else:
        raise ValueError("Unkown field name.")
    return message


@pytest.mark.parametrize("num_messages", [0, 100])
def test_find_market_by_price_lines_only_header(tmp_path: Path, num_messages: int) -> None:
    file = tmp_path / "test_file.csv"
    file.touch()
    test_messages = ""
    for num_message in range(num_messages):
        test_messages += generate_market_by_price_message(
            "TESTTICKER.MC",
            "2020-01-11T00:00:00.000000000Z",
            "+0",
            True,
            num_message,
            None,  # No summary line
            None,  # No map entries
        )
    file.write_text(test_messages)
    lines = find_market_by_price_lines(file)
    assert lines == [
        _ for _ in range(num_messages)
    ]  # Should find the headers in the correct places


@pytest.mark.parametrize("num_messages", [0, 100])
def test_find_market_by_price_lines_header_and_empty_summary(
    tmp_path: Path, num_messages: int
) -> None:
    file = tmp_path / "test_file.csv"
    file.touch()
    test_messages = ""
    for num_message in range(num_messages):
        test_messages += generate_market_by_price_message(
            "TESTTICKER.MC",
            "2020-01-11T00:00:00.000000000Z",
            "+0",
            True,
            num_message,
            {},  # Empty summary of no elements i.e. ",,,,Summary,,,,,,,,,0"
            None,  # No map entries
        )
    file.write_text(test_messages)
    lines = find_market_by_price_lines(file)
    assert lines == [
        _ for _ in range(0, num_messages * 2, 2)
    ]  # Should find the headers in the correct places


@pytest.mark.parametrize("num_messages", [0, 100])
def test_find_market_by_price_lines_header_and_summary(tmp_path: Path, num_messages: int) -> None:
    file = tmp_path / "test_file.csv"
    file.touch()
    test_messages = ""
    for num_message in range(num_messages):
        test_messages += generate_market_by_price_message(
            "TESTTICKER.MC",
            "2020-01-11T00:00:00.000000000Z",
            "+0",
            True,
            num_message,
            {"PROD_PERM": ["3240"], "DSPLY_NAME": ["TEST SA"], "CURRENCY": ["999", "TESTCOIN"]},
            None,
        )
    file.write_text(test_messages)
    lines = find_market_by_price_lines(file)

    # File contains a Market By Price header every 5 lines
    assert lines == [
        _ for _ in range(0, num_messages * 5, 5)
    ]  # Should find the headers in the correct places


@pytest.mark.parametrize("num_messages", [0, 1, 100])
@pytest.mark.parametrize("num_map_entries", [0, 1, 100])
def test_find_market_by_price_lines_header_and_summary_and_map_entries(
    tmp_path: Path, num_messages: int, num_map_entries: int
) -> None:
    file = tmp_path / "test_file.csv"
    file.touch()
    test_messages = ""
    for num_message in range(num_messages):
        random_map_entries = {}
        for index in range(num_map_entries):
            random_map_entries[("UPDATE", f"{index}.000000_B")] = {
                "BID_TIME": ["06:31:00.000000000"],
                "ORDER_PRC": ["100.0"],
                "ORDER_SIDE": ["1", "BID"],
                "NO_ORD": ["9"],
            }

        test_messages += generate_market_by_price_message(
            "TESTTICKER.MC",
            "2020-01-11T00:00:00.000000000Z",
            "+0",
            True,
            num_message,
            {"PROD_PERM": ["3240"], "DSPLY_NAME": ["TESTING SA"], "CURRENCY": ["999", "TESTCOIN"]},
            random_map_entries,
        )
    file.write_text(test_messages)
    lines = find_market_by_price_lines(file)

    assert lines == [
        _ for _ in range(0, num_messages * (5 + num_map_entries * 5), 5 + num_map_entries * 5)
    ]  # Should find the headers in the correct places


@pytest.mark.parametrize("num_map_entries", [0, 1, 100])
def test_flatten_map_entry_update_ok(num_map_entries):
    test_string = ""
    for _ in range(num_map_entries):
        test_string += generate_map_entry(
            "UPDATE",
            "1.000000_B",
            {
                "BID_TIME": ["06:31:00.000000000"],
                "ORDER_PRC": ["1.0"],
                "ORDER_SIDE": ["1", "BID"],
                "NO_ORD": ["9"],
                "ACC_SIZE": ["203"],
                "LV_TIM_MS": ["23460020"],
                "LV_DATE": ["2023-08-07"],
                "LV_TIM_NS": ["06:31:00.020570000"],
            },
        )
    result = flatten_map_entry(test_string)
    if num_map_entries == 0:
        assert result == [[]]
    elif num_map_entries > 0:
        expected = [
            [
                "ACC_SIZE",
                "BID_TIME",
                "LV_DATE",
                "LV_TIM_MS",
                "LV_TIM_NS",
                "MAP_ENTRY_KEY",
                "MAP_ENTRY_TYPE",
                "NO_ORD",
                "ORDER_PRC",
                "ORDER_SIDE",
            ]
        ]
        for _ in range(num_map_entries):
            expected.append(
                [
                    "203",
                    "06:31:00.000000000",
                    "2023-08-07",
                    "23460020",
                    "06:31:00.020570000",
                    "1.000000_B",
                    "UPDATE",
                    "9",
                    "1.0",
                    "BID",
                ]
            )
        assert result == expected


@pytest.mark.parametrize("num_map_entries", [0, 1, 100])
def test_flatten_map_entry_add_ok(num_map_entries):
    test_string = ""
    for _ in range(num_map_entries):
        test_string += generate_map_entry(
            "ADD",
            "1.000000_B",
            {
                "BID_TIME": ["06:31:00.000000000"],
                "ORDER_PRC": ["1.0"],
                "ORDER_SIDE": ["1", "BID"],
                "NO_ORD": ["9"],
                "ACC_SIZE": ["203"],
                "LV_TIM_MS": ["23460020"],
                "LV_DATE": ["2023-08-07"],
                "LV_TIM_NS": ["06:31:00.020570000"],
            },
        )
    result = flatten_map_entry(test_string)
    if num_map_entries == 0:
        assert result == [[]]
    elif num_map_entries > 0:
        expected = [
            [
                "ACC_SIZE",
                "BID_TIME",
                "LV_DATE",
                "LV_TIM_MS",
                "LV_TIM_NS",
                "MAP_ENTRY_KEY",
                "MAP_ENTRY_TYPE",
                "NO_ORD",
                "ORDER_PRC",
                "ORDER_SIDE",
            ]
        ]
        for _ in range(num_map_entries):
            expected.append(
                [
                    "203",
                    "06:31:00.000000000",
                    "2023-08-07",
                    "23460020",
                    "06:31:00.020570000",
                    "1.000000_B",
                    "ADD",
                    "9",
                    "1.0",
                    "BID",
                ]
            )
        assert result == expected


@pytest.mark.parametrize("num_map_entries", [0, 1, 100])
def test_flatten_map_entry_delete_ok(num_map_entries):
    test_string = ""
    for _ in range(num_map_entries):
        test_string += generate_map_entry("DELETE", "1.000000_B", {})
    result = flatten_map_entry(test_string)
    if num_map_entries == 0:
        assert result == [[]]
    elif num_map_entries > 0:
        expected = [
            [
                "MAP_ENTRY_KEY",
                "MAP_ENTRY_TYPE",
            ]
        ]
        for _ in range(num_map_entries):
            expected.append(["1.000000_B", "DELETE"])
        assert result == expected


@pytest.mark.parametrize("num_messages", [0, 1, 100, 500])  # Number of Market By Price messages
@pytest.mark.parametrize(
    "num_map_entries", [0, 1, 50]
)  # Number of MapEntry messages per Market By Price message
def test_run_ok(tmp_path: Path, num_messages: int, num_map_entries: int) -> None:
    file = tmp_path / "test_file.csv"
    file.touch()
    # Build expected DataFrame
    expected = pl.DataFrame()
    test_messages = ""
    for num_message in range(num_messages):
        random_map_entries = {}
        market_by_price_df = pl.DataFrame()
        for index in range(num_map_entries):
            random_map_entries[("UPDATE", f"{index}.000000_B")] = {
                "BID_TIME": ["06:31:00.000000000"],
                "ORDER_PRC": ["100.0"],
                "ORDER_SIDE": ["1", "BID"],
                "NO_ORD": ["9"],
            }

        for key, map_entry in random_map_entries.items():
            row = pl.DataFrame({k: v[-1] for k, v in map_entry.items()})
            row = row.with_columns(pl.lit(key[0]).alias("MAP_ENTRY_TYPE"))
            row = row.with_columns(pl.lit(key[1]).alias("MAP_ENTRY_KEY"))
            market_by_price_df = pl.concat([market_by_price_df, row], how="vertical")

        test_messages += generate_market_by_price_message(
            "TESTTICKER.MC",
            "2020-01-11T00:00:00.000000000Z",
            "+0",
            True,
            num_message,
            {"PROD_PERM": ["3240"], "DSPLY_NAME": ["TESTING SA"], "CURRENCY": ["999", "TESTCOIN"]},
            random_map_entries,
        )
        market_by_price_df = market_by_price_df.with_columns(
            pl.lit("REFRESH").alias("MARKET_MESSAGE_TYPE")
        )
        market_by_price_df = market_by_price_df.with_columns(
            pl.lit("TESTTICKER.MC").alias("TICKER")
        )
        market_by_price_df = market_by_price_df.with_columns(
            pl.lit("2020-01-11T00:00:00.000000000Z").alias("TIMESTAMP")
        )
        market_by_price_df = market_by_price_df.with_columns(pl.lit("+0").alias("GMT_OFFSET"))
        market_by_price_df = market_by_price_df.with_columns(pl.lit("3240").alias("PROD_PERM"))
        market_by_price_df = market_by_price_df.with_columns(
            pl.lit("TESTING SA").alias("DSPLY_NAME")
        )
        market_by_price_df = market_by_price_df.with_columns(pl.lit("TESTCOIN").alias("CURRENCY"))

        expected = pl.concat([expected, market_by_price_df.clone()])

    # Force column order in expected order. I.e. the final fill
    for col in supplement:
        if col not in expected.columns:
            expected = expected.with_columns(pl.lit("").alias(col))
    expected = expected.select(sorted(expected.columns))

    file.write_text(test_messages)

    assert run(Path(file), Path(tmp_path))

    if test_messages != "":
        res = pl.read_parquet(tmp_path / "part-*.parquet")
        assert_frame_equal(res, expected)
    else:
        # If the message was empty, no parquet file should be generated
        assert not all([file.suffix.endswith("parquet") for file in Path(tmp_path).iterdir()])


def test_run_raises_valueerror_when_file_is_not_csv_extension(tmp_path: Path):
    file = tmp_path / "test_file.txt"
    file.touch()

    with pytest.raises(ValueError) as excinfo:
        run(Path(file), Path(tmp_path))

    assert "is not of type CSV, Only .csv files are supported" in str(excinfo.value)


def test_run_raises_oserror_when_file_not_exists(tmp_path: Path):
    file = tmp_path / "test_file.csv"

    # The file is not created
    with pytest.raises(OSError, match=r'Failed to open file ".*test_file\.csv".*\(os error 2\)'):
        run(Path(file), Path(tmp_path))


@pytest.mark.parametrize(
    "num_messages", [0, 1]
)  # Number of Market By Price messages. IMPORTANT: flatten_market_by_price expects one Market By Price message
@pytest.mark.parametrize(
    "num_map_entries", [0, 1, 100]
)  # Number of MapEntry messages per Market By Price message
def test_flatten_market_by_price_ok(
    tmp_path: Path, num_messages: int, num_map_entries: int
) -> None:
    file = tmp_path / "test_file.csv"
    file.touch()
    # Build expected DataFrame
    expected = pl.DataFrame()
    test_messages = ""
    for num_message in range(num_messages):
        random_map_entries = {}
        market_by_price_df = pl.DataFrame()
        for index in range(num_map_entries):
            random_map_entries[("UPDATE", f"{index}.000000_B")] = {
                "BID_TIME": ["06:31:00.000000000"],
                "ORDER_PRC": ["100.0"],
                "ORDER_SIDE": ["1", "BID"],
                "NO_ORD": ["9"],
            }

        for key, map_entry in random_map_entries.items():
            row = pl.DataFrame({k: v[-1] for k, v in map_entry.items()})
            row = row.with_columns(pl.lit(key[0]).alias("MAP_ENTRY_TYPE"))
            row = row.with_columns(pl.lit(key[1]).alias("MAP_ENTRY_KEY"))
            market_by_price_df = pl.concat([market_by_price_df, row], how="vertical")

        test_messages += generate_market_by_price_message(
            "TESTTICKER.MC",
            "2020-01-11T00:00:00.000000000Z",
            "+0",
            True,
            num_message,
            {"PROD_PERM": ["3240"], "DSPLY_NAME": ["TESTING SA"], "CURRENCY": ["999", "TESTCOIN"]},
            random_map_entries,
        )
        market_by_price_df = market_by_price_df.with_columns(
            pl.lit("REFRESH").alias("MARKET_MESSAGE_TYPE")
        )
        market_by_price_df = market_by_price_df.with_columns(
            pl.lit("TESTTICKER.MC").alias("TICKER")
        )
        market_by_price_df = market_by_price_df.with_columns(
            pl.lit("2020-01-11T00:00:00.000000000Z").alias("TIMESTAMP")
        )
        market_by_price_df = market_by_price_df.with_columns(pl.lit("+0").alias("GMT_OFFSET"))
        market_by_price_df = market_by_price_df.with_columns(pl.lit("3240").alias("PROD_PERM"))
        market_by_price_df = market_by_price_df.with_columns(
            pl.lit("TESTING SA").alias("DSPLY_NAME")
        )
        market_by_price_df = market_by_price_df.with_columns(pl.lit("TESTCOIN").alias("CURRENCY"))

        expected = pl.concat([expected, market_by_price_df.clone()])

    res = flatten_market_by_price(test_messages)

    assert_frame_equal(res, expected, check_column_order=False)


# L10 Tests


def generate_l10_csv(
    ric: str, num_lines: int, bid_price: float = 70.0, ask_price: float = 75.0
) -> str:
    """Generate a simple L10 CSV file content"""
    # Header
    csv_content = "#RIC,Domain,Date-Time,Type,L1-BidPrice,L1-BidSize,L1-BuyNo,L1-AskPrice,L1-AskSize,L1-SellNo,"
    csv_content += "L2-BidPrice,L2-BidSize,L2-BuyNo,L2-AskPrice,L2-AskSize,L2-SellNo,"
    csv_content += "L3-BidPrice,L3-BidSize,L3-BuyNo,L3-AskPrice,L3-AskSize,L3-SellNo,"
    csv_content += "L4-BidPrice,L4-BidSize,L4-BuyNo,L4-AskPrice,L4-AskSize,L4-SellNo,"
    csv_content += "L5-BidPrice,L5-BidSize,L5-BuyNo,L5-AskPrice,L5-AskSize,L5-SellNo,"
    csv_content += "L6-BidPrice,L6-BidSize,L6-BuyNo,L6-AskPrice,L6-AskSize,L6-SellNo,"
    csv_content += "L7-BidPrice,L7-BidSize,L7-BuyNo,L7-AskPrice,L7-AskSize,L7-SellNo,"
    csv_content += "L8-BidPrice,L8-BidSize,L8-BuyNo,L8-AskPrice,L8-AskSize,L8-SellNo,"
    csv_content += "L9-BidPrice,L9-BidSize,L9-BuyNo,L9-AskPrice,L9-AskSize,L9-SellNo,"
    csv_content += (
        "L10-BidPrice,L10-BidSize,L10-BuyNo,L10-AskPrice,L10-AskSize,L10-SellNo,Exch Time\n"
    )

    # Data lines
    for i in range(num_lines):
        timestamp = f"2025-03-03T08:00:{i:02d}.000000000Z"
        csv_content += f"{ric},Market Price,{timestamp},Normalized LL2,"
        csv_content += f"{bid_price},{i + 1},1,{ask_price},{i + 2},1,"  # L1
        # L2-L10 (mostly empty for simplicity)
        csv_content += "," * 54  # 9 levels * 6 fields = 54 empty fields
        csv_content += "\n"  # Exch Time (empty)

    return csv_content


@pytest.mark.parametrize("num_lines", [1, 10, 100])
def test_run_l10_ok(tmp_path: Path, num_lines: int) -> None:
    # Arrange
    file = tmp_path / "test_l10.csv"
    csv_content = generate_l10_csv("TEST.RIC", num_lines)
    file.write_text(csv_content)

    # Act
    result = run_l10(Path(file), Path(tmp_path))

    # Assert
    assert result is True

    # Verify parquet was created
    parquet_files = list(tmp_path.glob("part-*.parquet"))
    assert len(parquet_files) > 0

    # Read and verify content
    df = pl.read_parquet(tmp_path / "part-*.parquet")
    assert df.shape[0] == num_lines
    assert df.shape[1] == 65  # All L10 columns

    # Verify some column names exist
    assert "#RIC" in df.columns
    assert "Domain" in df.columns
    assert "Date-Time" in df.columns
    assert "L1-BidPrice" in df.columns
    assert "L1-AskPrice" in df.columns

    # Verify data
    assert df["#RIC"][0] == "TEST.RIC"
    assert df["Domain"][0] == "Market Price"
    assert df["L1-BidPrice"][0] == "70.0"
    assert df["L1-AskPrice"][0] == "75.0"


def test_run_l10_empty_file(tmp_path: Path) -> None:
    # Arrange - file with only header
    file = tmp_path / "test_l10_empty.csv"
    csv_content = generate_l10_csv("TEST.RIC", 0)
    file.write_text(csv_content)

    # Act
    result = run_l10(Path(file), Path(tmp_path))

    # Assert
    assert result is True
    # No parquet files should be created for empty input
    parquet_files = list(tmp_path.glob("part-*.parquet"))
    # May have empty parquet or no parquet at all, both are acceptable
    if len(parquet_files) > 0:
        df = pl.read_parquet(tmp_path / "part-*.parquet")
        assert df.shape[0] == 0


def test_run_l10_raises_valueerror_when_file_is_not_csv_extension(tmp_path: Path):
    file = tmp_path / "test_file.txt"
    file.touch()

    with pytest.raises(ValueError) as excinfo:
        run_l10(Path(file), Path(tmp_path))

    assert "is not of type CSV, Only .csv files are supported" in str(excinfo.value)


def test_run_l10_raises_oserror_when_file_not_exists(tmp_path: Path):
    file = tmp_path / "test_l10_nonexistent.csv"

    # The file is not created
    with pytest.raises(
        OSError, match=r'Failed to open file ".*test_l10_nonexistent\.csv".*\(os error 2\)'
    ):
        run_l10(Path(file), Path(tmp_path))
