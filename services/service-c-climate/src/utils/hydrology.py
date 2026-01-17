def calculate_evapotranspiration(temp_c: float, humidity_pct: float) -> float:
    """
    Estimates Potential Evapotranspiration (PET) using a simplified method
    appropriate for the available data variables.
    
    Note: Real-world systems use Penman-Monteith, but that requires wind speed 
    and pressure. Here we use a temperature-humidity index proxy.
    """
    # Base evaporation factor
    # Higher Temp = Higher Evaporation
    # Lower Humidity = Higher Evaporation
    
    saturation_deficit = (100 - humidity_pct) / 100.0
    evap_factor = 0.05 # Calibration constant for the region
    
    # Simple formula: E = k * T * (1 - RelHum)
    pet_mm = evap_factor * temp_c * saturation_deficit
    
    return max(0.0, pet_mm)

def calculate_effective_rainfall(
    total_rainfall_mm: float, 
    temp_c: float, 
    humidity_pct: float
) -> float:
    """
    Calculates the 'Effective Rainfall' that actually recharges the aquifer
    after accounting for evaporation losses.
    
    Formula: Recharge = Max(0, Rainfall - Evapotranspiration)
    """
    evap_loss = calculate_evapotranspiration(temp_c, humidity_pct)
    effective_rain = total_rainfall_mm - evap_loss
    
    return max(0.0, effective_rain)