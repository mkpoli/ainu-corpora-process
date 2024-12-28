use pyo3::prelude::*;
use quick_xml::events::Event;
use quick_xml::Reader;
use regex::Regex;
use serde::Serialize;
use std::fs::File;
use std::io::{BufReader, BufWriter, Write};

#[derive(Serialize)]
struct Entry {
    title: String,
    text: String,
}

fn parse_wiktionary_dump(
    reader: BufReader<File>,
    writer: &mut BufWriter<File>,
) -> std::io::Result<()> {
    let mut xml_reader = Reader::from_reader(reader);
    xml_reader.trim_text(true);

    let mut buf = Vec::new();
    let mut in_page = false;
    let mut in_title = false;
    let mut in_ns = false;
    let mut in_text = false;

    let mut title = String::new();
    let mut ns = String::new();
    let mut text = String::new();

    let regex = Regex::new(r"==[^=]*(?:\{\{(?:L\|ain|ain)\}\}|アイヌ語)[^=]*==").unwrap();

    write!(writer, "[")?;
    let mut first = true;

    loop {
        match xml_reader.read_event_into(&mut buf) {
            Ok(Event::Start(ref e)) => match e.name().as_ref() {
                b"page" => {
                    in_page = true;
                    title.clear();
                    ns.clear();
                    text.clear();
                }
                b"title" if in_page => {
                    in_title = true;
                }
                b"ns" if in_page => {
                    in_ns = true;
                }
                b"text" if in_page => {
                    in_text = true;
                }
                _ => {}
            },
            Ok(Event::End(ref e)) => match e.name().as_ref() {
                b"page" => {
                    if ns == "0" && regex.is_match(&text) {
                        let entry = Entry {
                            title: title.clone(),
                            text: text.clone(),
                        };
                        if !first {
                            write!(writer, ",")?;
                        }
                        serde_json::to_writer(&mut *writer, &entry)?;
                        first = false;
                    }
                    in_page = false;
                }
                b"title" => {
                    in_title = false;
                }
                b"ns" => {
                    in_ns = false;
                }
                b"text" => {
                    in_text = false;
                }
                _ => {}
            },
            Ok(Event::Text(e)) => {
                let t = e.unescape().unwrap().to_string();
                if in_title {
                    title.push_str(&t);
                } else if in_ns {
                    ns.push_str(&t);
                } else if in_text {
                    text.push_str(&t);
                }
            }
            Ok(Event::Eof) => break,
            Err(e) => eprintln!("Error: {:?}", e),
            _ => {}
        }
        buf.clear();
    }

    write!(writer, "]")?;

    Ok(())
}

#[pyfunction]
fn extract_ainu_entries(input_path: &str, output_path: &str) -> PyResult<()> {
    let input_file = File::open(input_path)?;
    let reader = BufReader::new(input_file);

    let output_file = File::create(output_path)?;
    let mut writer = BufWriter::new(output_file);

    parse_wiktionary_dump(reader, &mut writer)?;

    Ok(())
}

#[pymodule]
fn wiktionary(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(extract_ainu_entries, m)?)?;
    Ok(())
}
