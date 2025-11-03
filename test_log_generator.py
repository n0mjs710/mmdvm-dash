#!/usr/bin/env python3
"""
Test script to generate sample log entries for testing
Creates a test log file and writes sample MMDVMHost log entries
"""
import time
import random
from datetime import datetime
from pathlib import Path

def generate_timestamp():
    """Generate MMDVMHost timestamp format"""
    now = datetime.now()
    return now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

def write_log_entry(f, level, message):
    """Write a log entry in MMDVMHost format"""
    timestamp = generate_timestamp()
    f.write(f"{level}: {timestamp} {message}\n")
    f.flush()

def main():
    # Create test log directory
    log_dir = Path("/tmp/mmdvm-test-logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "MMDVMHost.log"
    
    print(f"Creating test log file: {log_file}")
    print("Update config/config.json to point to this file:")
    print(f'  "path": "{log_file}"')
    print("\nGenerating sample log entries...")
    print("Press Ctrl+C to stop\n")
    
    modes = ["DMR", "D-Star", "YSF", "P25", "NXDN"]
    callsigns = ["N0CALL", "W1AW", "K2ABC", "VE3XYZ", "G4KLX"]
    dmr_ids = ["3106849", "1234567", "2345678", "3456789"]
    talkgroups = ["91", "310", "3100", "10100", "65000"]
    
    with open(log_file, 'w') as f:
        # Initial startup sequence
        write_log_entry(f, 'M', 'MMDVMHost starting')
        write_log_entry(f, 'M', 'MMDVM protocol version: 1, description: MMDVM_HS_Hat')
        write_log_entry(f, 'M', 'DMR Network, connected')
        write_log_entry(f, 'M', 'Mode set to DMR')
        
        time.sleep(2)
        
        # Generate random transmissions
        try:
            count = 0
            while True:
                mode = random.choice(modes)
                
                # Mode change occasionally
                if random.random() < 0.1:
                    write_log_entry(f, 'M', f'Mode set to {mode}')
                    print(f"Mode changed to {mode}")
                    time.sleep(1)
                    continue
                
                if mode == "DMR":
                    slot = random.choice([1, 2])
                    src = random.choice(dmr_ids)
                    tg = random.choice(talkgroups)
                    
                    write_log_entry(f, 'M', f'DMR Slot {slot}, received voice header from {src} to TG {tg}')
                    print(f"DMR: {src} → TG {tg} (Slot {slot})")
                    
                    # Simulate transmission duration
                    duration = random.randint(2, 10)
                    time.sleep(duration)
                    
                    write_log_entry(f, 'M', f'DMR Slot {slot}, transmission ended, duration: {duration}.0s')
                
                elif mode == "D-Star":
                    src = random.choice(callsigns)
                    write_log_entry(f, 'M', f'D-Star, received header from {src}  /1234    to CQCQCQ  ')
                    print(f"D-Star: {src} → CQCQCQ")
                    time.sleep(random.randint(3, 8))
                
                elif mode == "YSF":
                    src = random.choice(callsigns)
                    write_log_entry(f, 'M', f'YSF, received header from {src} to ALL')
                    print(f"YSF: {src} → ALL")
                    time.sleep(random.randint(2, 6))
                
                elif mode == "P25":
                    src = random.choice(dmr_ids)
                    tg = random.choice(["10100", "31000", "31665"])
                    write_log_entry(f, 'M', f'P25, received voice header from {src} to TG {tg}')
                    print(f"P25: {src} → TG {tg}")
                    time.sleep(random.randint(3, 7))
                
                elif mode == "NXDN":
                    src = random.choice(["12345", "23456", "34567"])
                    tg = random.choice(["65000", "65001", "9999"])
                    write_log_entry(f, 'M', f'NXDN, received voice header from {src} to TG {tg}')
                    print(f"NXDN: {src} → TG {tg}")
                    time.sleep(random.randint(2, 6))
                
                count += 1
                
                # Random network events
                if count % 20 == 0:
                    if random.random() < 0.3:
                        network = random.choice(["DMR", "YSF", "P25"])
                        if random.random() < 0.5:
                            write_log_entry(f, 'M', f'{network} Network, connected')
                            print(f"{network} Network connected")
                        else:
                            write_log_entry(f, 'M', f'{network} Network, disconnected')
                            print(f"{network} Network disconnected")
                
                # Wait between transmissions
                time.sleep(random.randint(5, 15))
        
        except KeyboardInterrupt:
            print("\n\nStopping test log generator...")
            write_log_entry(f, 'M', 'MMDVMHost stopping')

if __name__ == "__main__":
    main()
