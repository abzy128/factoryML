import os
import pandas as pd
import numpy as np
import tensorflow as tf
from keras import models, layers
from keras import layers, callbacks
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
import matplotlib.pyplot as plt
import joblib

# Configuration
SENSOR_COLUMNS = [
    "ActivePower"
]

TRAIN_FILE_PATH = "./data/dataset.csv"
TEST_FILE_PATH = "./data/dataset_test.csv"
MODEL_EXPORT_BASE_DIR = "./model/" # Base directory for models
DATETIME_COLUMN = "Datetime"  # Name of your datetime column

# Model & Training Parameters
SEQUENCE_LENGTH = 24  # Number of past time steps to use for prediction
VALIDATION_SPLIT_RATIO = 0.2  # 20% of training data for validation
EPOCHS = 100  # Max epochs; early stopping will likely stop it sooner
BATCH_SIZE = 32
PATIENCE_EARLY_STOPPING = 10  # Patience for early stopping

# --- Helper Functions ---

def load_data(file_path, datetime_col):
    """Loads data, parses datetime, and sets it as index."""
    try:
        df = pd.read_csv(file_path)
        df[datetime_col] = pd.to_datetime(df[datetime_col])
        df = df.set_index(datetime_col)
        print(f"Successfully loaded data from {file_path}")
        return df
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}. Please ensure it exists.")
        return None
    except Exception as e:
        print(f"Error loading data from {file_path}: {e}")
        return None


def create_sequences(data, seq_length):
    """Creates sequences and corresponding labels for LSTM."""
    xs, ys = [], []
    for i in range(len(data) - seq_length):
        x = data[i : (i + seq_length)]
        y = data[i + seq_length]
        xs.append(x)
        ys.append(y)
    if not xs: # Handle case where data is too short for any sequences
        return np.array([]).reshape((0, seq_length, 1)), np.array([]).reshape((0, 1))
    return np.array(xs), np.array(ys)


def build_lstm_model(input_shape):
    """Builds and compiles a simple LSTM model."""
    model = models.Sequential(
        [
            layers.LSTM(
                50, activation="relu", input_shape=input_shape
            ),
            layers.Dense(25, activation="relu"),
            layers.Dense(1),
        ]
    )
    model.compile(
        optimizer="adam", loss="mean_squared_error"
    )
    return model


def plot_training_history(history, feature_name, save_dir):
    """Plots training & validation loss and saves the plot."""
    plt.figure(figsize=(10, 6))
    plt.plot(
        history.history["loss"], label="Training Loss"
    )
    plt.plot(
        history.history["val_loss"], label="Validation Loss"
    )
    plt.title(f"Training History for {feature_name}")
    plt.xlabel("Epoch")
    plt.ylabel("Loss (MSE)")
    plt.legend()
    plt.grid(True)
    # Save plot inside the feature-specific model directory
    plot_path = os.path.join(save_dir, f"{feature_name}_training_history.png")
    plt.savefig(plot_path)
    plt.close()
    print(f"Saved training history plot to {plot_path}")


def plot_comparison_metric(
    metrics_dict, metric_name, title, save_path
):
    """Plots a bar chart comparing a metric across models."""
    features = list(metrics_dict.keys())
    values = list(metrics_dict.values())

    if not features:
        print(f"No data to plot for {title}")
        return

    plt.figure(figsize=(max(10, len(features) * 0.8), 6)) # Adjust width
    plt.bar(features, values, color="skyblue")
    plt.xlabel("Feature")
    plt.ylabel(metric_name)
    plt.title(title)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.grid(axis="y", linestyle="--")
    plt.savefig(save_path)
    #plt.show()
    print(f"Saved comparison plot to {save_path}")


# --- Script Execution ---

if not SENSOR_COLUMNS:
    print(
        "Error: SENSOR_COLUMNS list is empty. "
        "Please define the features to model in the script."
    )
    exit()

# Create base directories if they don't exist
os.makedirs(MODEL_EXPORT_BASE_DIR, exist_ok=True)
if not os.path.isdir("./data"):
    print("Error: ./data directory not found. Please create it and place your datasets there.")
    exit()


# Load data
print("Loading training data...")
df_train_val_full = load_data(
    TRAIN_FILE_PATH, DATETIME_COLUMN
)
if df_train_val_full is None:
    exit()

print("\nLoading test data...")
df_test_full = load_data(TEST_FILE_PATH, DATETIME_COLUMN)
if df_test_full is None:
    exit()

all_best_train_losses = {}
all_best_val_losses = {}
all_test_mses = {}

for feature_name in SENSOR_COLUMNS:
    print(f"\n--- Processing feature: {feature_name} ---")

    # Directory for plots specific to this feature will be MODEL_EXPORT_BASE_DIR
    # Model file will be directly in MODEL_EXPORT_BASE_DIR named {feature_name}.keras

    # 1. Prepare data for the current feature
    if feature_name not in df_train_val_full.columns:
        print(
            f"Warning: Feature '{feature_name}' not found in training data ({TRAIN_FILE_PATH}). Skipping."
        )
        continue
    if feature_name not in df_test_full.columns:
        print(
            f"Warning: Feature '{feature_name}' not found in test data ({TEST_FILE_PATH}). Skipping evaluation for this feature."
        )

    series_train_val = df_train_val_full[feature_name].copy().dropna()
    if series_train_val.empty:
        print(f"Warning: No data for feature '{feature_name}' in training set after dropna. Skipping.")
        continue

    split_index = int(
        len(series_train_val) * (1 - VALIDATION_SPLIT_RATIO)
    )
    series_train = series_train_val.iloc[:split_index]
    series_val = series_train_val.iloc[split_index:]

    if series_train.empty or series_val.empty:
        print(f"Warning: Not enough data to split train/val for '{feature_name}'. Skipping.")
        continue

    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_train = scaler.fit_transform(
        series_train.values.reshape(-1, 1)
    )
    scaled_val = scaler.transform(
        series_val.values.reshape(-1, 1)
    )

    X_train, y_train = create_sequences(
        scaled_train, SEQUENCE_LENGTH
    )
    X_val, y_val = create_sequences(
        scaled_val, SEQUENCE_LENGTH
    )

    if X_train.shape[0] == 0 or X_val.shape[0] == 0:
        print(f"Warning: Not enough data to create sequences for training/validation for '{feature_name}'. Skipping.")
        continue
    
    print(f"Training data shape (X, y): {X_train.shape}, {y_train.shape}")
    print(f"Validation data shape (X, y): {X_val.shape}, {y_val.shape}")

    scaler_filename = f"{feature_name}_scaler.joblib"
    scaler_path = os.path.join(MODEL_EXPORT_BASE_DIR, scaler_filename)
    try:
        joblib.dump(scaler, scaler_path)
        print(f"Scaler for {feature_name} saved to {scaler_path}")
    except Exception as e:
        print(f"Error saving scaler for {feature_name}: {e}")

    # 2. Build LSTM model
    model = build_lstm_model(
        input_shape=(SEQUENCE_LENGTH, 1)
    )
    model.summary()

    # 3. Train model
    early_stopping = callbacks.EarlyStopping(
        monitor="val_loss",
        patience=PATIENCE_EARLY_STOPPING,
        restore_best_weights=True,
        verbose=1
    )

    print(f"Training model for {feature_name}...")
    history = model.fit(
        X_train,
        y_train,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        validation_data=(X_val, y_val),
        callbacks=[early_stopping],
        verbose=1,
    )

    best_val_loss_epoch = np.argmin(history.history["val_loss"])
    all_best_train_losses[feature_name] = history.history["loss"][best_val_loss_epoch]
    all_best_val_losses[feature_name] = history.history["val_loss"][best_val_loss_epoch]

    # Save training history plot in the base model directory
    plot_training_history(
        history, feature_name, MODEL_EXPORT_BASE_DIR
    )

    # 4. Evaluate model on test data
    if feature_name in df_test_full.columns:
        series_test = df_test_full[feature_name].copy().dropna()
        if not series_test.empty:
            scaled_test = scaler.transform(
                series_test.values.reshape(-1, 1)
            )
            X_test, y_test = create_sequences(
                scaled_test, SEQUENCE_LENGTH
            )

            if X_test.shape[0] > 0:
                print(f"Test data shape (X, y): {X_test.shape}, {y_test.shape}")
                test_mse = model.evaluate(
                    X_test, y_test, verbose=0
                )
                all_test_mses[feature_name] = test_mse
                print(f"Test MSE for {feature_name}: {test_mse:.4f}")
            else:
                print(f"Warning: Not enough test data to create sequences for '{feature_name}'. Skipping evaluation.")
                all_test_mses[feature_name] = np.nan
        else:
            print(f"Warning: No test data for '{feature_name}' after dropna. Skipping evaluation.")
            all_test_mses[feature_name] = np.nan
    else:
        print(f"Warning: Feature '{feature_name}' not in test data. Test MSE will be NaN.")
        all_test_mses[feature_name] = np.nan

    # 5. Export model in .keras format
    # Model file will be named {featureName}.keras and saved in MODEL_EXPORT_BASE_DIR
    export_path = os.path.join(
        MODEL_EXPORT_BASE_DIR, f"{feature_name}.keras"
    )
    try:
        model.save(export_path)
        print(f"Model for {feature_name} saved to {export_path}")
    except Exception as e:
        print(f"Error saving model for {feature_name} to .keras format: {e}")


# --- Statistics Visualization ---
print("\n--- Overall Model Performance ---")
if all_test_mses:
    plot_mses = {k: v for k, v in all_test_mses.items() if not np.isnan(v)}
    if plot_mses:
        plot_comparison_metric(
            plot_mses,
            "Test MSE",
            "Comparison of Test MSE Across Models",
            os.path.join(MODEL_EXPORT_BASE_DIR, "comparison_test_mse.png"),
        )
    else:
        print("No valid Test MSEs to plot.")
else:
    print("No Test MSEs recorded.")

if all_best_val_losses:
    plot_val_losses = {k: v for k, v in all_best_val_losses.items() if not np.isnan(v)}
    if plot_val_losses:
        plot_comparison_metric(
            plot_val_losses,
            "Best Validation Loss",
            "Comparison of Best Validation Loss Across Models",
            os.path.join(MODEL_EXPORT_BASE_DIR, "comparison_validation_loss.png"),
        )
    else:
        print("No valid Validation Losses to plot.")

print("\nSummary of Metrics:")
summary_df = pd.DataFrame({
    "Best Train Loss": pd.Series(all_best_train_losses),
    "Best Validation Loss": pd.Series(all_best_val_losses),
    "Test MSE": pd.Series(all_test_mses)
})
print(summary_df.to_string())

summary_csv_path = os.path.join(MODEL_EXPORT_BASE_DIR, "model_metrics_summary.csv")
summary_df.to_csv(summary_csv_path)
print(f"Saved summary metrics to {summary_csv_path}")

print("\nScript finished.")
