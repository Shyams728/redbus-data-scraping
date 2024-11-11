# RedBus Scraper

This project is a web scraper built using Python and Selenium to extract bus details from the RedBus website. The scraped data includes information about RTC (Regional Transport Corporation) and private vehicles, such as bus names, types, departure times, durations, reaching times, star ratings, prices, and seat availability. The data is stored in a SQLite database and can be filtered and viewed using a Streamlit-based web interface.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Dependencies](#dependencies)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Data Extraction**: Scrapes bus details from RedBus, including RTC and private vehicles.
- **Database Storage**: Stores the scraped data in a SQLite database.
- **Filtering**: Allows users to filter the data based on various criteria such as route name, corporation name, star rating, and price range.
- **Streamlit Interface**: Provides a user-friendly interface to view and filter the scraped data.
- **Error Logging**: Logs errors encountered during the scraping process to a CSV file.

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/shyams728/redbus-data-scraper.git
   cd redbus-data-scraper
   ```

2. **Install the required dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Download and set up ChromeDriver**:
   - Download the appropriate version of ChromeDriver from [here](https://sites.google.com/a/chromium.org/chromedriver/downloads).
   - Extract the downloaded file and place the `chromedriver` executable in the project directory or update the path in the `initialize_driver` function.

## Usage

1. **Run the Streamlit app**:
   ```bash
   streamlit run redbus_scraper.py
   ```

2. **Access the app**:
   Open your web browser and go to `http://localhost:8501` to access the Streamlit interface.

3. **Extract Data**:
   - Select the "Extract Data" option to start scraping bus details from RedBus.
   - The progress of the scraping process will be displayed, and the data will be stored in the SQLite database.

4. **View Data**:
   - Select the "View the Data" option to filter and view the scraped data.
   - Use the sidebar options to filter the data based on route name, corporation name, star rating, and price range.

## Dependencies

- **Python**: 3.7+
- **Streamlit**: For the web interface.
- **Selenium**: For web scraping.
- **SQLite3**: For database storage.
- **Pandas**: For data manipulation.
- **ChromeDriver**: For controlling the Chrome browser.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue if you find any bugs or have suggestions for improvements.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.