import os
import pandas as pd
import numpy as np
from keras import Model, models
import joblib
from sklearn.preprocessing import MinMaxScaler

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from typing import List, Dict

# Configuration
SEQUENCE_LENGTH = 24
DATETIME_COLUMN = "Datetime"
MODEL_BASE_DIR = "../model/"
TEST_FILE_PATH = "../data/dataset.csv"

AVAILABLE_SENSOR_COLUMNS = [
    'ActivePower', 'ReactivePower',
    'MetalOutputIntensity',
    'PowerSetpoint',
    'FurnacePodTemparature', 'FurnaceBathTemperature',
    'ReleaseAmountA', 'ReleaseAmountB', 'ReleaseAmountC',
    'UpperRingRaiseA', 'UpperRingRaiseB', 'UpperRingRaiseC',
    'UpperRingReleaseA', 'UpperRingReleaseB', 'UpperRingReleaseC',
    'GasPressureUnderFurnaceA', 'GasPressureUnderFurnaceB', 'GasPressureUnderFurnaceC',
    'PowerA', 'PowerB', 'PowerC',
    'HighVoltageA', 'HighVoltageB', 'HighVoltageC'
    'LowerRingReleaseA', 'LowerRingReleaseB', 'LowerRingReleaseC',
    'VentialtionValveForMantelA', 'VentialtionValveForMantelB', 'VentialtionValveForMantelC',
    'VoltageStepA', 'VoltageStepB', 'VoltageStepC',
    'CurrentHolderPositionA', 'CurrentHolderPositionB', 'CurrentHolderPositionC',
    'HolderModeA', 'HolderModeB', 'HolderModeC',
    'AirTemperatureMantelA', 'AirTemperatureMantelB', 'AirTemperatureMantelC'
]

# Pydantic Models for Request and Response
class PredictionRequest(BaseModel):
    sensorName: str
    startDate: datetime
    endDate: datetime

class DataPoint(BaseModel):
    timestamp: datetime
    value: float

class PredictionResponse(BaseModel):
    sensorName: str
    data: List[DataPoint]
    message: str

app = FastAPI(title="ML Inference API")

# Global Caches and Pre-loaded Data
loaded_models: Dict[str, Model] = {}
loaded_scalers: Dict[str, MinMaxScaler] = {}
df_test_full: pd.DataFrame = None
last_known_timestamps: Dict[str, pd.Timestamp] = {}
initial_scaled_sequences: Dict[str, list] = {}


def load_test_data(file_path: str, datetime_col: str) -> pd.DataFrame:
    """Loads test data, parses datetime, sets index, and ensures UTC."""
    try:
        df = pd.read_csv(file_path)
        df[datetime_col] = pd.to_datetime(df[datetime_col])
        df = df.set_index(datetime_col)
        # Ensure index is UTC timezone-aware
        if df.index.tzinfo is None:
            df.index = df.index.tz_localize('UTC')
        else:
            df.index = df.index.tz_convert('UTC')
        print(f"Successfully loaded and processed test data from {file_path}")
        return df
    except FileNotFoundError:
        print(f"FATAL: Test data file not found at {file_path}")
        raise
    except Exception as e:
        print(f"FATAL: Error loading test data from {file_path}: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    """Load necessary data and prepare initial sequences on startup."""
    global df_test_full, last_known_timestamps, initial_scaled_sequences

    print("Application startup: Loading test data and preparing initial sequences...")
    df_test_full = load_test_data(TEST_FILE_PATH, DATETIME_COLUMN)
    if df_test_full is None:
        # load_test_data now raises an error, so this check might be redundant
        # but good for safety.
        raise RuntimeError("Failed to load test data on startup.")

    for sensor_name in AVAILABLE_SENSOR_COLUMNS:
        if sensor_name not in df_test_full.columns:
            print(f"Warning: Sensor {sensor_name} not found in test data. Skipping initial sequence preparation.")
            continue

        # Load scaler for this sensor
        scaler_path = os.path.join(MODEL_BASE_DIR, f"{sensor_name}_scaler.joblib")
        if not os.path.exists(scaler_path):
            print(f"Warning: Scaler for {sensor_name} not found at {scaler_path}. Cannot prepare initial sequence.")
            continue
        try:
            scaler = joblib.load(scaler_path)
            loaded_scalers[sensor_name] = scaler # Cache scaler
        except Exception as e:
            print(f"Warning: Failed to load scaler for {sensor_name}: {e}")
            continue

        # Get the last SEQUENCE_LENGTH raw values from the test set
        sensor_series = df_test_full[sensor_name].dropna()
        if len(sensor_series) < SEQUENCE_LENGTH:
            print(f"Warning: Not enough data points in test set for {sensor_name} (need {SEQUENCE_LENGTH}, got {len(sensor_series)}).")
            continue

        last_known_raw_sequence = sensor_series.iloc[-SEQUENCE_LENGTH:].values
        # Scale these values using the loaded scaler
        scaled_sequence = scaler.transform(last_known_raw_sequence.reshape(-1, 1)).flatten().tolist()
        
        initial_scaled_sequences[sensor_name] = scaled_sequence
        last_known_timestamps[sensor_name] = sensor_series.index[-1] # This is UTC
        print(f"Prepared initial sequence for {sensor_name}. Last known timestamp: {last_known_timestamps[sensor_name]}")

    print("Startup complete.")


def get_model_and_scaler(sensor_name: str):
    """Lazily loads model and retrieves scaler for a given sensor."""
    if sensor_name not in AVAILABLE_SENSOR_COLUMNS:
        raise HTTPException(status_code=404, detail=f"Sensor '{sensor_name}' is not supported or model data is unavailable.")

    # Load Keras model if not already cached
    if sensor_name not in loaded_models:
        model_path = os.path.join(MODEL_BASE_DIR, f"{sensor_name}.keras")
        if not os.path.exists(model_path):
            raise HTTPException(status_code=500, detail=f"Model file for sensor '{sensor_name}' not found.")
        try:
            loaded_models[sensor_name] = models.load_model(model_path)
            print(f"Loaded Keras model for {sensor_name}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error loading model for '{sensor_name}': {str(e)}")

    # Retrieve scaler (should be cached during startup)
    if sensor_name not in loaded_scalers:
        # This case should ideally be handled by startup, but as a fallback:
        scaler_path = os.path.join(MODEL_BASE_DIR, f"{sensor_name}_scaler.joblib")
        if not os.path.exists(scaler_path):
             raise HTTPException(status_code=500, detail=f"Scaler for sensor '{sensor_name}' not found (should have been loaded on startup).")
        try:
            loaded_scalers[sensor_name] = joblib.load(scaler_path)
            print(f"Loaded scaler for {sensor_name} on demand.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error loading scaler for '{sensor_name}': {str(e)}")


    return loaded_models[sensor_name], loaded_scalers[sensor_name]


@app.get("/api/v1/sensor/predict", response_model=PredictionResponse)
async def predict_sensor_values(
    sensorName: str = Query(..., example="ActivePower"),
    startDate: datetime = Query(..., example="2025-02-17T01:00:00Z"),
    endDate: datetime = Query(..., example="2025-02-17T02:00:00Z"),
):
    
    sensor_name = sensorName

    # Validate sensor name
    if sensor_name not in AVAILABLE_SENSOR_COLUMNS:
        raise HTTPException(status_code=400, detail=f"Sensor '{sensor_name}' is not supported.")
    if sensor_name not in initial_scaled_sequences or sensor_name not in last_known_timestamps:
        raise HTTPException(status_code=503, detail=f"Initial data for sensor '{sensor_name}' not available. Check server logs.")

    # Ensure dates are UTC
    start_date_utc = startDate.astimezone(timezone.utc) if startDate.tzinfo else startDate.replace(tzinfo=timezone.utc)
    end_date_utc = endDate.astimezone(timezone.utc) if endDate.tzinfo else endDate.replace(tzinfo=timezone.utc)

    if start_date_utc >= end_date_utc:
        raise HTTPException(status_code=400, detail="Start date must be before end date.")

    model, scaler = get_model_and_scaler(sensor_name)
    
    # Get the pre-calculated initial sequence and last known timestamp for this sensor
    current_scaled_sequence = list(initial_scaled_sequences[sensor_name]) # Make a copy
    current_timestamp = last_known_timestamps[sensor_name]

    # Predictions should start after the last known data point
    min_prediction_start_time = current_timestamp + timedelta(minutes=1)
    if start_date_utc < min_prediction_start_time:
        raise HTTPException(
            status_code=400,
            detail=f"Prediction start date ({start_date_utc.isoformat()}) "
                   f"cannot be before the earliest possible prediction time "
                   f"({min_prediction_start_time.isoformat()})."
        )

    predictions_output: List[DataPoint] = []
    
    print(f"Starting prediction for {sensor_name} from {current_timestamp.isoformat()} up to {end_date_utc.isoformat()}")
    print(f"Client requested range: {start_date_utc.isoformat()} to {end_date_utc.isoformat()}")

    # Iteratively predict minute by minute
    # The loop continues as long as current_timestamp (timestamp of the *last* value in sequence)
    # is less than the target endDate. The prediction will be for current_timestamp + 1 min.
    while current_timestamp < end_date_utc:
        if len(current_scaled_sequence) < SEQUENCE_LENGTH:
            # This should not happen if initial_scaled_sequences is set up correctly
            raise HTTPException(status_code=500, detail="Internal error: Insufficient data in sequence.")

        # Prepare input for model (last SEQUENCE_LENGTH points)
        input_for_model = np.reshape(
            np.array(current_scaled_sequence[-SEQUENCE_LENGTH:]), (1, SEQUENCE_LENGTH, 1)
        )
        
        # Predict scaled value for the next minute
        scaled_pred = model.predict(input_for_model, verbose=0)[0, 0]
        #print(f"Predicted scaled value: {scaled_pred} for timestamp: {current_timestamp.isoformat()}")
        # Update current_timestamp for this new prediction
        current_timestamp += timedelta(minutes=1)
        
        # Inverse transform to original scale
        original_pred = scaler.inverse_transform(np.array([[scaled_pred]]))[0, 0]
        
        # Add to output list if it falls within the user's requested date range
        if current_timestamp >= start_date_utc and current_timestamp <= end_date_utc:
            predictions_output.append(
                DataPoint(timestamp=current_timestamp, value=float(original_pred))
            )
            
        # Update the sequence for the next iteration by appending the new scaled prediction
        current_scaled_sequence.append(scaled_pred)
        # No need to explicitly truncate current_scaled_sequence, as slicing [-SEQUENCE_LENGTH:] handles it.

        # Safety break for extremely long requests (optional, adjust as needed)
        # if len(predictions_output) > 7 * 24 * 60 * 2 : # Max 2 weeks of minute-by-minute data
        #      print("Warning: Prediction limit reached for a single request.")
        #      break
    
    if not predictions_output and start_date_utc <= end_date_utc :
        # This might happen if the requested range is valid but very short and falls
        # between prediction steps, or if end_date_utc was just after current_timestamp
        # before the loop could make a relevant prediction.
        message = "No prediction data generated for the specified range. The range might be too short or outside effective prediction generation."
    else:
        message = "Prediction successful"


    return PredictionResponse(
        sensorName=sensor_name,
        data=predictions_output,
        message=message
    )

if __name__ == "__main__":
    import uvicorn
    print("Starting Uvicorn server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

