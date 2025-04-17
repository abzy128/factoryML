import os
os.environ["KERAS_BACKEND"] = "tensorflow" # Set backend before importing keras

import pandas as pd
import numpy as np
import keras
import joblib
from fastapi import FastAPI, HTTPException, Query
from datetime import datetime, timedelta
import uvicorn
from typing import List, Dict, Any

# --- Configuration (Should match training script) ---
MODEL_BASE_PATH = './model'
MODEL_PATH = f'{MODEL_BASE_PATH}/factory_lstm_model.keras'
PREPROCESSOR_PATH = f'{MODEL_BASE_PATH}/preprocessor.joblib'
TARGET_SCALER_PATH = f'{MODEL_BASE_PATH}/target_scaler.joblib'
# For prototype: Load historical data source
# Use the original data file before splitting/processing in training
HISTORICAL_DATA_PATH = './data/dataset.csv'
SEQUENCE_LENGTH = 60 # Must match training!

# Redefine or import necessary lists/functions from training
# (Ensure these exactly match the ones used for training the loaded model)
SENSOR_COLUMNS = [
    'ActivePower', 'ReactivePower', 'MetalOutputIntensity',
    'FurnacePodTemparature', 'FurnaceBathTemperature', 'PowerSetpoint',
    'ReleaseAmountA', 'ReleaseAmountB', 'ReleaseAmountC',
    'UpperRingRaiseA', 'UpperRingRaiseB', 'UpperRingRaiseC',
    'UpperRingReleaseA', 'UpperRingReleaseB', 'UpperRingReleaseC',
    'GasPressureUnderFurnaceA', 'GasPressureUnderFurnaceB', 'GasPressureUnderFurnaceC',
    'PowerA', 'PowerB', 'PowerC',
    'HighVoltageA', 'HighVoltageB', 'HighVoltageC',
    'LowerRingReleaseA', 'LowerRingReleaseB', 'LowerRingReleaseC',
    'VentialtionValveForMantelA', 'VentialtionValveForMantelB', 'VentialtionValveForMantelC',
    'VoltageStepA', 'VoltageStepB', 'VoltageStepC',
    'CurrentHolderPositionA', 'CurrentHolderPositionB', 'CurrentHolderPositionC',
    'HolderModeA', 'HolderModeB', 'HolderModeC', # Categorical
    'AirTemperatureMantelA', 'AirTemperatureMantelB', 'AirTemperatureMantelC'
]
CATEGORICAL_COLUMNS = ['HolderModeA', 'HolderModeB', 'HolderModeC']
NUMERICAL_COLUMNS = [col for col in SENSOR_COLUMNS if col not in CATEGORICAL_COLUMNS]
TARGET_COLUMNS = SENSOR_COLUMNS # Assuming we predict all sensor columns
TIME_FEATURES = ['hour_sin', 'hour_cos', 'dayofweek_sin', 'dayofweek_cos']
ALL_NUMERICAL_FOR_SCALING = NUMERICAL_COLUMNS + TIME_FEATURES

def add_time_features(df_in):
    # Simplified version assuming df_in.index is DatetimeIndex
    df_out = df_in.copy()
    df_out['hour_sin'] = np.sin(2 * np.pi * df_out.index.hour / 24.0)
    df_out['hour_cos'] = np.cos(2 * np.pi * df_out.index.hour / 24.0)
    df_out['dayofweek_sin'] = np.sin(2 * np.pi * df_out.index.dayofweek / 7.0)
    df_out['dayofweek_cos'] = np.cos(2 * np.pi * df_out.index.dayofweek / 7.0)
    return df_out

# --- Global Variables ---
model = None
preprocessor = None
target_scaler = None
historical_df = None
feature_names_out = None # Store feature names after preprocessing

# --- FastAPI App ---
app = FastAPI(title="Factory Sensor Predictor")

# --- Helper Functions ---
def load_resources():
    """Loads model, preprocessors, and historical data at startup."""
    global model, preprocessor, target_scaler, historical_df, feature_names_out
    try:
        print("Loading Keras model...")
        model = keras.models.load_model(MODEL_PATH)
        print("Loading preprocessor...")
        preprocessor = joblib.load(PREPROCESSOR_PATH)
        print("Loading target scaler...")
        target_scaler = joblib.load(TARGET_SCALER_PATH)

        # Determine feature names after preprocessing (important!)
        try:
             # Get feature names from the fitted preprocessor
             feature_names_out = (
                 ALL_NUMERICAL_FOR_SCALING +
                 list(preprocessor.named_transformers_['cat'].get_feature_names_out(CATEGORICAL_COLUMNS))
             )
             print(f"Determined {len(feature_names_out)} processed feature names.")
        except Exception as e:
             print(f"Warning: Could not automatically determine feature names from preprocessor: {e}")
             print("Ensure feature_names_out is manually set correctly if needed.")
             # You might need to manually define this list if the above fails, matching training
             # feature_names_out = [...]


        print("Loading historical data for context...")
        # Load enough historical data to provide context for predictions
        # Adjust 'nrows' or loading strategy based on memory constraints
        historical_df = pd.read_csv(
            HISTORICAL_DATA_PATH,
            index_col='DateTime',
            parse_dates=True,
            usecols=['DateTime'] + SENSOR_COLUMNS # Load only necessary columns
        )
        historical_df.sort_index(inplace=True)
        # Basic imputation for historical data (match training approach)
        historical_df.ffill(inplace=True)
        # Use a global median or mean if needed for remaining NaNs at the start
        historical_df.fillna(historical_df.median(numeric_only=True), inplace=True)

        print("Resources loaded successfully.")

    except FileNotFoundError as e:
        print(f"Error loading resources: {e}. Make sure model/preprocessor files exist.")
        raise RuntimeError(f"Failed to load essential resources: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during resource loading: {e}")
        raise RuntimeError(f"Failed to load essential resources: {e}")


@app.on_event("startup")
async def startup_event():
    """Load resources when the server starts."""
    load_resources()

# --- API Endpoint ---
@app.get("/predict/", response_model=List[Dict[str, Any]])
async def get_predictions(
    sensorId: str = Query(..., description="The specific sensor ID (column name) to predict."),
    startDate: str = Query(..., description="Start date/time for prediction (ISO 8601 format, e.g., 2025-04-18T10:00:00Z)"),
    endDate: str = Query(..., description="End date/time for prediction (ISO 8601 format, e.g., 2025-04-18T12:00:00Z)")
):
    """
    Generates predictions for a specific sensor between startDate and endDate.
    Requires historical data preceding the startDate for context.
    """
    global model, preprocessor, target_scaler, historical_df, feature_names_out

    if not all([model, preprocessor, target_scaler, historical_df is not None, feature_names_out]):
         raise HTTPException(status_code=503, detail="Server resources not ready.")

    if sensorId not in TARGET_COLUMNS:
        raise HTTPException(status_code=400, detail=f"Invalid sensorId. Available sensors: {TARGET_COLUMNS}")

    try:
        start_dt = pd.to_datetime(startDate)
        end_dt = pd.to_datetime(endDate)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO 8601.")

    if start_dt >= end_dt:
        raise HTTPException(status_code=400, detail="startDate must be before endDate.")

    # --- Prediction Logic ---
    predictions = []
    current_dt = start_dt

    # 1. Get initial context data (SEQUENCE_LENGTH points before start_dt)
    context_end_time = start_dt - pd.Timedelta(minutes=1) # Last known actual data point
    context_start_time = context_end_time - pd.Timedelta(minutes=SEQUENCE_LENGTH - 1)

    # Ensure we have enough historical data
    if context_start_time < historical_df.index.min():
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient historical data. Need data back to {context_start_time}, but earliest available is {historical_df.index.min()}"
        )

    # Select the initial sequence data (raw features)
    # Use .loc for robust time-based indexing
    current_sequence_df_raw = historical_df.loc[context_start_time:context_end_time].copy()

    if len(current_sequence_df_raw) < SEQUENCE_LENGTH:
         raise HTTPException(
            status_code=400,
            detail=f"Data gap or insufficient points ({len(current_sequence_df_raw)}/{SEQUENCE_LENGTH}) in the historical context window ending at {context_end_time}."
        )
    # Ensure exactly SEQUENCE_LENGTH points if slicing resulted in more/less due to frequency
    current_sequence_df_raw = current_sequence_df_raw.iloc[-SEQUENCE_LENGTH:]


    print(f"Initial context window: {current_sequence_df_raw.index.min()} to {current_sequence_df_raw.index.max()} ({len(current_sequence_df_raw)} points)")

    # --- Iterative Prediction Loop ---
    while current_dt <= end_dt:
        # a. Add time features to the current raw sequence
        sequence_with_time = add_time_features(current_sequence_df_raw)

        # b. Preprocess the sequence
        # Ensure columns are in the correct order for the preprocessor
        sequence_processed = preprocessor.transform(sequence_with_time[SENSOR_COLUMNS + TIME_FEATURES]) # Use the columns preprocessor expects

        # c. Reshape for model input (samples, timesteps, features)
        model_input = np.reshape(sequence_processed, (1, SEQUENCE_LENGTH, sequence_processed.shape[1]))

        # d. Predict the next step (scaled) - predicts ALL target features
        scaled_prediction_vector = model.predict(model_input, verbose=0)[0] # Get the single prediction vector

        # e. Inverse transform the prediction to original scale
        original_scale_prediction_vector = target_scaler.inverse_transform(scaled_prediction_vector.reshape(1, -1))[0]

        # f. Create a DataFrame for the single predicted step
        prediction_df = pd.DataFrame(
            [original_scale_prediction_vector],
            columns=TARGET_COLUMNS,
            index=[current_dt] # Timestamp for this prediction
        )

        # g. Extract the requested sensor's prediction
        predicted_value_numpy = prediction_df.iloc[0][sensorId]
        predicted_value = predicted_value_numpy.item()
        
        predictions.append({
            "timestamp": current_dt.isoformat(),
            "sensorId": sensorId,
            "predicted_value": predicted_value
        })

        # h. Update the sequence for the next iteration:
        #    - Drop the oldest row from the raw sequence DataFrame
        #    - Append the new prediction (raw features)
        #    - Need to handle categorical features if they were predicted (or assume they persist/use logic)
        #      For simplicity here, we'll use the predicted numerical values and carry over
        #      the last known categorical values from the sequence.
        next_step_raw = prediction_df.iloc[[0]] # Keep it as a DataFrame row

        # Carry over categorical columns from the last step of the previous sequence
        last_step_cats = current_sequence_df_raw[CATEGORICAL_COLUMNS].iloc[[-1]]
        last_step_cats.index = next_step_raw.index # Align index
        for col in CATEGORICAL_COLUMNS:
             if col not in next_step_raw.columns: # Add if not predicted
                 next_step_raw[col] = last_step_cats[col].values[0]
             else: # Overwrite if predicted (less common for cats)
                 next_step_raw[col] = next_step_raw[col] # Or apply logic if needed


        # Ensure columns match the original historical_df order before concatenating
        next_step_raw = next_step_raw[current_sequence_df_raw.columns]

        # Append new prediction and drop oldest
        current_sequence_df_raw = pd.concat([current_sequence_df_raw.iloc[1:], next_step_raw])


        # Increment time for the next prediction step (assuming 1-minute frequency)
        current_dt += pd.Timedelta(minutes=1)

    return predictions

# --- Run the server ---
if __name__ == "__main__":
    # Ensure data directory exists if needed by HISTORICAL_DATA_PATH
    # os.makedirs('data', exist_ok=True)

    print("Starting FastAPI server...")
    # Use reload=True for development, remove for production
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
