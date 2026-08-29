import torch
import torch.nn as nn

class GroundwaterLSTM(nn.Module):
    """
    PyTorch LSTM recurrent neural network for multi-day groundwater level forecasting.
    Ported directly from feature/deep-learning branch.
    """
    def __init__(self, input_dim: int = 6, hidden_dim: int = 50, output_dim: int = 1, num_layers: int = 2):
        super(GroundwaterLSTM, self).__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.num_layers = num_layers
        
        # LSTM Layer: Captures temporal dependencies across the 30-day lookback sequence
        self.lstm = nn.LSTM(
            input_size=input_dim, 
            hidden_size=hidden_dim, 
            num_layers=num_layers, 
            batch_first=True,
            dropout=0.2 if num_layers > 1 else 0.0
        )
        
        # Fully Connected Layer: Maps final hidden state to predicted water level
        self.fc = nn.Linear(hidden_dim, output_dim)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        x shape: (batch_size, sequence_length=30, input_dim=6)
        Output shape: (batch_size, 1)
        """
        out, (hn, cn) = self.lstm(x)
        last_step_out = out[:, -1, :] # Last time step
        prediction = self.fc(last_step_out)
        return prediction
