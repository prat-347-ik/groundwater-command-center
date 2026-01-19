import torch
import torch.nn as nn

class GroundwaterLSTM(nn.Module):
    def __init__(self, input_dim, hidden_dim=64, output_dim=1, num_layers=2):
        super(GroundwaterLSTM, self).__init__()
        
        # LSTM Layer: Captures time-dependencies
        # input_dim = number of features (Rain, Temp, Extraction, etc.)
        self.lstm = nn.LSTM(
            input_size=input_dim, 
            hidden_size=hidden_dim, 
            num_layers=num_layers, 
            batch_first=True,
            dropout=0.2
        )
        
        # Fully Connected Layer: Maps LSTM output to Water Level
        self.fc = nn.Linear(hidden_dim, output_dim)
        
    def forward(self, x):
        # x shape: (batch_size, sequence_length, input_dim)
        
        # LSTM Output
        # out shape: (batch_size, seq_len, hidden_dim)
        out, (hn, cn) = self.lstm(x)
        
        # We only care about the LAST time step for prediction
        # shape: (batch_size, hidden_dim)
        last_step_out = out[:, -1, :] 
        
        # Prediction
        prediction = self.fc(last_step_out)
        return prediction