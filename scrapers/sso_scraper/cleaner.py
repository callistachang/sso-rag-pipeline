from bs4 import BeautifulSoup


def clean_data(html_content: str) -> str:
    """
    Takes a full act HTML and parses the important text into a text file.
    """

    soup = BeautifulSoup(html_content, "html.parser")
    parts = []

    divs = soup.find_all("div", class_="prov1")
    for div in divs:
        header = div.find("span", class_="").text.strip()
        content = div.find("td", class_="prov1Txt").text.strip()
        act_text = f"{header}\n{content}"
        parts.append(act_text)

    output_text = "\n\n".join(parts)
    return output_text


if __name__ == "__main__":
    import glob
    import os
    from pathlib import Path

    assert "scrapers" in os.getcwd().split("/")[-1], "must be called within the /scrapers dir"

    in_folder = "out_html"
    out_folder = "out_text"
    relative_filepaths = glob.glob(f"./**/{in_folder}/*", recursive=True)

    for in_fp in relative_filepaths:
        in_fp = Path(in_fp)
        html_content = in_fp.read_text()
        cleaned_text_content = clean_data(html_content)

        out_fp = Path(out_folder) / f"{in_fp.stem}.txt"
        out_fp.parent.mkdir(parents=True, exist_ok=True)
        out_fp.write_text(cleaned_text_content)
        print(f"saved to file {out_fp}")
