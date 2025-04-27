use crossbeam::channel::bounded;
use polars::prelude::*;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use pyo3_polars::PyDataFrame;
use std::collections::HashMap;
use std::collections::HashSet;
use std::fs::{self, File};
use std::io::{BufRead, BufReader, BufWriter, Read, Seek, SeekFrom};
use std::path::PathBuf;
use std::thread::{available_parallelism, sleep};
use std::{thread, time};

#[pyfunction]
fn find_market_by_price_lines(path: PathBuf, py: Python) -> PyResult<PyObject> {
    if path.extension().and_then(|ext| ext.to_str()) != Some("csv") {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "The file {:?} is not of type CSV, Only .csv files are supported",
            path
        )));
    }

    let file = File::open(&path).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!(
            "Failed to open file {:?}: {}",
            path, e
        ))
    })?;

    let reader = BufReader::new(file);
    let mut result = Vec::new();

    for (i, line) in reader.lines().enumerate() {
        let line = line.map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Error reading line: {}", e))
        })?;
        if line.contains("Market By Price") {
            result.push(i);
        }
    }

    match PyList::new(py, result) {
        Ok(py_list) => Ok(py_list.into()),
        Err(e) => Err(e),
    }
}

#[pyfunction]
fn extract_fids(path: PathBuf, py: Python) -> PyResult<PyObject> {
    if path.extension().and_then(|ext| ext.to_str()) != Some("csv") {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "The file {:?} is not of type CSV, Only .csv files are supported",
            path
        )));
    }

    let file = File::open(&path).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!(
            "Failed to open file {:?}: {}",
            path, e
        ))
    })?;

    let reader = BufReader::new(file);
    let dict = PyDict::new(py);

    for line in reader.lines() {
        let line = line.map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Error reading line: {}", e))
        })?;

        let parts: Vec<&str> = line.split(',').collect();

        if parts[4].trim() == "FID" {
            let fid = parts[5].trim();
            let name = parts[7].trim();
            let mut has_two = "false";

            if !parts[9].is_empty() {
                has_two = "true";
            }

            if !fid.is_empty() && !name.is_empty() {
                let list = PyList::new(py, [fid, has_two]).unwrap();
                dict.set_item(name, list)?;
            }
        }
    }

    Ok(dict.into())
}

#[pyfunction]
fn flatten_map_entry(message: &str, py: Python) -> PyResult<PyObject> {
    let matrix = flat_map_entry(message);

    let py_list = PyList::empty(py);
    for row_vec in matrix {
        let py_row = PyList::empty(py);
        for cell in row_vec {
            py_row.append(cell.into_py(py))?;
        }
        py_list.append(py_row.into_py(py))?;
    }

    Ok(py_list.into_py(py))
}

fn flat_map_entry(message: &str) -> Vec<Vec<String>> {
    let mut rows: Vec<HashMap<String, String>> = Vec::new();
    let mut current_row: Option<HashMap<String, String>> = None;
    for line in message.lines() {
        let parts: Vec<&str> = line.split(',').collect();

        if parts[4] == "MapEntry" {
            // Start a new row
            if let Some(row) = current_row.take() {
                rows.push(row);
            }

            let mut new_row = HashMap::new();

            if let Some(entry_type) = parts.get(6) {
                new_row.insert("MAP_ENTRY_TYPE".to_string(), entry_type.to_string());
            }

            if let Some(entry_id) = parts.get(12) {
                new_row.insert("MAP_ENTRY_KEY".to_string(), entry_id.to_string());
            }

            current_row = Some(new_row);
        }

        if parts[4] == "FID" {
            let mut fid_value_index = 8;
            if !parts[9].is_empty() {
                fid_value_index = 9;
            }
            if let (Some(key), Some(value)) = (parts.get(7), parts.get(fid_value_index)) {
                if let Some(ref mut row) = current_row {
                    row.insert(key.to_string(), value.to_string());
                }
            }
        }
    }
    if let Some(row) = current_row.take() {
        rows.push(row);
    }
    // Build headers from all unique keys
    let mut headers: Vec<String> = rows.iter().flat_map(|r| r.keys().cloned()).collect();
    headers.sort();
    headers.dedup();

    let mut matrix: Vec<Vec<String>> = Vec::new();
    matrix.push(headers.clone());
    for row in &rows {
        let values = headers
            .iter()
            .map(|k| row.get(k).cloned().unwrap_or_default())
            .collect::<Vec<String>>();
        matrix.push(values);
    }
    matrix
}

fn flat_market_by_price(message: &str) -> Result<DataFrame, PolarsError> {
    let mut rows: Vec<HashMap<String, String>> = Vec::new();
    let mut current_row: Option<HashMap<String, String>> = None;
    let mut header_info: HashMap<String, String> = HashMap::new();
    let mut in_summary: bool = false;

    for line in message.lines() {
        let parts: Vec<&str> = line.split(',').collect();

        if parts.len() > 2 && parts[1] == "Market By Price" {
            // Extract header information
            if let Some(ticker) = parts.first() {
                header_info.insert("TICKER".to_string(), ticker.to_string());
            }
            if let Some(timestamp) = parts.get(2) {
                header_info.insert("TIMESTAMP".to_string(), timestamp.to_string());
            }
            if let Some(gmt_offset) = parts.get(3) {
                header_info.insert("GMT_OFFSET".to_string(), gmt_offset.to_string());
            }
            if let Some(market_message_type) = parts.get(5) {
                header_info.insert(
                    "MARKET_MESSAGE_TYPE".to_string(),
                    market_message_type.to_string(),
                );
            }
            continue;
        } else if parts[4] == "Summary" {
            in_summary = true;
            continue;
        } else if parts[4] == "MapEntry" {
            in_summary = false;
            // Start a new row
            if let Some(row) = current_row.take() {
                rows.push(row);
            }

            let mut new_row = HashMap::new();

            if let Some(entry_type) = parts.get(6) {
                new_row.insert("MAP_ENTRY_TYPE".to_string(), entry_type.to_string());
            }

            if let Some(entry_id) = parts.get(12) {
                new_row.insert("MAP_ENTRY_KEY".to_string(), entry_id.to_string());
            }

            current_row = Some(new_row);
        } else if parts[4] == "FID" {
            let mut fid_value_index = 8;
            if !parts[9].is_empty() {
                fid_value_index = 9;
            }
            if let (Some(key), Some(value)) = (parts.get(7), parts.get(fid_value_index)) {
                if in_summary {
                    // Add summary info to header_info
                    header_info.insert(key.to_string(), value.to_string());
                } else if let Some(ref mut row) = current_row {
                    row.insert(key.to_string(), value.to_string());
                }
            }
        }
    }
    // Last row
    if let Some(row) = current_row.take() {
        rows.push(row);
    }
    // Collect all unique column names
    let mut column_names: Vec<String> = rows.iter().flat_map(|row| row.keys().cloned()).collect();
    column_names.sort();
    column_names.dedup();

    // Create vectors for each column
    let mut columns: Vec<Column> = Vec::new();

    // Build each column
    for col_name in &column_names {
        let values: Vec<String> = rows
            .iter()
            .map(|row| row.get(col_name).cloned().unwrap_or_default())
            .collect();

        // Create the series for this column
        columns.push(Column::new(col_name.into(), values));
    }

    let new_columns: Vec<Expr> = header_info
        .iter()
        .map(|(key, value)| lit(value.clone()).alias(key.clone()))
        .collect();

    // Create the DataFrame
    let df = DataFrame::new(columns)?
        .lazy()
        .with_columns(new_columns)
        .collect()?;

    Ok(df)
}

#[pyfunction]
fn flatten_market_by_price(message: &str) -> PyResult<PyDataFrame> {
    let df = flat_market_by_price(message).unwrap();

    // Convert Polars DataFrame to Python PyObject
    let pydf = PyDataFrame(df);
    Ok(pydf)
}

struct IndexedMessage {
    index: usize,
    content: String,
}

struct IndexedDataFrame {
    index: usize,
    data: DataFrame,
}

#[pyfunction]
fn run(path: PathBuf, output_path: PathBuf, py: Python) -> PyResult<bool> {
    // Get the Python logger
    let logging = PyModule::import(py, "logging")?;
    let logger = logging.getattr("getLogger")?.call1(("lobmp",))?;

    if path.extension().and_then(|ext| ext.to_str()) != Some("csv") {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "The file {:?} is not of type CSV, Only .csv files are supported",
            path
        )));
    }

    let file: File = File::open(&path).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!(
            "Failed to open file {:?}: {}",
            path, e
        ))
    })?;
    let mut reader: BufReader<File> = BufReader::new(file);

    logger.call_method1(
        "info",
        ("Counting lines in file and recognising possible FIDs...",),
    )?;
    let mut possible_fids: HashSet<String> = HashSet::new();
    let mut line_count = 0;

    for line in reader.by_ref().lines() {
        let str_line = line.unwrap();
        line_count += 1;

        let parts: Vec<&str> = str_line.split(',').collect();
        if let Some(s) = parts.get(4) {
            if *s == "FID" {
                if let Some(fid_name) = parts.get(7) {
                    possible_fids.insert(fid_name.to_string());
                }
            }
        }
    }
    possible_fids.extend([
        "TICKER".to_string(),
        "TIMESTAMP".to_string(),
        "GMT_OFFSET".to_string(),
        "MARKET_MESSAGE_TYPE".to_string(),
        "MAP_ENTRY_TYPE".to_string(),
        "MAP_ENTRY_KEY".to_string(),
    ]);

    reader.seek(SeekFrom::Start(0))?;

    logger.call_method1("info", (format!("Found {} lines in file", line_count),))?;

    let num_cpus: usize = available_parallelism().unwrap().get();
    logger.call_method1("debug", (format!("Using {} CPUs", num_cpus),))?;

    let (tx_parsing, rx_parsing) = bounded::<IndexedMessage>(2 * num_cpus);
    let (tx_dataframes, rx_dataframes) = bounded::<IndexedDataFrame>(2 * num_cpus);

    let rx_parsing_run = rx_parsing.clone();
    let (tx_dataframes_run, rx_dataframes_run) = (tx_dataframes.clone(), rx_dataframes.clone());

    let mut parsing_threads = Vec::new();
    {
        for _i in 0..num_cpus {
            let rx_parsing = rx_parsing.clone();
            let tx_dataframes = tx_dataframes.clone();
            let parsing_handle = thread::spawn(move || {
                // Process messages until the channel is closed
                while let Ok(indexed_message) = rx_parsing.recv() {
                    let index = indexed_message.index;
                    let message = indexed_message.content;
                    match flat_market_by_price(message.as_str()) {
                        Ok(df) => {
                            // Send the DataFrame to the output channel
                            let indexed_df = IndexedDataFrame { index, data: df };
                            if tx_dataframes.send(indexed_df).is_err() {
                                println!("Dataframes queue was closed before the parsing queue was finished...");
                                return;
                            }
                        }
                        Err(e) => {
                            println!("Error processing message on processing thread: {}", e);
                            return;
                        }
                    }
                }
                drop(tx_dataframes);
            });

            parsing_threads.push(parsing_handle);
        }
    }
    let mut writing_threads = Vec::new();
    {
        let dataframe_handler = thread::spawn(move || {
            const BATCH_SIZE: usize = 16384;
            let mut dfs: Vec<LazyFrame> = Vec::new();
            let mut next_index_to_write: usize = 0;
            let mut dataframes_map: HashMap<usize, LazyFrame> = HashMap::new();
            let mut batch_counter: usize = 0;

            let mut expected_columns: Vec<&str> =
                possible_fids.iter().map(|s| s.as_str()).collect();
            expected_columns.sort();

            // Ensure the output directory exists
            fs::create_dir_all(&output_path).expect("Failed to create output directory");

            while let Ok(indexed_df) = rx_dataframes.recv() {
                let df_with_columns = indexed_df.data.clone().lazy();
                let mut df_with_all_columns =
                    expected_columns
                        .iter()
                        .fold(df_with_columns, |acc, &col_name| {
                            // Check if column exists
                            if indexed_df.data.schema().get(col_name).is_some() {
                                acc
                            } else {
                                // Add missing column with empty string values
                                acc.with_column(lit("").alias(col_name))
                            }
                        });
                df_with_all_columns = df_with_all_columns
                    .select(expected_columns.iter().map(|&c| col(c)).collect::<Vec<_>>());
                dataframes_map.insert(indexed_df.index, df_with_all_columns);

                while dataframes_map.contains_key(&next_index_to_write) && dfs.len() < BATCH_SIZE {
                    dfs.push(dataframes_map.remove(&next_index_to_write).unwrap());
                    next_index_to_write += 1;
                }

                if dfs.len() >= BATCH_SIZE {
                    let file_path = output_path.join(format!("part-{:06}.parquet", batch_counter));
                    let file = File::create(&file_path).expect("Failed to create batch file");
                    let writer = ParquetWriter::new(BufWriter::new(file));
                    let mut batch_df = concat(dfs.drain(..), UnionArgs::default())
                        .unwrap()
                        .collect()
                        .unwrap();

                    writer.finish(&mut batch_df).expect("Failed to write batch");
                    batch_counter += 1;
                }
            }

            // Final flush
            while let Some(lf) = dataframes_map.remove(&next_index_to_write) {
                dfs.push(lf);
                next_index_to_write += 1;
            }

            if !dfs.is_empty() {
                let file_path = output_path.join(format!("part-{:06}.parquet", batch_counter));
                let file = File::create(&file_path).expect("Failed to create final batch file");
                let writer = ParquetWriter::new(BufWriter::new(file));
                let mut final_df = concat(dfs, UnionArgs::default())
                    .unwrap()
                    .collect()
                    .unwrap();

                writer
                    .finish(&mut final_df)
                    .expect("Failed to write final batch");
            }
        });

        writing_threads.push(dataframe_handler);
    }

    let start_time: time::Instant = time::Instant::now();
    logger.call_method1("info", ("Starting file processing...",))?;

    let mut next_message: String = String::from("");
    let mut found_first: bool = false;
    let mut message_index = 0;
    for (i, line) in reader.lines().enumerate() {
        let line = line.map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Error reading line: {}", e))
        })?;
        if line.contains("Market By Price") {
            if !next_message.is_empty() && found_first {
                let indexed_message = IndexedMessage {
                    index: message_index,
                    content: next_message.clone(),
                };

                tx_parsing.send(indexed_message).unwrap();
                message_index += 1;
                next_message.clear();
            }
            if !found_first {
                found_first = true;
            }
        }
        if found_first {
            next_message.push_str(&line);
            next_message.push('\n');
        }
        if i > 0 && i % 100000 == 0 {
            let elapsed_time: time::Duration = time::Instant::now() - start_time;
            let estimated_total_time = (elapsed_time / i.try_into().unwrap()) * line_count;
            let estimated_remaining = estimated_total_time - elapsed_time;
            logger.call_method1(
                "info",
                (format!(
                    "Processed: {} lines. Estimated {:02?} remaining",
                    i, estimated_remaining
                ),),
            )?;
        }
    }

    // Send the last message if there is one
    if !next_message.is_empty() && found_first {
        let indexed_message = IndexedMessage {
            index: message_index,
            content: next_message.clone(),
        };

        if let Err(e) = tx_parsing.send(indexed_message) {
            logger.call_method1(
                "error",
                (format!(
                    "Failed to send last message to the parsing queue: {}",
                    e
                ),),
            )?;
        }
    }

    // Safely close parsing job
    while !tx_parsing.is_empty() && !rx_parsing_run.is_empty() {
        sleep(time::Duration::from_millis(10));
    }
    drop(tx_parsing);
    drop(rx_parsing_run);

    for handle in parsing_threads {
        match handle.join() {
            Ok(_) => {
                logger.call_method1("debug", ("Parsing thread completed successfully",))?;
            }
            Err(_e) => {
                logger.call_method1("error", ("Parsing thread panicked. This is very bad :(",))?;
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    "Parsing thread panicked. This is very bad :(",
                ));
            }
        }
    }

    // Safely close writing job
    while !tx_dataframes_run.is_empty() && !rx_dataframes_run.is_empty() {
        sleep(time::Duration::from_millis(10));
    }
    drop(tx_dataframes_run);
    drop(tx_dataframes);

    logger.call_method1("debug", ("Writing queue is empty!",))?;

    for handle in writing_threads {
        match handle.join() {
            Ok(_) => {
                logger.call_method1("debug", ("Writing thread completed successfully",))?;
            }
            Err(_e) => {
                logger.call_method1("error", ("Writing thread panicked. This is very bad :(",))?;
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    "Writing thread panicked. This is very bad :(",
                ));
            }
        }
    }
    Ok(true)
}

#[pymodule]
fn _lobmp(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(find_market_by_price_lines, m)?)?;
    m.add_function(wrap_pyfunction!(extract_fids, m)?)?;
    m.add_function(wrap_pyfunction!(flatten_map_entry, m)?)?;
    m.add_function(wrap_pyfunction!(flatten_market_by_price, m)?)?;
    m.add_function(wrap_pyfunction!(run, m)?)?;
    Ok(())
}
