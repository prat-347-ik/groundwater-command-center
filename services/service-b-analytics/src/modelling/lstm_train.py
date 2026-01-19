import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import numpy as np
import logging
import sys
import os
from src.config.mongo_client import mongo_client
from src.modelling.lstm_arch import GroundwaterLSTM

# Logging
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

# HYPERPARAMETERS
SEQUENCE_LENGTH = 30 # Look back 30 days
HIDDEN_DIM = 50
EPOCHS = 100
LEARNING_RATE = 0.01

def create_sequences(data, seq_length, feature_cols, target_col):
    xs, ys = [], []
    data_matrix = data[feature_cols].values
    target_array = data[target_col].values

    for i in range(len(data) - seq_length):
        x = data_matrix[i : i + seq_length]
        y = target_array[i + seq_length]
        xs.append(x)
        ys.append(y)
        
    return np.array(xs), np.array(ys)

def train_lstm_for_region(region_id: str):
    logger.info(f"🧠 Starting LSTM Training for {region_id}...")
    
    # 1. Fetch Data
    db = mongo_client.get_olap_db()
    cursor = db.region_feature_store.find({"region_id": region_id}).sort("date", 1)
    df = pd.DataFrame(list(cursor))
    
    if len(df) < (SEQUENCE_LENGTH + 5):
        logger.warning(f"❌ Not enough data ({len(df)} rows). Need > {SEQUENCE_LENGTH + 5}.")
        return

    # 2. Select Features
    feature_cols = [
        'effective_rainfall', 'log_extraction', 'feat_net_flux_1d_lag',
        'feat_soil_permeability', 'feat_sin_day', 'feat_cos_day'
    ]
    target_col = 'target_water_level'
    
    # Fill NaNs
    df = df.fillna(0)

    # 3. Create Sequences
    X, y = create_sequences(df, SEQUENCE_LENGTH, feature_cols, target_col)
    
    # Convert to Tensors
    X_tensor = torch.tensor(X, dtype=torch.float32)
    y_tensor = torch.tensor(y, dtype=torch.float32).view(-1, 1)
    
    # 4. Initialize Model
    model = GroundwaterLSTM(input_dim=len(feature_cols), hidden_dim=HIDDEN_DIM)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    
    # 5. Train
    model.train()
    for epoch in range(EPOCHS):
        optimizer.zero_grad()
        outputs = model(X_tensor)
        loss = criterion(outputs, y_tensor)
        loss.backward()
        optimizer.step()
        
        if (epoch+1) % 20 == 0:
            logger.info(f"   Epoch [{epoch+1}/{EPOCHS}], Loss: {loss.item():.4f}")

    # 6. Save Model
    save_path = f"models/v1/lstm_{region_id}.pth"
    os.makedirs("models/v1", exist_ok=True)
    torch.save(model.state_dict(), save_path)
    logger.info(f"✅ LSTM Model Saved: {save_path}")

if __name__ == "__main__":
    # Use the Region ID from your previous output
    train_lstm_for_region("65f4fc28-a5f9-47e0-b326-962b20bb35b1")  # Replace with actual Region ID