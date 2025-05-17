import pandas as pd
from datetime import datetime as dt_datetime, time, timedelta
from typing import List, Union, TypeVar
from app.api.v1.schemas import DataPoint

# To handle pandas Timestamps in Pydantic model if needed, though we convert to datetime
PandasTimestamp = TypeVar("PandasTimestamp")

class SensorDataRepo:
    """
    Retrieves time-series data from a CSV file, with specific rules for
    out-of-range requests.
    """

    DATASET_START_DATE = pd.Timestamp("2025-01-13T00:00:00Z")
    DATASET_END_DATE = pd.Timestamp(
        "2025-02-16T23:59:59.999999Z"
    )  # Inclusive end
    DEFAULT_WEEK_START_DATE = pd.Timestamp(
        "2025-02-10T00:00:00Z"
    )  # This is a Monday

    def __init__(self, csv_path: str):
        """
        Initializes the retriever by loading and preparing the dataset.

        Args:
            csv_path (str): Path to the CSV dataset file.
        """
        self.df = self._load_data(csv_path)
        if self.df.empty:
            # Depending on requirements, could raise error or just warn
            print(f"Warning: DataFrame loaded from {csv_path} is empty.")
        elif self.df.index.name != "Datetime":
            # This check might be redundant if _load_data is robust
            raise ValueError(
                "DataFrame index must be 'Datetime' after loading."
            )

    def _load_data(self, csv_path: str) -> pd.DataFrame:
        """
        Loads data from the specified CSV file.

        Args:
            csv_path (str): Path to the CSV file.

        Returns:
            pd.DataFrame: DataFrame with 'Datetime' as timezone-aware UTC index.

        Raises:
            FileNotFoundError: If the CSV file is not found.
            ValueError: If 'Datetime' column is missing or other parsing issues.
            Exception: For other unexpected loading errors.
        """
        try:
            df = pd.read_csv(csv_path)
            if "Datetime" not in df.columns:
                raise ValueError(
                    "The CSV file must contain a 'Datetime' column."
                )

            # Convert 'Datetime' column to UTC-aware pandas Timestamps
            df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True)
            df = df.set_index("Datetime")
            df = df.sort_index()  # Ensure chronological order for slicing
            return df
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Error: The file {csv_path} was not found."
            )
        except ValueError as ve: # Catch specific pandas errors if possible
            raise ValueError(f"Error parsing CSV or 'Datetime' column: {ve}")
        except Exception as e:
            raise Exception(f"An unexpected error occurred loading data: {e}")

    def _ensure_dt_is_utc_aware_pd_timestamp(
        self, dt_input: dt_datetime
    ) -> pd.Timestamp:
        """Converts a datetime.datetime object to a UTC-aware pandas Timestamp."""
        if not isinstance(dt_input, dt_datetime):
            raise TypeError(
                "Input datetime must be a datetime.datetime object."
            )
        # Create a pandas Timestamp. If naive, localize to UTC. If aware, convert to UTC.
        ts = pd.Timestamp(dt_input)
        if ts.tzinfo is None:
            return ts.tz_localize("UTC")
        return ts.tz_convert("UTC")

    def _map_dt_to_default_week(
        self, dt_to_map: pd.Timestamp
    ) -> pd.Timestamp:
        """Maps a given Timestamp to the equivalent day and time in the default week."""
        if dt_to_map.tzinfo is None or dt_to_map.tzinfo.utcoffset(dt_to_map) is None:
             dt_to_map = dt_to_map.tz_localize("UTC") # Ensure tz-aware for weekday()
        elif dt_to_map.tzname() != "UTC":
             dt_to_map = dt_to_map.tz_convert("UTC")

        day_of_week = dt_to_map.weekday()  # Monday=0, Sunday=6
        time_of_day = dt_to_map.time()

        # DEFAULT_WEEK_START_DATE is a Monday
        target_date_in_default_week = (
            self.DEFAULT_WEEK_START_DATE.date()
            + pd.Timedelta(days=day_of_week)
        )

        # Combine the target date with the original time
        target_dt_naive = dt_datetime.combine(
            target_date_in_default_week, time_of_day
        )
        # Return as a UTC-aware pandas Timestamp
        return pd.Timestamp(target_dt_naive, tz="UTC")

    def get_sensor_value(
        self, sensorName: str, startDate: dt_datetime, endDate: dt_datetime
    ) -> List[DataPoint]:
        """
        Retrieves a list of DataPoint objects for a given sensor and time range.

        - If startDate is within the dataset's valid range (DATASET_START_DATE
          to DATASET_END_DATE), data is fetched for the original [startDate, endDate].
        - If startDate is outside this range, startDate is mapped to the
          default week (2025-02-10 to 2025-02-16), the original duration of
          the query is preserved, and data is fetched for this mapped range.

        Args:
            sensorName (str): The name of the sensor (column) to retrieve data for.
            startDate (datetime): The start of the time range.
            endDate (datetime): The end of the time range.

        Returns:
            List[DataPoint]: A list of DataPoint objects.

        Raises:
            ValueError: If sensorName is invalid, or startDate is after endDate.
            TypeError: If startDate or endDate are not datetime.datetime objects.
        """
        if sensorName not in self.df.columns:
            raise ValueError(
                f"Sensor '{sensorName}' not found in dataset columns: {self.df.columns.tolist()}"
            )

        start_ts = self._ensure_dt_is_utc_aware_pd_timestamp(startDate)
        end_ts = self._ensure_dt_is_utc_aware_pd_timestamp(endDate)

        if start_ts > end_ts:
            raise ValueError("startDate cannot be after endDate.")

        actual_query_start: pd.Timestamp
        actual_query_end: pd.Timestamp

        # Determine the query range based on whether startDate is in the dataset's valid period
        if (
            self.DATASET_START_DATE <= start_ts <= self.DATASET_END_DATE
        ):
            actual_query_start = start_ts
            actual_query_end = end_ts
        else:
            # startDate is out of range; map to default week and preserve duration
            actual_query_start = self._map_dt_to_default_week(start_ts)
            duration = end_ts - start_ts
            actual_query_end = actual_query_start + duration

        # Slice the DataFrame for the determined range and sensor
        # .loc is inclusive for both start and end if they are exact matches in the index
        try:
            sensor_series = self.df.loc[
                actual_query_start:actual_query_end, sensorName
            ]
        except KeyError:
            # This can occur if the range is completely outside any data,
            # even after mapping, or if the slice results in no data.
            return []

        # Drop NaN values, as DataPoint.value expects non-null float, int, or str
        sensor_series = sensor_series.dropna()

        # Format into DataPoint objects
        data_points = [
            DataPoint(
                timestamp=idx.to_pydatetime(), value=val
            )  # Convert pd.Timestamp index to datetime.datetime
            for idx, val in sensor_series.items()
        ]

        return data_points

