from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Configuration
RESIDENTIAL_VOLTAGE = 230  # Volts
INDUSTRIAL_VOLTAGE = 415   # Volts (3-phase)

# Tariff rates (₹ per kWh)
TARIFF_RATES = {
    "residential": {"name": "Residential", "rate": 10.0, "currency": "₹"},
    "industrial": {"name": "Industrial", "rate": 15.0, "currency": "₹"}
}

# Residential wire specifications
RESIDENTIAL_WIRE_SPECS = {
    "0.5": {"current": 6.0, "power": 6.0 * RESIDENTIAL_VOLTAGE},
    "0.75": {"current": 7.5, "power": 7.5 * RESIDENTIAL_VOLTAGE},
    "1.0": {"current": 12, "power": 12 * RESIDENTIAL_VOLTAGE},
    "1.5": {"current": 16, "power": 16 * RESIDENTIAL_VOLTAGE},
    "2.0": {"current": 19, "power": 19 * RESIDENTIAL_VOLTAGE},
    "2.5": {"current": 22, "power": 22 * RESIDENTIAL_VOLTAGE},
    "4.0": {"current": 29, "power": 29 * RESIDENTIAL_VOLTAGE},
    "6.0": {"current": 37, "power": 37 * RESIDENTIAL_VOLTAGE},
    "10.0": {"current": 52, "power": 52 * RESIDENTIAL_VOLTAGE},
}

# Industrial wire specifications
INDUSTRIAL_WIRE_SPECS = {
    "1.5": {"current": 20, "power": 20 * INDUSTRIAL_VOLTAGE},
    "2.5": {"current": 27, "power": 27 * INDUSTRIAL_VOLTAGE},
    "4.0": {"current": 36, "power": 36 * INDUSTRIAL_VOLTAGE},
    "6.0": {"current": 46, "power": 46 * INDUSTRIAL_VOLTAGE},
    "10.0": {"current": 63, "power": 63 * INDUSTRIAL_VOLTAGE},
    "16.0": {"current": 85, "power": 85 * INDUSTRIAL_VOLTAGE},
    "25.0": {"current": 113, "power": 113 * INDUSTRIAL_VOLTAGE},
    "35.0": {"current": 140, "power": 140 * INDUSTRIAL_VOLTAGE},
    "50.0": {"current": 170, "power": 170 * INDUSTRIAL_VOLTAGE},
}

# Residential devices
RESIDENTIAL_DEVICES = {
    "Refrigerator (250W)": 250,
    "Air Conditioner 1.5 Ton (2000W)": 2000,
    "Air Conditioner 1 Ton (1500W)": 1500,
    "Television 32 inch (50W)": 50,
    "Television 43 inch (70W)": 70,
    "Washing Machine (500W)": 500,
    "Microwave Oven (1200W)": 1200,
    "Electric Kettle (1500W)": 1500,
    "Water Heater (1500W)": 1500,
    "Iron (1000W)": 1000,
    "Ceiling Fan (75W)": 75,
    "LED Light Bulb (9W)": 9,
    "Tube Light (40W)": 40,
    "Laptop Charger (65W)": 65,
    "Phone Charger (10W)": 10,
    "Vacuum Cleaner (800W)": 800,
    "Rice Cooker (700W)": 700,
    "Mixer Grinder (500W)": 500,
    "Water Pump (750W)": 750,
    "Desktop Computer (200W)": 200,
}

# Industrial devices
INDUSTRIAL_DEVICES = {
    "Industrial Motor 5HP (3730W)": 3730,
    "Industrial Motor 10HP (7460W)": 7460,
    "Industrial Motor 15HP (11190W)": 11190,
    "Compressor 5HP (3730W)": 3730,
    "Compressor 10HP (7460W)": 7460,
    "Conveyor Belt 2HP (1492W)": 1492,
    "Conveyor Belt 5HP (3730W)": 3730,
    "Welding Machine (5000W)": 5000,
    "Industrial Oven (8000W)": 8000,
    "CNC Machine (7500W)": 7500,
    "Industrial Pump 3HP (2238W)": 2238,
    "Industrial Pump 7.5HP (5595W)": 5595,
    "HVAC System (10000W)": 10000,
    "Industrial Fan 2HP (1492W)": 1492,
    "Lighting System (500W)": 500,
    "Control Panel (200W)": 200,
    "Server Rack (1500W)": 1500,
    "Industrial Charger (1000W)": 1000,
}

def get_safety_status(total_power, wire_power_capacity):
    """Determine safety status based on load - CORRECTED THRESHOLDS"""
    percentage = (total_power / wire_power_capacity) * 100
    
    if percentage <= 80:
        return "✅ SAFE", "green", f"Load: {percentage:.1f}% - Safe operation"
    elif percentage <= 90:
        return "⚠️ CAUTION", "orange", f"Load: {percentage:.1f}% - Approaching limit, consider upgrading"
    elif percentage <= 100:
        return "🔴 NEAR LIMIT", "#ff6b35", f"Load: {percentage:.1f}% - At maximum capacity, upgrade recommended"
    else:
        return "❌ OVERLOAD", "red", f"Load: {percentage:.1f}% - EXCEEDS capacity! Immediate action needed"

def calculate_monthly_cost(total_power_watts, hours_per_day, days_per_month, tariff_rate):
    """Calculate monthly electricity cost"""
    power_kw = total_power_watts / 5000
    monthly_consumption_kwh = power_kw * hours_per_day * days_per_month
    monthly_cost = monthly_consumption_kwh * tariff_rate
    annual_cost = monthly_cost * 12
    
    return {
        "power_kw": round(power_kw, 2),
        "daily_consumption_kwh": round(power_kw * hours_per_day, 2),
        "monthly_consumption_kwh": round(monthly_consumption_kwh, 2),
        "monthly_cost": round(monthly_cost, 2),
        "annual_cost": round(annual_cost, 2)
    }

@app.route("/")
def index():
    """Home page - renders the calculator interface"""
    return render_template("index.html", 
                         residential_devices=RESIDENTIAL_DEVICES,
                         industrial_devices=INDUSTRIAL_DEVICES,
                         residential_wires=RESIDENTIAL_WIRE_SPECS,
                         industrial_wires=INDUSTRIAL_WIRE_SPECS,
                         tariff_rates=TARIFF_RATES)

@app.route("/calculate", methods=["POST"])
def calculate():
    """Calculate power load and cost"""
    try:
        data = request.json
        usage_type = data.get("usage_type", "residential")
        wire_size = data.get("wire_size")
        devices = data.get("devices", [])
        custom_devices = data.get("custom_devices", [])
        
        hours_per_day = float(data.get("hours_per_day", 8))
        days_per_month = int(data.get("days_per_month", 30))
        
        # Select appropriate specs
        if usage_type == "industrial":
            wire_specs = INDUSTRIAL_WIRE_SPECS
            devices_data = INDUSTRIAL_DEVICES
            voltage = INDUSTRIAL_VOLTAGE
        else:
            wire_specs = RESIDENTIAL_WIRE_SPECS
            devices_data = RESIDENTIAL_DEVICES
            voltage = RESIDENTIAL_VOLTAGE
        
        wire = wire_specs.get(wire_size)
        if not wire:
            return jsonify({"error": "Invalid wire size"}), 400
        
        wire_power = wire["power"]
        wire_current = wire["current"]
        
        total_power = 0
        device_details = []
        
        # Process predefined devices
        for device_name in devices:
            if device_name in devices_data:
                power = devices_data[device_name]
                total_power += power
                device_details.append({"name": device_name, "power": power, "type": "predefined"})
        
        # Process custom devices
        for custom in custom_devices:
            try:
                power = float(custom.get("power", 0))
                name = custom.get("name", f"Custom Device ({power}W)")
                if power > 0:
                    total_power += power
                    device_details.append({"name": name, "power": power, "type": "custom"})
            except (ValueError, TypeError):
                continue
        
        if not device_details:
            return jsonify({"error": "No valid devices provided"}), 400
        
        total_current = total_power / voltage
        safety_msg, color, load_percentage = get_safety_status(total_power, wire_power)
        
        # Calculate cost
        tariff_rate = TARIFF_RATES[usage_type]["rate"]
        cost_calculation = calculate_monthly_cost(total_power, hours_per_day, days_per_month, tariff_rate)
        
        # Find recommended wire size - ONLY if load exceeds 85%
        recommended_size = None
        load_percent = (total_power / wire_power) * 100
        
        if load_percent > 85:
            for size, spec in wire_specs.items():
                if spec["power"] >= total_power * 1.2:  # 20% headroom
                    recommended_size = size
                    break
            if not recommended_size:
                for size, spec in wire_specs.items():
                    if spec["power"] >= total_power:
                        recommended_size = size
                        break
        
        result = {
            "success": True,
            "usage_type": usage_type,
            "usage_type_name": TARIFF_RATES[usage_type]["name"],
            "wire_size_mm2": wire_size,
            "wire_power_capacity_w": round(wire_power, 2),
            "wire_current_capacity_a": round(wire_current, 2),
            "total_power_w": round(total_power, 2),
            "total_current_a": round(total_current, 2),
            "load_percentage": load_percentage,
            "devices": device_details,
            "device_count": len(device_details),
            "safety_status": safety_msg,
            "color": color,
            "voltage": voltage,
            "electricity_cost": cost_calculation,
            "tariff_rate": tariff_rate,
            "currency": TARIFF_RATES[usage_type]["currency"],
            "hours_per_day": hours_per_day,
            "days_per_month": days_per_month,
            "recommended_wire_size": recommended_size,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("\n" + "="*60)
    print("⚡ ELECTRICITY POWER & COST CALCULATOR")
    print("="*60)
    print(f"📍 Server: http://127.0.0.1:5000")
    print(f"🔧 Debug Mode: ON")
    print(f"📊 Press CTRL+C to stop")
    print("="*60 + "\n")
    app.run(debug=True, host='127.0.0.1', port=5000)